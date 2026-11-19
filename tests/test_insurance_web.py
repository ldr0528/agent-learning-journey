"""本机 HTTP 边界与页面连接；使用假服务，不读取密钥或请求模型。"""

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import http.client
import json
import threading
import unittest

from agent_learning.insurance.web import MAX_BODY_BYTES, create_server


class MemoryStore:
    def __init__(self):
        self.items = {}

    def create(self, request, catalog_kind="demo"):
        session_id = f"session_{len(self.items) + 1}"
        self.items[session_id] = {"id": session_id, "request": deepcopy(request),
                                  "catalog_kind": catalog_kind, "result": None,
                                  "revision": 0, "history": []}
        return session_id

    def save(self, session_id, result):
        self.items[session_id]["result"] = deepcopy(result)
        self.items[session_id]["request"] = deepcopy(result["request"])
        self.items[session_id]["revision"] += 1

    def load(self, session_id):
        return deepcopy(self.items[session_id])


class ExampleCatalog:
    def __init__(self, kind):
        self.kind = kind
        self.fingerprint = "fake-" + kind
        self.products = [{"product_id": f"{kind}_{i}", "version": "v1", "name": f"资料 {i}",
                          "data_kind": "synthetic" if kind == "demo" else "official_excerpt",
                          "source": {"title": "测试来源", "url": ""}} for i in range(1, 4)]

    def list_products(self):
        return deepcopy(self.products)

    def get_product(self, product_id, version):
        for product in self.products:
            if (product_id, version) == (product["product_id"], product["version"]):
                return deepcopy(product)
        raise ValueError("产品或资料版本不存在。")


class InsuranceWebTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.calls = []
        self.catalogs = {kind: ExampleCatalog(kind) for kind in ("demo", "official")}

        def runner(store, session_id, *, request=None, mode="offline", catalog=None, max_calls=6):
            self.calls.append({"id": session_id, "request": deepcopy(request), "mode": mode,
                               "catalog": catalog.kind, "max_calls": max_calls})
            request = request or store.load(session_id)["request"]
            result = {"session_id": session_id, "request": request,
                      "status": "completed" if len(request["selections"]) >= 2 else "needs_input",
                      "rows": [], "sources": [], "questions": [], "trace": [],
                      "model_calls": int(mode == "live"), "tool_calls": 0}
            store.save(session_id, result)
            return result

        self.server = create_server(store=self.store, catalogs=self.catalogs, runner=runner, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = self.server.origin
        self.csrf = self.get("/api/bootstrap")[2]["csrf_token"]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def request(self, method, path, *, data=None, headers=None, raw=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        request_headers = dict(headers or {})
        body = raw
        if data is not None:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
        try:
            connection.request(method, path, body=body, headers=request_headers)
            response = connection.getresponse()
            output = response.read()
            response_headers = dict(response.getheaders())
            if "application/json" in response_headers.get("Content-Type", ""):
                output = json.loads(output)
            return response.status, response_headers, output
        finally:
            connection.close()

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, data, *, headers=None):
        trusted = {"Origin": self.origin, "X-CSRF-Token": self.csrf}
        trusted.update(headers or {})
        return self.request("POST", path, data=data, headers=trusted)

    def payload(self, kind="demo"):
        return {"catalog": kind, "question": "比较保障条件。", "profile": {
            "focus": ["coverage", "renewal"], "age": None, "annual_budget": None,
            "social_insurance": "unknown"},
            "selections": [{"product_id": f"{kind}_{i}", "version": "v1"} for i in (1, 2)]}

    def create(self, kind="demo"):
        status, _, body = self.post("/api/sessions", self.payload(kind))
        self.assertEqual(status, 201)
        return body["session_id"]

    def test_page_is_local_only_and_static_paths_are_fixed(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        status, headers, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("医疗险资料比较".encode(), body)
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertNotIn(b'<script src="https:', body)
        for path in ("/../.env", "/%2e%2e/.env", "/static/index.html", "/api/sessions/../report"):
            with self.subTest(path=path):
                self.assertEqual(self.get(path)[0], 404)

    def test_host_and_origin_reject_cross_site_reads(self):
        self.assertEqual(self.get("/api/bootstrap", headers={"Host": "evil.example"})[0], 403)
        self.assertEqual(self.get("/api/bootstrap", headers={"Origin": "https://evil.example"})[0], 403)
        self.assertEqual(self.get("/api/bootstrap", headers={"Sec-Fetch-Site": "cross-site"})[0], 403)

    def test_mutations_require_both_origin_and_csrf(self):
        request = self.payload()
        variants = ({}, {"Origin": self.origin}, {"X-CSRF-Token": self.csrf},
                    {"Origin": self.origin, "X-CSRF-Token": "wrong"},
                    {"Origin": "https://evil.example", "X-CSRF-Token": self.csrf})
        for headers in variants:
            with self.subTest(headers=list(headers)):
                status, _, _ = self.request("POST", "/api/sessions", data=request, headers=headers)
                self.assertEqual(status, 403)
        self.assertEqual(self.store.items, {})
        self.assertEqual(self.calls, [])

    def test_early_rejection_delivers_403_with_in_flight_request_bodies(self):
        # 模拟多页同时提交：正文仍在传输时拒绝，不能以 TCP reset 吞掉错误响应。
        body = json.dumps({"question": "x" * 60000}).encode()
        def rejected_request(_):
            return self.request("POST", "/api/sessions", raw=body,
                                headers={"Content-Type": "application/json"})
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(rejected_request, range(16)))
        for status, headers, response in results:
            self.assertEqual(status, 403)
            self.assertEqual(headers["Connection"], "close")
            self.assertIn("error", response)
        self.assertEqual(self.store.items, {})
        self.assertEqual(self.calls, [])

    def test_live_is_explicit_and_never_runs_from_get_or_bad_csrf(self):
        session_id = self.create()
        route = f"/api/sessions/{session_id}/run"
        self.assertEqual(self.post(route, {})[0], 200)
        self.assertEqual(self.calls[-1]["mode"], "offline")
        self.assertEqual(self.get(route)[0], 405)
        self.assertEqual(self.post(route, {"mode": "live"}, headers={"X-CSRF-Token": "wrong"})[0], 403)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.post(route, {"mode": "live"})[0], 200)
        self.assertEqual(self.calls[-1]["mode"], "live")

    def test_incomplete_needs_can_be_saved_and_run(self):
        status, _, created = self.post("/api/sessions", {"catalog": "demo"})
        self.assertEqual(status, 201)
        status, _, result = self.post(f'/api/sessions/{created["session_id"]}/run', {})
        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "needs_input")
        self.assertEqual(result["request"]["selections"], [])

    def test_restore_and_update_keep_original_catalog(self):
        session_id = self.create("official")
        status, _, saved = self.get(f"/api/sessions/{session_id}")
        self.assertEqual(status, 200)
        self.assertEqual(saved["catalog_kind"], "official")
        changed = self.payload("official")
        changed.pop("catalog")
        changed["profile"]["annual_budget"] = 2500
        status, _, result = self.post(f"/api/sessions/{session_id}/run", {"request": changed})
        self.assertEqual(status, 200)
        self.assertEqual(self.calls[-1]["catalog"], "official")
        self.assertEqual(result["request"]["profile"]["annual_budget"], 2500)
        self.assertEqual(self.store.load(session_id)["request"], result["request"])
        status, _, _ = self.post(f"/api/sessions/{session_id}/run", {"catalog": "demo"})
        self.assertEqual(status, 409)
        self.assertEqual(len(self.calls), 1)

    def test_catalog_and_version_validation_is_delegated_to_core(self):
        bad = self.payload()
        bad["selections"][0]["version"] = "not-a-version"
        self.assertEqual(self.post("/api/sessions", bad)[0], 400)
        self.assertEqual(self.post("/api/sessions", {"catalog": []})[0], 400)
        self.assertEqual(self.get("/api/products?catalog=../../.env")[0], 400)
        self.assertEqual(self.store.items, {})

    def test_oversized_and_non_json_bodies_do_not_reach_service(self):
        trusted = {"Origin": self.origin, "X-CSRF-Token": self.csrf, "Content-Type": "application/json"}
        response = self.request("POST", "/api/sessions", raw=b" " * (MAX_BODY_BYTES + 1), headers=trusted)
        self.assertEqual(response[0], 413)
        self.assertEqual(self.request("POST", "/api/sessions", raw=b"{broken", headers=trusted)[0], 400)
        self.assertEqual(self.request("POST", "/api/sessions", raw=b'{"age":NaN}', headers=trusted)[0], 400)
        trusted["Content-Type"] = "text/plain"
        self.assertEqual(self.request("POST", "/api/sessions", raw=b"{}", headers=trusted)[0], 415)
        self.assertEqual(self.store.items, {})

    def test_duplicate_or_unbounded_runs_are_rejected(self):
        session_id = self.create()
        route = f"/api/sessions/{session_id}/run"
        self.server.run_lock.acquire()
        try:
            self.assertEqual(self.post(route, {"mode": "live"})[0], 409)
        finally:
            self.server.run_lock.release()
        for value in (0, 13, True, 1.5):
            with self.subTest(value=value):
                self.assertEqual(self.post(route, {"max_calls": value})[0], 400)
        self.assertEqual(self.calls, [])

    def test_report_download_and_unknown_session(self):
        session_id = self.create()
        self.assertEqual(self.get(f"/api/sessions/{session_id}/report")[0], 404)
        self.post(f"/api/sessions/{session_id}/run", {})
        status, headers, result = self.get(f"/api/sessions/{session_id}/report")
        self.assertEqual(status, 200)
        self.assertIn("attachment", headers["Content-Disposition"])
        self.assertEqual(result["session_id"], session_id)
        self.assertEqual(self.get("/api/sessions/not-found")[0], 404)

    def test_unexpected_service_errors_do_not_expose_private_error_text(self):
        session_id = self.create()

        def fail(*args, **kwargs):
            raise RuntimeError("private-response-and-key-sentinel")

        self.server.runner = fail
        status, _, result = self.post(f"/api/sessions/{session_id}/run", {"mode": "live"})
        self.assertEqual(status, 500)
        self.assertNotIn("private-response", result["error"])
        self.assertFalse(self.server.run_lock.locked())


if __name__ == "__main__":
    unittest.main()
