"""本地会话与任务记录；SQLite 事务保护跨线程、跨进程的版本更新。"""

from contextlib import closing, contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import threading
from uuid import uuid4


SCHEMA_VERSION = 2
MAX_RECORD_BYTES = 8_000_000
ACTIVE_STATUSES = {"queued", "running", "cancelling"}
TERMINAL_STATUSES = {"succeeded", "failed", "cancelled", "interrupted"}


def now():
    return datetime.now(timezone.utc).isoformat()


class StoreConflict(ValueError):
    pass


class StoreNotFound(ValueError):
    pass


class SessionStore:
    def __init__(self, directory="outputs/insurance-sessions"):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.database = self.directory / "state.sqlite3"
        self._context = threading.local()
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("CREATE TABLE IF NOT EXISTS records (key TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            connection.execute("PRAGMA user_version=2")

    def _connect(self):
        connection = sqlite3.connect(self.database, timeout=5, isolation_level=None)
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    @contextmanager
    def _transaction(self):
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _id(self, value):
        if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{32}", value):
            raise ValueError("会话或任务编号不合法。")
        return value

    def _path(self, session_id):
        return self.directory / (self._id(session_id) + ".json")

    @staticmethod
    def _get(connection, key):
        row = connection.execute("SELECT payload FROM records WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    @staticmethod
    def _put(connection, key, value):
        payload = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        if len(payload.encode("utf-8")) > MAX_RECORD_BYTES:
            raise ValueError("本地记录超过 8 MB 保存上限。")
        connection.execute("INSERT INTO records(key,payload) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET payload=excluded.payload",
                           (key, payload))

    @staticmethod
    def _normalize(record):
        record.setdefault("schema_version", SCHEMA_VERSION)
        record.setdefault("brief_version", 1)
        record.setdefault("confirmed_version", 0)
        record.setdefault("result_brief_version", record["brief_version"] if record.get("result") is not None else None)
        record.setdefault("messages", [])
        record.setdefault("proposal", None)
        record.setdefault("active_run", None)
        record.setdefault("history", [])
        record.setdefault("revision", 0)
        record["schema_version"] = SCHEMA_VERSION
        record["result_stale"] = record.get("result") is not None and record["result_brief_version"] != record["brief_version"]
        return record

    def _session(self, connection, session_id):
        self._id(session_id)
        record = self._get(connection, "session:" + session_id)
        if record is None:
            legacy = self._path(session_id)
            if not legacy.is_file():
                raise StoreNotFound("找不到这个本地会话。")
            if legacy.stat().st_size > MAX_RECORD_BYTES:
                raise ValueError("会话文件过大。")
            record = json.loads(legacy.read_text(encoding="utf-8-sig"))
            if not isinstance(record, dict) or record.get("id") != session_id or not isinstance(record.get("request"), dict):
                raise ValueError("旧会话内容不合法。")
            self._normalize(record)
            self._put(connection, "session:" + session_id, record)
        return self._normalize(record)

    @staticmethod
    def _version(record, expected_version):
        if expected_version is not None and (type(expected_version) is not int or expected_version != record["brief_version"]):
            raise StoreConflict("需求版本已更新，请刷新会话后重试。")

    def _guard_write(self, record):
        active = record.get("active_run")
        running_id = getattr(self._context, "run_id", None)
        if running_id and (not active or active["id"] != running_id):
            raise StoreConflict("该任务已经停止，不能覆盖当前会话。")
        if active and active["id"] != running_id:
            raise StoreConflict("当前会话正在运行，请等待结束或取消后再修改。")

    @contextmanager
    def execution(self, run_id):
        previous = getattr(self._context, "run_id", None)
        self._context.run_id = run_id
        try:
            yield
        finally:
            self._context.run_id = previous

    @contextmanager
    def claim_session(self, session_id, *, kind="comparison", mode="offline"):
        """同步 CLI 与后台任务共享占用；认领发生在任何模型调用之前。"""
        inherited = getattr(self._context, "run_id", None)
        if inherited:
            with self._transaction() as connection:
                self._guard_write(self._session(connection, session_id))
            yield inherited
            return
        from .runs import process_alive
        self.recover_runs(process_alive)
        record = self.load(session_id)
        operation = uuid4().hex
        run, _ = self.create_run(session_id, kind=kind, payload={"mode": mode, "synchronous": True},
            client_request_id=operation, expected_version=record["brief_version"],
            owner_id="sync:" + operation, owner_pid=os.getpid())
        self.change_run(run["id"], status="running")
        try:
            with self.execution(run["id"]):
                yield run["id"]
        except BaseException as error:
            cancelled = type(error).__name__ in ("ExecutionCancelled", "KeyboardInterrupt")
            self.change_run(run["id"], status="cancelled" if cancelled else "failed",
                            error=None if cancelled else "本次同步操作未完成。")
            raise
        else:
            self.change_run(run["id"], status="succeeded")

    def finish_claim(self, run_id, result):
        """同步入口保存业务结果后结束认领；后台任务仍由 RunManager 收尾。"""
        run = self.load_run(run_id)
        if not run["payload"].get("synchronous"):
            return run
        if not isinstance(result, dict):
            raise ValueError("任务结果需为对象。")
        status = ("cancelled" if result.get("status") == "cancelled" else
                  "failed" if result.get("status") == "model_error" else "succeeded")
        message = ("任务已取消，已取得的内容保留在会话中。" if status == "cancelled" else
                   "本次处理未完成，已有资料保留在会话中。" if status == "failed" else "本次处理已完成。")
        return self.change_run(run_id, status=status, result=result,
            error=message if status == "failed" else None, event={"type": status, "message": message})

    def create(self, request, catalog_kind="demo"):
        if catalog_kind not in ("demo", "official") or not isinstance(request, dict):
            raise ValueError("会话资料目录或需求不合法。")
        if len(json.dumps(request, ensure_ascii=False, allow_nan=False)) > 20000:
            raise ValueError("需求内容过长。")
        session_id = uuid4().hex
        record = self._normalize({"id": session_id, "request": deepcopy(request), "catalog_kind": catalog_kind,
                                  "result": None, "revision": 0, "history": [], "updated_at": now()})
        with self._transaction() as connection:
            self._put(connection, "session:" + session_id, record)
        return session_id

    def load(self, session_id):
        with self._transaction() as connection:
            return self._session(connection, session_id)

    def list_sessions(self, limit=50):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("会话列表数量需为 1–100。")
        with self._transaction() as connection:
            # 只迁移历史约定中的 UUID 文件；不读取任意路径，原文件保持不变。
            for path in self.directory.glob("*.json"):
                if re.fullmatch(r"[a-f0-9]{32}", path.stem):
                    try:
                        self._session(connection, path.stem)
                    except (ValueError, OSError):
                        continue
            records = [self._normalize(json.loads(row[0])) for row in connection.execute(
                "SELECT payload FROM records WHERE key LIKE 'session:%'")]
        records.sort(key=lambda record: record.get("updated_at", ""), reverse=True)
        summaries = []
        for record in records[:limit]:
            active, result = record["active_run"], record.get("result") or {}
            summaries.append({key: record.get(key) for key in ("id", "catalog_kind", "updated_at", "brief_version",
                "confirmed_version", "result_brief_version", "result_stale", "active_run")})
            generic = {"", "比较选定医疗险的保障与限制。", "比较选定医疗险的保障与限制", "新的医疗险比较"}
            title = (record["request"].get("question") or "").strip()
            if title in generic:
                proposal = ((record.get("proposal") or {}).get("request") or {}).get("question", "").strip()
                first_message = next((message.get("content", "").strip() for message in record["messages"]
                                      if message.get("role") == "user" and message.get("content", "").strip()), "")
                title = proposal if proposal not in generic else first_message or title or "新的医疗险比较"
            summaries[-1].update(title=" ".join(title.split())[:60],
                                  status=active["status"] if active else result.get("status", "draft"))
        return summaries

    def require_message_capacity(self, session_id, count):
        """在会话认领内预检，确保模型调用前已预留完整一轮消息的空间。"""
        if type(count) is not int or count < 1:
            raise ValueError("消息数量需为正整数。")
        with self._transaction() as connection:
            record = self._session(connection, session_id)
            self._guard_write(record)
            if len(record["messages"]) + count > 200:
                raise StoreConflict("本会话剩余消息空间不足，请新建会话继续。")

    def append_message(self, session_id, role, content, **metadata):
        if role not in ("user", "assistant", "system") or not isinstance(content, str) or len(content) > 12000:
            raise ValueError("消息角色或内容不符合要求。")
        if set(metadata) & {"id", "role", "content", "created_at"}:
            raise ValueError("消息元数据不能覆盖基础字段。")
        message = {"id": uuid4().hex, "role": role, "content": content, "created_at": now(), **deepcopy(metadata)}
        with self._transaction() as connection:
            record = self._session(connection, session_id)
            self._guard_write(record)
            if len(record["messages"]) >= 200:
                raise ValueError("本会话已达到 200 条消息，请新建会话继续。")
            record["messages"].append(message)
            record["updated_at"] = now()
            self._put(connection, "session:" + session_id, record)
        return message

    def set_proposal(self, session_id, proposal, expected_version):
        if not isinstance(proposal, dict) or not isinstance(proposal.get("request"), dict):
            raise ValueError("需求提案需包含完整需求。")
        with self._transaction() as connection:
            record = self._session(connection, session_id)
            self._version(record, expected_version)
            self._guard_write(record)
            record["proposal"] = {**deepcopy(proposal), "base_version": record["brief_version"]}
            record["updated_at"] = now()
            self._put(connection, "session:" + session_id, record)
            return record

    def update_brief(self, session_id, request, expected_version=None, confirm=True):
        if not isinstance(request, dict) or type(confirm) is not bool:
            raise ValueError("需求内容或确认状态不合法。")
        if len(json.dumps(request, ensure_ascii=False, allow_nan=False)) > 20000:
            raise ValueError("需求内容过长。")
        with self._transaction() as connection:
            record = self._session(connection, session_id)
            self._version(record, expected_version)
            self._guard_write(record)
            if record["request"] != request:
                record["brief_version"] += 1
            record["request"] = deepcopy(request)
            if confirm:
                record["confirmed_version"] = record["brief_version"]
            record["proposal"] = None
            record["updated_at"] = now()
            self._normalize(record)
            self._put(connection, "session:" + session_id, record)
            return record

    def save(self, session_id, result, expected_version=None):
        if not isinstance(result, dict) or not isinstance(result.get("request"), dict):
            raise ValueError("保存结果需要完整的需求快照。")
        with self._transaction() as connection:
            record = self._session(connection, session_id)
            self._version(record, expected_version)
            self._guard_write(record)
            if record["result"] is not None:
                record["history"] = (record["history"] + [{"revision": record["revision"],
                    "result": record["result"], "updated_at": record["updated_at"]}])[-5:]
            # 兼容旧 CLI 通过 run_session(request=...) 更新完整需求。
            if record["request"] != result["request"]:
                record["brief_version"] += 1
                record["proposal"] = None
            record.update(request=deepcopy(result["request"]), result=deepcopy(result),
                          result_brief_version=record["brief_version"], revision=record["revision"] + 1, updated_at=now())
            self._normalize(record)
            self._put(connection, "session:" + session_id, record)

    @staticmethod
    def _request_key(session_id, client_request_id):
        if not isinstance(client_request_id, str) or not 1 <= len(client_request_id) <= 100:
            raise ValueError("请提供 1–100 字符的请求编号。")
        return "request:" + session_id + ":" + hashlib.sha256(client_request_id.encode()).hexdigest()

    def existing_run(self, session_id, client_request_id, payload):
        with self._transaction() as connection:
            return self._existing_run(connection, session_id, client_request_id, payload)

    def _existing_run(self, connection, session_id, client_request_id, payload):
        key = self._request_key(session_id, client_request_id)
        existing = self._get(connection, key)
        if existing:
            if existing["payload"] != payload:
                raise StoreConflict("同一请求编号不能提交不同内容，请使用新的请求编号。")
            return self._get(connection, "run:" + existing["run_id"])
        return None

    def create_run(self, session_id, *, kind, payload, client_request_id, expected_version, owner_id, owner_pid):
        with self._transaction() as connection:
            existing = self._existing_run(connection, session_id, client_request_id, payload)
            if existing:
                return existing, False
            record = self._session(connection, session_id)
            self._version(record, expected_version)
            if record["active_run"]:
                raise StoreConflict("当前会话已有任务，请等待结束或取消。")
            run_id, timestamp = uuid4().hex, now()
            run = {"id": run_id, "session_id": session_id, "kind": kind, "status": "queued",
                   "events": [], "last_seq": 0, "result": None, "error": None,
                   "created_at": timestamp, "updated_at": timestamp, "cancel_requested": False,
                   "payload": deepcopy(payload), "owner_id": owner_id, "owner_pid": owner_pid,
                   "schema_version": SCHEMA_VERSION}
            record["active_run"] = {key: run[key] for key in ("id", "status", "kind", "created_at")}
            record["updated_at"] = timestamp
            self._put(connection, "run:" + run_id, run)
            self._put(connection, "session:" + session_id, record)
            self._put(connection, self._request_key(session_id, client_request_id), {"payload": deepcopy(payload), "run_id": run_id})
            return run, True

    def load_run(self, run_id):
        self._id(run_id)
        with closing(self._connect()) as connection:
            run = self._get(connection, "run:" + run_id)
        if run is None:
            raise StoreNotFound("找不到这个任务。")
        return run

    def change_run(self, run_id, *, status=None, event=None, result=None, error=None, cancel=False):
        with self._transaction() as connection:
            run = self._get(connection, "run:" + self._id(run_id))
            if run is None:
                raise StoreNotFound("找不到这个任务。")
            if run["status"] in TERMINAL_STATUSES:
                return run
            if cancel:
                run["cancel_requested"] = True
                status = "cancelled" if run["status"] == "queued" else "cancelling"
            if status:
                if status not in ACTIVE_STATUSES | TERMINAL_STATUSES:
                    raise ValueError("任务状态不合法。")
                if run["cancel_requested"] and status == "succeeded":
                    status = "cancelled"
                    if event:
                        event = {**event, "type": "cancelled", "message": "任务已取消，已取得的内容保留在会话中。"}
                run["status"] = status
            if result is not None:
                run["result"] = deepcopy(result)
            if error is not None:
                run["error"] = error
            if event and run["last_seq"] < 1000:
                run["last_seq"] += 1
                run["events"].append({**deepcopy(event), "seq": run["last_seq"]})
            run["updated_at"] = now()
            record = self._session(connection, run["session_id"])
            if record["active_run"] and record["active_run"]["id"] == run_id:
                if run["status"] in TERMINAL_STATUSES:
                    record["active_run"] = None
                else:
                    record["active_run"]["status"] = run["status"]
                record["updated_at"] = run["updated_at"]
                self._put(connection, "session:" + record["id"], record)
            self._put(connection, "run:" + run_id, run)
            return run

    def recover_run(self, run_id, process_alive):
        run = self.load_run(run_id)
        if run["status"] in ACTIVE_STATUSES and not process_alive(run.get("owner_pid")):
            return self.change_run(run_id, status="interrupted", error="执行进程已退出，本次任务中断；不会自动重新请求模型。",
                event={"type": "interrupted", "message": "任务中断，已保留保存的记录。"})
        return run

    def recover_runs(self, process_alive):
        with closing(self._connect()) as connection:
            runs = [json.loads(row[0]) for row in connection.execute("SELECT payload FROM records WHERE key LIKE 'run:%'")]
        for run in runs:
            if run["status"] in ACTIVE_STATUSES:
                self.recover_run(run["id"], process_alive)
