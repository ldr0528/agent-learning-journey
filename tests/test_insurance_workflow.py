"""业务证据边界、预算、纠错与会话恢复的回归场景，不请求模型。"""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
import unittest

from agent_learning.insurance.agent import execute_tool
from agent_learning.insurance.catalog import Catalog, DIMENSIONS
from agent_learning.insurance.service import run_session
from agent_learning.insurance.store import SessionStore
from agent_learning.insurance.workflow import EvidenceWorkspace, prepare_request, render_markdown, run_comparison


REQUEST = {"question": "比较普通门诊与续保，并说明预算是否够用。",
           "profile": {"focus": ["coverage", "renewal"], "annual_budget": 2000, "age": 30},
           "selections": [{"product_id": "demo_hospital", "version": "demo-v1"},
                          {"product_id": "demo_outpatient", "version": "demo-v1"}]}


def reply(name, arguments, call_id):
    call = NS(id=call_id, function=NS(name=name, arguments=json.dumps(arguments, ensure_ascii=False)))
    return NS(choices=[NS(finish_reason="tool_calls", message=NS(content=None, tool_calls=[call]))], usage=None)


def scripted_model(catalog, *, invalid_finish=False):
    steps = [reply("read_product_clauses", {**item, "dimensions": list(DIMENSIONS)}, f"call-{i}")
             for i, item in enumerate(REQUEST["selections"])]
    ids = [f["evidence_id"] for item in REQUEST["selections"]
           for f in catalog.get_product(**item)["facts"]]
    if invalid_finish:
        steps.append(reply("finish_comparison", {"evidence_ids": ids + ["INVENTED"]}, "bad"))
    steps.append(reply("finish_comparison", {"evidence_ids": ids}, "finish"))
    requests = []

    def request(messages, tools):
        requests.append(deepcopy(messages))
        return steps.pop(0)
    return request, requests


class InsuranceWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.catalog = Catalog()

    def test_clarification_happens_before_any_model_call(self):
        def forbidden(*args):
            self.fail("不应请求模型")
        report = run_comparison({}, mode="live", request_model=forbidden)
        self.assertEqual(report["status"], "needs_input")
        self.assertEqual(report["model_calls"], 0)
        self.assertEqual(len(report["questions"]), 2)

    def test_complete_matrix_keeps_conditions_and_unknown_price(self):
        report = run_comparison(REQUEST)
        self.assertEqual(report["status"], "completed_with_gaps")
        self.assertEqual(len(report["rows"]), 9)
        self.assertEqual(len(report["sources"]), 18)
        price = next(row for row in report["rows"] if row["dimension"] == "premium")
        self.assertTrue(all(c["status"] == "unknown" for c in price["cells"]))
        self.assertIn("不判定任何产品是否符合预算", " ".join(report["gaps"]))
        self.assertTrue(all(c["conditions"] for row in report["rows"] for c in row["cells"]))

    def test_preserves_user_focus_order_without_omitting_other_dimensions(self):
        request = deepcopy(REQUEST)
        request["profile"]["focus"] = ["waiting_period", "hospital"]
        report = run_comparison(request)
        self.assertEqual([r["dimension"] for r in report["rows"][:2]], request["profile"]["focus"])
        self.assertEqual({r["dimension"] for r in report["rows"]}, set(DIMENSIONS))

    def test_product_version_and_out_of_scope_reads_are_rejected(self):
        workspace = EvidenceWorkspace(REQUEST)
        with self.assertRaises(ValueError):
            workspace.read_dimensions("demo_renewal", "demo-v1", ["coverage"])
        with self.assertRaises(ValueError):
            workspace.read_dimensions("demo_hospital", "another-version", ["coverage"])
        self.assertFalse(workspace.evidence)

    def test_registered_but_unread_evidence_cannot_be_cited(self):
        workspace = EvidenceWorkspace(REQUEST)
        ids = [x["evidence_id"] for x in self.catalog.get_product("demo_hospital", "demo-v1")["facts"]]
        with self.assertRaisesRegex(ValueError, "没有返回"):
            workspace.finish(ids)

    def test_early_finish_requires_other_product_and_restrictions(self):
        workspace = EvidenceWorkspace(REQUEST)
        facts = workspace.read_dimensions("demo_hospital", "demo-v1", ["coverage"])
        with self.assertRaisesRegex(ValueError, "尚未齐全"):
            workspace.finish([x["evidence_id"] for x in facts])

    def test_tampered_tool_evidence_is_rejected(self):
        workspace = EvidenceWorkspace(REQUEST)
        valid, fact = self.catalog.get_product("demo_hospital", "demo-v1")["facts"][:2]
        fact["text"] = "所有疾病均承保，免费。"
        with self.assertRaisesRegex(ValueError, "不一致"):
            workspace.remember([valid, fact])
        self.assertFalse(workspace.evidence)

    def test_native_tool_feedback_and_finish(self):
        model, requests = scripted_model(self.catalog)
        report = run_comparison(REQUEST, mode="live", request_model=model)
        self.assertEqual(report["status"], "completed_with_gaps")
        self.assertEqual(report["model_calls"], 3)
        self.assertEqual(report["tool_calls"], 3)
        tool_messages = [m for m in requests[1] if m["role"] == "tool"]
        self.assertEqual(len(tool_messages), 1)
        self.assertIn("DEMO-HOSP", tool_messages[0]["content"])
        self.assertIn("包含本次", requests[0][1]["content"])

    def test_invalid_citation_feedback_then_repair(self):
        model, requests = scripted_model(self.catalog, invalid_finish=True)
        report = run_comparison(REQUEST, mode="live", request_model=model)
        self.assertEqual(report["status"], "completed_with_gaps")
        self.assertEqual(report["model_calls"], 4)
        self.assertTrue(report["trace"][2]["is_error"])
        self.assertIn("没有返回", requests[3][-1]["content"])

    def test_budget_preserves_partial_evidence_without_extra_request(self):
        model, requests = scripted_model(self.catalog)
        report = run_comparison(REQUEST, mode="live", request_model=model, max_calls=1)
        self.assertEqual(report["status"], "call_limit")
        self.assertEqual(len(requests), 1)
        self.assertEqual(len(report["sources"]), 9)
        self.assertTrue(any(not c["evidence_ids"] for row in report["rows"] for c in row["cells"]))
        self.assertIn(report["error"], render_markdown(report))

    def test_tool_budget_limits_execution(self):
        model, requests = scripted_model(self.catalog)
        report = run_comparison(REQUEST, mode="live", request_model=model, max_tools=1)
        self.assertEqual(report["status"], "tool_limit")
        self.assertEqual(report["tool_calls"], 1)
        self.assertEqual(len(requests), 1)

    def test_free_text_cannot_bypass_source_validation(self):
        def model(*args):
            return NS(choices=[NS(finish_reason="stop", message=NS(content="直接购买A，全部承保。", tool_calls=[]))], usage=None)
        report = run_comparison(REQUEST, mode="live", request_model=model, max_calls=1)
        self.assertEqual(report["status"], "call_limit")
        self.assertNotIn("直接购买", render_markdown(report))

    def test_transport_failure_does_not_leak_exception_text(self):
        def model(*args):
            raise RuntimeError("SECRET_FAKE_VALUE")
        report = run_comparison(REQUEST, mode="live", request_model=model)
        self.assertEqual(report["status"], "model_error")
        self.assertNotIn("SECRET_FAKE_VALUE", json.dumps(report))

    def test_invalid_requests_and_tool_arguments(self):
        for patch in ({"age": True}, {"annual_budget": float("nan")}, {"focus": ["secret"]}):
            request = deepcopy(REQUEST)
            request["profile"].update(patch)
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                prepare_request(request, self.catalog)
        with self.assertRaises(ValueError):
            execute_tool(EvidenceWorkspace(REQUEST), "purchase", {})

    def test_source_conflicts_are_preserved_not_resolved_by_recency(self):
        from agent_learning.insurance.catalog import DEFAULT_PATH
        payload = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
        payload["products"][0]["facts"][0]["status"] = "conflict"
        payload["products"][0]["facts"][0]["text"] = "两份资料对普通门诊责任的说明冲突，待核对。"
        with TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            report = run_comparison(REQUEST, catalog=Catalog(path))
        cell = report["rows"][0]["cells"][0]
        self.assertEqual(cell["status"], "conflict")
        self.assertIn("冲突", report["next_steps"][0])

    def test_sessions_restore_update_and_keep_history(self):
        with TemporaryDirectory() as directory:
            store = SessionStore(directory)
            session_id = store.create({})
            first = run_session(store, session_id)
            self.assertEqual(first["status"], "needs_input")
            result = run_session(store, session_id, request=REQUEST)
            record = SessionStore(directory).load(session_id)
            self.assertEqual(record["result"]["rows"], result["rows"])
            self.assertEqual(record["revision"], 2)
            self.assertEqual(record["history"][0]["result"]["status"], "needs_input")
            self.assertEqual(record["request"]["selections"], REQUEST["selections"])
            with self.assertRaises(ValueError):
                store.load("../../.env")


