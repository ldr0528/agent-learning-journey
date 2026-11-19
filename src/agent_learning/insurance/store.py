"""本地会话快照；按随机编号访问，原子替换文件，保留最近五次结果。"""

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import threading
from uuid import uuid4


class SessionStore:
    def __init__(self, directory="outputs/insurance-sessions"):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _path(self, session_id):
        if not isinstance(session_id, str) or not re.fullmatch(r"[a-f0-9]{32}", session_id):
            raise ValueError("会话编号不合法。")
        return self.directory / (session_id + ".json")

    def _write(self, record):
        path = self._path(record["id"])
        payload = json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False)
        if len(payload.encode("utf-8")) > 8000000:
            raise ValueError("会话内容超过本地保存上限。")
        temp = path.with_suffix("." + uuid4().hex + ".tmp")
        try:
            temp.write_text(payload, encoding="utf-8")
            temp.replace(path)
        finally:
            if temp.exists():
                temp.unlink()

    def create(self, request, catalog_kind="demo"):
        if catalog_kind not in ("demo", "official") or not isinstance(request, dict):
            raise ValueError("会话资料目录或需求不合法。")
        if len(json.dumps(request, ensure_ascii=False, allow_nan=False)) > 20000:
            raise ValueError("需求内容过长。")
        session_id = uuid4().hex
        with self._lock:
            self._write({"id": session_id, "request": deepcopy(request), "catalog_kind": catalog_kind,
                         "result": None, "revision": 0, "history": [],
                         "updated_at": datetime.now(timezone.utc).isoformat()})
        return session_id

    def load(self, session_id):
        with self._lock:
            path = self._path(session_id)
            if not path.is_file():
                raise ValueError("找不到这个本地会话。")
            if path.stat().st_size > 8000000:
                raise ValueError("会话文件过大。")
            return json.loads(path.read_text(encoding="utf-8"))

    def save(self, session_id, result):
        if not isinstance(result, dict) or not isinstance(result.get("request"), dict):
            raise ValueError("保存结果需要完整的需求快照。")
        with self._lock:
            record = self.load(session_id)
            if record["result"] is not None:
                record["history"] = (record["history"] + [{"revision": record["revision"],
                                      "result": record["result"], "updated_at": record["updated_at"]}])[-5:]
            record.update(request=deepcopy(result["request"]), result=deepcopy(result),
                          revision=record["revision"] + 1, updated_at=datetime.now(timezone.utc).isoformat())
            self._write(record)
