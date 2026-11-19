"""有界后台任务、事件轮询与协作取消；不会自动重放中断的模型请求。"""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import os
import threading
from uuid import uuid4

from .store import ACTIVE_STATUSES, StoreConflict, TERMINAL_STATUSES
from .workflow import prepare_request


def process_alive(pid):
    if type(pid) is not int or pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return ctypes.get_last_error() == 5  # 无权限不等于进程已退出。
        try:
            code = wintypes.DWORD()
            return not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value == 259
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def public_run(run, after_seq=0):
    if type(after_seq) is not int or after_seq < 0:
        raise ValueError("事件序号需为非负整数。")
    result = {key: deepcopy(run.get(key)) for key in (
        "id", "session_id", "status", "kind", "last_seq", "result", "error", "created_at", "updated_at")}
    result["events"] = [deepcopy(event) for event in run["events"] if event["seq"] > after_seq]
    result["mode"] = run["payload"].get("mode", "offline")
    return result


class RunManager:
    def __init__(self, store, runner, *, message_runner=None, catalogs=None, max_workers=2, max_queue=6):
        if type(max_workers) is not int or not 1 <= max_workers <= 4 or type(max_queue) is not int or not 0 <= max_queue <= 20:
            raise ValueError("后台工作线程需为 1–4，排队上限需为 0–20。")
        self.store, self.runner, self.message_runner = store, runner, message_runner
        self.catalogs = catalogs or {}
        self.owner_id = uuid4().hex
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="insurance-run")
        self._slots = threading.BoundedSemaphore(max_workers + max_queue)
        self._lock = threading.RLock()
        self._futures = {}
        self._closed = False
        self.store.recover_runs(process_alive)

    def _catalog(self, kind):
        if kind in self.catalogs:
            return self.catalogs[kind]
        from .service import load_catalog
        return load_catalog(kind)

    def submit(self, session_id, *, kind, payload, expected_version, client_request_id):
        if kind not in ("comparison", "intake", "followup"):
            raise ValueError("任务类型不合法。")
        if not isinstance(payload, dict) or payload.get("mode", "offline") not in ("offline", "live"):
            raise ValueError("运行模式需为 offline 或 live。")
        if type(expected_version) is not int or expected_version < 1:
            raise ValueError("请提供当前需求版本。")
        canonical = {**deepcopy(payload), "kind": kind, "expected_version": expected_version}
        with self._lock:
            if self._closed:
                raise StoreConflict("服务正在停止，请稍后再试。")
            existing = self.store.existing_run(session_id, client_request_id, canonical)
            if existing:
                return public_run(existing)
            record = self.store.load(session_id)
            self.store._version(record, expected_version)
            if kind == "comparison":
                calls = canonical.get("max_calls", 6)
                if type(calls) is not int or not 1 <= calls <= 12:
                    raise ValueError("模型请求上限需为 1–12。")
                if not canonical.get("legacy"):
                    if record["confirmed_version"] != record["brief_version"]:
                        raise StoreConflict("请先确认本次需求，再开始比较。")
                    prepared = prepare_request(record["request"], self._catalog(record["catalog_kind"]))
                    if prepared["status"] != "ready":
                        raise StoreConflict("请补充关注维度并选择两到三个产品版本。")
            if not self._slots.acquire(blocking=False):
                raise StoreConflict("任务队列已满，请等待正在进行的任务完成。")
            try:
                run, created = self.store.create_run(session_id, kind=kind, payload=canonical,
                    client_request_id=client_request_id, expected_version=expected_version,
                    owner_id=self.owner_id, owner_pid=os.getpid())
                if not created:
                    self._slots.release()
                    return public_run(run)
                run = self.store.change_run(run["id"], event={"type": "queued", "message": "任务已加入队列。"})
                future = self._executor.submit(self._execute, run["id"])
                self._futures[run["id"]] = future
                future.add_done_callback(lambda completed, run_id=run["id"]: self._done(run_id))
                return public_run(run)
            except BaseException:
                self._slots.release()
                if "run" in locals() and "created" in locals() and created:
                    self.store.change_run(run["id"], status="failed", error="任务未能启动。")
                raise

    def _done(self, run_id):
        with self._lock:
            self._futures.pop(run_id, None)
            self._slots.release()

    def _execute(self, run_id):
        run = self.store.change_run(run_id, status="running", event={"type": "started", "message": "正在处理本次请求。"})
        if run["status"] in TERMINAL_STATUSES:
            return

        def should_cancel():
            current = self.store.load_run(run_id)
            return current["cancel_requested"] or current["status"] in TERMINAL_STATUSES

        def on_event(event):
            if not isinstance(event, dict):
                return
            clean = deepcopy(event)
            clean["type"] = str(clean.get("type", "progress"))[:80]
            clean["message"] = str(clean.get("message", ""))[:2000]
            if len(json.dumps(clean, ensure_ascii=False, allow_nan=False).encode()) > 32768:
                clean = {"type": clean["type"], "message": clean["message"]}
            self.store.change_run(run_id, event=clean)

        try:
            if should_cancel():
                self.store.change_run(run_id, status="cancelled")
                return
            with self.store.execution(run_id):
                record = self.store.load(run["session_id"])
                payload = run["payload"]
                common = dict(mode=payload.get("mode", "offline"), catalog=self._catalog(record["catalog_kind"]),
                              on_event=on_event, should_cancel=should_cancel,
                              expected_version=payload["expected_version"])
                if run["kind"] == "comparison":
                    result = self.runner(self.store, run["session_id"], request=payload.get("request"),
                                         max_calls=payload.get("max_calls", 6), **common)
                else:
                    message_runner = self.message_runner
                    if message_runner is None:
                        from .service import run_message
                        message_runner = run_message
                    result = message_runner(self.store, run["session_id"], message=payload["message"],
                                            intent=run["kind"], **common)
                cancelled = should_cancel() or (isinstance(result, dict) and result.get("status") == "cancelled")
                model_error = isinstance(result, dict) and result.get("status") == "model_error"
                status = "cancelled" if cancelled else "failed" if model_error else "succeeded"
                message = ("任务已取消，已保存取得的内容。" if cancelled else
                           "本次处理未完成，已有资料保留在会话中。" if model_error else "本次处理已完成。")
                self.store.change_run(run_id, status=status, result=result, error=message if model_error and not cancelled else None,
                    event={"type": status, "message": message})
        except Exception as error:
            cancelled = should_cancel() or type(error).__name__ == "ExecutionCancelled"
            status = "cancelled" if cancelled else "failed"
            message = "任务已取消。" if cancelled else "本次处理未完成，请查看会话中的已有结果后重试。"
            self.store.change_run(run_id, status=status, error=None if cancelled else message,
                                  event={"type": status, "message": message})

    def get(self, run_id, after_seq=0):
        return public_run(self.store.load_run(run_id), after_seq)

    def cancel(self, run_id):
        with self._lock:
            run = self.store.change_run(run_id, cancel=True,
                event={"type": "cancel_requested", "message": "已请求停止，将在当前操作结束后取消。"})
            future = self._futures.get(run_id)
            if future and run["status"] == "cancelled":
                future.cancel()
            return public_run(run)

    def wait(self, run_id):
        with self._lock:
            future = self._futures.get(run_id)
        if future:
            future.result()
        return self.get(run_id)

    def close(self, *, wait=True):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            active = list(self._futures)
        for run_id in active:
            self.cancel(run_id)
        self._executor.shutdown(wait=wait, cancel_futures=True)
        if not wait:
            for run_id in active:
                self.store.change_run(run_id, status="interrupted", error="服务停止，本次任务未完成。")