@unittest.skipUnless(importlib.util.find_spec("langgraph"), "需要可选 graph 依赖")
class InsuranceGraphTests(unittest.TestCase):
    def test_graph_reuses_comparison_and_clarification(self):
        from agent_learning.insurance.integrations import run_graph_comparison
        graph = run_graph_comparison(REQUEST)
        self.assertEqual(graph["rows"], run_comparison(REQUEST)["rows"])
        self.assertEqual(graph["graph_nodes"], ["intake", "research", "verify", "deliver"])
        empty = run_graph_comparison({})
        self.assertEqual(empty["graph_nodes"], ["intake", "clarify", "deliver"])
        self.assertEqual(empty["model_calls"], 0)
        self.assertEqual(run_graph_comparison({}, mode="live")["mode"], "live")
        with self.assertRaises(ValueError):
            run_graph_comparison({}, mode="invalid")


@unittest.skipUnless(importlib.util.find_spec("mcp"), "需要可选 mcp 依赖")
class InsuranceMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_clarification_preserves_mode_without_starting_tool_server(self):
        from agent_learning.insurance.integrations import run_mcp_comparison
        from unittest.mock import patch
        with patch("mcp.client.stdio.stdio_client", side_effect=AssertionError("不应启动取证服务")):
            report = await run_mcp_comparison({}, mode="live")
        self.assertEqual(report["mode"], "live")
        self.assertEqual(report["status"], "needs_input")
        with self.assertRaises(ValueError):
            await run_mcp_comparison({}, mode="invalid")

    async def test_real_protocol_same_case_and_citations(self):
        from agent_learning.insurance.integrations import run_mcp_comparison
        protocol = await run_mcp_comparison(REQUEST)
        local = run_comparison(REQUEST)
        self.assertEqual(protocol["rows"], local["rows"])
        self.assertEqual(protocol["sources"], local["sources"])
        self.assertEqual(protocol["server"], "insurance-evidence")
        self.assertEqual(protocol["model_calls"], 0)

    async def test_model_tool_decisions_cross_protocol_boundary(self):
        from agent_learning.insurance.integrations import run_mcp_comparison
        model, requests = scripted_model(Catalog())
        report = await run_mcp_comparison(REQUEST, mode="live", request_model=model)
        self.assertEqual(report["status"], "completed_with_gaps")
        self.assertEqual(report["model_calls"], 3)
        self.assertEqual(report["rows"], run_comparison(REQUEST)["rows"])
        self.assertEqual([message["role"] for message in requests[1]][-1], "tool")


if __name__ == "__main__":
    unittest.main()
