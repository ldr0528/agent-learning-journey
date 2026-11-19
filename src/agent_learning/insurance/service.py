"""同一比较任务的配置、模型适配与会话保存；密钥只留在客户端。"""

from pathlib import Path
from contextlib import contextmanager, nullcontext
import threading

from ..config import load_settings
from .catalog import Catalog
from .workflow import run_comparison
from .execution import ExecutionCancelled, check_cancelled, emit


_LOCK_GUARD = threading.Lock()
_SESSION_LOCKS = {}


@contextmanager
def _session_lock(store, session_id):
    key = str(getattr(store, "directory", id(store))), session_id
    with _LOCK_GUARD:
        lock = _SESSION_LOCKS.setdefault(key, threading.Lock())
    if not lock.acquire(blocking=False):
        raise ValueError("这个会话已有操作正在进行，请等待或停止后再试。")
    try:
        yield
    finally:
        lock.release()


def load_catalog(kind="demo"):
    if kind not in ("demo", "official"):
        raise ValueError("资料目录需为 demo 或 official。")
    return Catalog() if kind == "demo" else Catalog(Path(__file__).resolve().parents[1] / "data" / "insurance_official.json")


def _cancellation(store, run_id, external):
    def cancelled():
        return bool((external and external()) or
                    (run_id and store.load_run(run_id).get("cancel_requested")))
    return cancelled


def model_adapter(client, settings):
    def request(messages, tools):
        options = dict(settings.request_options)
        # 比较完成工具需要列出多产品的证据编号，单次文本练习的输出额度不足。
        if "max_tokens" in options:
            options["max_tokens"] = 2200
        elif "max_completion_tokens" in options:
            options["max_completion_tokens"] = 4096
        return client.chat.completions.create(model=settings.model, messages=messages, tools=tools,
                                             tool_choice="auto", parallel_tool_calls=False, **options)
    return request


def run_session(store, session_id, request=None, mode="offline", catalog=None, max_calls=6,
                on_event=None, should_cancel=None, expected_version=None):
    if mode not in ("offline", "live"):
        raise ValueError("运行模式需为 offline 或 live。")
    claim = store.claim_session(session_id, kind="comparison", mode=mode) if hasattr(store, "claim_session") else nullcontext()
    with _session_lock(store, session_id), claim as run_id:
        should_cancel = _cancellation(store, run_id, should_cancel)
        record = store.load(session_id)
        version = record.get("brief_version", 1)
        if expected_version is not None and version != expected_version:
            raise ValueError("需求已经更新，请刷新后再运行。")
        catalog = catalog or load_catalog(record["catalog_kind"])
        current = request if request is not None else record["request"]
        # 缺需求时不创建模型客户端；补充后从保存的需求重新取证，避免混用旧资料。
        from .workflow import prepare_request
        ready = prepare_request(current, catalog)
        if mode == "offline" or ready["status"] == "needs_input":
            report = run_comparison(current, catalog=catalog, mode="offline",
                                    on_event=on_event, should_cancel=should_cancel)
            report["mode"] = mode
        else:
            settings = load_settings()
            with settings.create_client() as client:
                report = run_comparison(current, catalog=catalog, mode="live", max_calls=max_calls,
                                        request_model=model_adapter(client, settings),
                                        on_event=on_event, should_cancel=should_cancel)
        if should_cancel and should_cancel():
            report.update(status="cancelled", error="本次查证已停止，已取得的资料保留。")
        report.update(session_id=session_id, catalog_kind=record["catalog_kind"],
                      revision=record["revision"] + 1)
        store.save(session_id, report, expected_version=version)
        if hasattr(store, "append_message"):
            content = ("本次查证已停止，已取得的资料保存在报告中。" if report["status"] == "cancelled" else
                       "资料比较已整理。你可以查看关注项差异、完整对照和出处，也可以继续追问。" if report["status"] in ("completed", "completed_with_gaps") else
                       "本次查证尚未完成，请查看报告中的停止原因与已取得的资料。")
            store.append_message(session_id, "assistant", content, kind="report", report_revision=report["revision"])
        return report


def run_message(store, session_id, message, *, intent="intake", mode="offline", catalog=None,
                on_event=None, should_cancel=None, expected_version=None, request_model=None):
    """一条消息只做需求提案或报告追问；确认与查证由独立动作触发。"""
    if not isinstance(message, str) or not 1 <= len(message.strip()) <= 1500:
        raise ValueError("消息需为 1–1500 字符。")
    if intent not in ("intake", "followup") or mode not in ("offline", "live"):
        raise ValueError("消息类型或运行模式不符合要求。")
    from .conversation import propose_needs, answer_report
    claim = store.claim_session(session_id, kind=intent, mode=mode) if hasattr(store, "claim_session") else nullcontext()
    with _session_lock(store, session_id), claim as run_id:
        should_cancel = _cancellation(store, run_id, should_cancel)
        record = store.load(session_id)
        version = record.get("brief_version", 1)
        if expected_version is not None and version != expected_version:
            raise ValueError("需求已经更新，请刷新后重试。")
        catalog = catalog or load_catalog(record["catalog_kind"])
        check_cancelled(should_cancel)
        store.append_message(session_id, "user", message.strip(), kind=intent)
        calls = 0

        def invoke(adapter):
            def counted(messages, tools):
                nonlocal calls
                calls += 1
                return adapter(messages, tools)
            options = dict(mode=mode, request_model=counted if adapter else None,
                           on_event=on_event, should_cancel=should_cancel)
            return (propose_needs(record, message.strip(), catalog, **options) if intent == "intake" else
                    answer_report(record, message.strip(), **options))

        try:
            needs_report = intent == "followup" and (not record.get("result") or record.get("result_stale"))
            if mode == "offline" or needs_report:
                result = invoke(None)
            elif request_model is not None:
                result = invoke(request_model)
            else:
                settings = load_settings()
                with settings.create_client() as client:
                    result = invoke(model_adapter(client, settings))
            check_cancelled(should_cancel)
        except ExecutionCancelled:
            result = {"kind": intent, "status": "cancelled", "content": "本次处理已停止。需求和已有报告没有被更改。",
                      "evidence_ids": [], "sources": [], "model_calls": calls, "mode": mode, "usage": []}
        except Exception as error:
            # 不将供应商异常、密钥、模型原文或原始参数暴露到界面。
            result = {"kind": intent, "status": "model_error", "content":
                      "这条消息暂时没有处理完成。可以重试，或在需求卡中直接填写；已保存的资料仍然保留。",
                      "error_type": type(error).__name__, "evidence_ids": [], "sources": [],
                      "model_calls": calls, "mode": mode, "usage": []}
            emit(on_event, "message_error", "消息处理未完成，已保留会话。")
        if result.get("proposal"):
            store.set_proposal(session_id, result["proposal"], expected_version=version)
        store.append_message(session_id, "assistant", result["content"], kind=result["kind"],
                             status=result["status"], evidence_ids=result.get("evidence_ids", []),
                             sources=result.get("sources", []), report_revision=result.get("report_revision"),
                             mode=mode, model_calls=result.get("model_calls", 0))
        return result
