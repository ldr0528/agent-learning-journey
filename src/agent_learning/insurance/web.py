"""仅供本机使用的医疗险资料比较界面；HTTP 层不直接调用模型。"""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
import threading
from urllib.parse import parse_qs, urlsplit

from .catalog import DIMENSIONS
from .workflow import prepare_request


MAX_BODY_BYTES = 64 * 1024
SESSION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}")
CATALOG_LABELS = {"demo": "自拟教学示例", "official": "官方条款节选"}
PAGE_PATH = Path(__file__).resolve().parent / "static" / "index.html"


class HTTPProblem(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def create_server(*, store, catalogs, runner, port=8765):
    """返回未启动的本地服务器；测试可注入目录、存储与不请求模型的 runner。"""
    if not catalogs or set(catalogs) - set(CATALOG_LABELS):
        raise ValueError("网页目录仅接受 demo 和 official。")
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("端口需为 0–65535 的整数。")

    class InsuranceServer(ThreadingHTTPServer):
        daemon_threads = True
        block_on_close = False

    class Handler(BaseHTTPRequestHandler):
        server_version = "InsuranceLocal/1.0"

        def setup(self):
            super().setup()
            self.connection.settimeout(10)
            self._body_consumed = False

        def log_message(self, format, *args):
            # 需求、会话标识和错误正文不进入默认访问日志。
            pass

        def _send(self, status, body, content_type="application/json; charset=utf-8", *, filename=None):
            if not isinstance(body, bytes):
                body = json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                             "style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; "
                             "frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'")
            if filename:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(body)

        def _check_origin(self, *, mutation=False):
            hosts = self.headers.get_all("Host", [])
            if hosts != [self.server.authority]:
                raise HTTPProblem(403, "请使用启动时显示的本机地址访问。")
            origins = self.headers.get_all("Origin", [])
            if origins and origins != [self.server.origin]:
                raise HTTPProblem(403, "不接受其他网页发起的请求。")
            if self.headers.get("Sec-Fetch-Site", "") not in ("", "none", "same-origin"):
                raise HTTPProblem(403, "不接受跨站请求。")
            if mutation:
                if origins != [self.server.origin]:
                    raise HTTPProblem(403, "操作需要来自本机页面。")
                tokens = self.headers.get_all("X-CSRF-Token", [])
                if len(tokens) != 1 or not tokens[0].isascii() or not secrets.compare_digest(tokens[0], self.server.csrf_token):
                    raise HTTPProblem(403, "页面凭据已失效，请刷新后重试。")

        def _json_body(self):
            if self.headers.get_all("Transfer-Encoding"):
                raise HTTPProblem(400, "不支持分块请求。")
            lengths = self.headers.get_all("Content-Length", [])
            if not lengths:
                raise HTTPProblem(411, "请求缺少内容长度。")
            if len(lengths) != 1 or not re.fullmatch(r"[0-9]+", lengths[0]):
                raise HTTPProblem(400, "请求长度不合法。")
            length = int(lengths[0])
            if length > MAX_BODY_BYTES:
                raise HTTPProblem(413, "需求内容过长，请精简后重试。")
            if self.headers.get_content_type() != "application/json":
                raise HTTPProblem(415, "请求内容必须为 JSON。")
            raw = self.rfile.read(length)
            self._body_consumed = True
            if len(raw) != length:
                raise HTTPProblem(400, "请求内容不完整。")
            try:
                body = json.loads(raw.decode("utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError()))
            except (UnicodeDecodeError, ValueError):
                raise HTTPProblem(400, "无法读取需求，请检查输入内容。") from None
            if not isinstance(body, dict):
                raise HTTPProblem(400, "请求内容需为对象。")
            return body

        def _discard_rejected_body(self):
            # 校验 Origin/CSRF 时尚未读取 POST 正文。直接关闭 Windows socket
            # 可能发送 RST，使浏览器连 403 都收不到。只丢弃有界正文，不解析或执行。
            if self._body_consumed or self.headers.get_all("Transfer-Encoding"):
                return
            lengths = self.headers.get_all("Content-Length", [])
            if len(lengths) != 1 or not re.fullmatch(r"[0-9]+", lengths[0]):
                return
            remaining = int(lengths[0])
            if remaining > MAX_BODY_BYTES + 1:
                return
            previous_timeout = self.connection.gettimeout()
            self.connection.settimeout(0.5)
            try:
                while remaining:
                    chunk = self.rfile.read(min(remaining, 8192))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                self._body_consumed = True
            except (OSError, TimeoutError):
                pass
            finally:
                self.connection.settimeout(previous_timeout)

        def _catalog(self, kind):
            if not isinstance(kind, str) or kind not in self.server.catalogs:
                raise HTTPProblem(400, "请选择可用的资料目录。")
            return self.server.catalogs[kind]

        def _prepare(self, request, catalog):
            try:
                return prepare_request(request, catalog)["request"]
            except ValueError as error:
                raise HTTPProblem(400, str(error)) from None

        def _load(self, session_id):
            try:
                saved = self.server.store.load(session_id)
            except (FileNotFoundError, KeyError, ValueError):
                raise HTTPProblem(404, "没有找到这个会话，请检查会话编号。") from None
            if not isinstance(saved, dict):
                raise HTTPProblem(500, "会话内容无法读取。")
            self._catalog(saved.get("catalog_kind", "demo"))
            return saved

        def _route(self, *, mutation=False):
            self._check_origin(mutation=mutation)
            parsed = urlsplit(self.path)
            if parsed.scheme or parsed.netloc:
                raise HTTPProblem(400, "请求路径不合法。")
            path = parsed.path
            if not mutation and path in ("/", "/index.html"):
                return self._send(200, PAGE_PATH.read_bytes(), "text/html; charset=utf-8")
            if not mutation and path == "/api/bootstrap":
                return self._send(200, {
                    "csrf_token": self.server.csrf_token,
                    "catalogs": [{"id": kind, "label": CATALOG_LABELS[kind]} for kind in self.server.catalogs],
                    "dimensions": [{"key": key, "label": label} for key, label in DIMENSIONS.items()],
                    "default_catalog": "demo" if "demo" in self.server.catalogs else next(iter(self.server.catalogs)),
                })
            if not mutation and path == "/api/products":
                query = parse_qs(parsed.query)
                kinds = query.get("catalog", ["demo"])
                if len(kinds) != 1:
                    raise HTTPProblem(400, "请只选择一个资料目录。")
                catalog = self._catalog(kinds[0])
                return self._send(200, {"catalog": kinds[0], "products": catalog.list_products()})
            if mutation and path == "/api/sessions":
                data = self._json_body()
                kind = data.pop("catalog", "demo")
                catalog = self._catalog(kind)
                # 缺关注点或少于两个对象仍可保存，工作流会给出 needs_input。
                clean = self._prepare(data, catalog)
                session_id = self.server.store.create(clean, catalog_kind=kind)
                if not isinstance(session_id, str) or not SESSION_ID.fullmatch(session_id):
                    raise HTTPProblem(500, "会话编号生成失败。")
                return self._send(201, {"session_id": session_id, "catalog_kind": kind})
            match = re.fullmatch(r"/api/sessions/([A-Za-z0-9][A-Za-z0-9_-]{0,79})(?:/(run|report))?", path)
            if not match:
                raise HTTPProblem(404, "没有找到该页面或操作。")
            session_id, action = match.groups()
            saved = self._load(session_id)
            kind = saved.get("catalog_kind", "demo")
            if not mutation and action is None:
                return self._send(200, saved)
            if not mutation and action == "report":
                report = saved.get("result")
                if not report:
                    raise HTTPProblem(404, "这个会话还没有比较报告。")
                return self._send(200, report, filename=f"insurance-report-{session_id}.json")
            if mutation and action == "run":
                data = self._json_body()
                if set(data) - {"request", "mode", "max_calls", "catalog"}:
                    raise HTTPProblem(400, "运行参数包含不支持的字段。")
                if data.get("catalog", kind) != kind:
                    raise HTTPProblem(409, "这个会话使用另一份目录，请新建需求后比较。")
                mode = data.get("mode", "offline")
                if mode not in ("offline", "live"):
                    raise HTTPProblem(400, "请选择资料对照或模型辅助模式。")
                max_calls = data.get("max_calls", 6)
                if type(max_calls) is not int or not 1 <= max_calls <= 12:
                    raise HTTPProblem(400, "模型请求上限需为 1–12。")
                catalog = self._catalog(kind)
                request = data.get("request")
                if request is not None:
                    request = self._prepare(request, catalog)
                if not self.server.run_lock.acquire(blocking=False):
                    raise HTTPProblem(409, "已有比较正在进行，请稍后再试。")
                try:
                    report = self.server.runner(self.server.store, session_id, request=request,
                                                mode=mode, catalog=catalog, max_calls=max_calls)
                finally:
                    self.server.run_lock.release()
                return self._send(200, report)
            raise HTTPProblem(405, "此操作不支持当前请求方式。")

        def _handle(self, *, mutation=False):
            try:
                self._route(mutation=mutation)
            except HTTPProblem as error:
                self.close_connection = True
                self._discard_rejected_body()
                self._send(error.status, {"error": error.message})
            except ValueError:
                self.close_connection = True
                self._send(400, {"error": "本次输入或本地配置不符合要求，请检查后重试。"})
            except (BrokenPipeError, ConnectionResetError, TimeoutError):
                self.close_connection = True
            except Exception:
                self.close_connection = True
                self._send(500, {"error": "本次比较未完成，请检查本地配置或稍后重试。"})

        def do_GET(self):
            self._handle()

        def do_POST(self):
            self._handle(mutation=True)

        def do_OPTIONS(self):
            # 不提供 CORS 授权，跨站预检也不能触发业务动作。
            self._send(403, {"error": "不接受跨站请求。"})

    server = InsuranceServer(("127.0.0.1", port), Handler)
    server.store, server.catalogs, server.runner = store, dict(catalogs), runner
    server.authority = "127.0.0.1" + (f":{server.server_port}" if server.server_port != 80 else "")
    server.origin = f"http://{server.authority}"
    server.csrf_token = secrets.token_urlsafe(32)
    server.run_lock = threading.Lock()
    return server


def main():
    parser = argparse.ArgumentParser(description="打开本机医疗险资料比较页面")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--sessions", default="outputs/insurance-sessions", help="本地会话保存目录")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port 必须为 1–65535。")
    from .catalog import Catalog, OFFICIAL_PATH
    from .service import run_session
    from .store import SessionStore
    try:
        server = create_server(store=SessionStore(args.sessions),
                               catalogs={"demo": Catalog(), "official": Catalog(OFFICIAL_PATH)},
                               runner=run_session, port=args.port)
    except (OSError, ValueError):
        print("无法启动本地页面，请检查资料目录或端口是否被占用。")
        return 1
    print(f"医疗险资料比较：{server.origin}")
    print("默认直接对照资料。页面中启用模型辅助后，才会请求配置的 API。按 Ctrl+C 停止。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
