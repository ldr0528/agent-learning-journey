"""咨询边界：提取需确认、数值有原话、追问受报告版本与证据限制。"""

from copy import deepcopy
import json
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
import unittest

from agent_learning.insurance.catalog import Catalog, DIMENSIONS
from agent_learning.insurance.conversation import propose_needs, answer_report
from agent_learning.insurance.service import run_message, run_session
from agent_learning.insurance.store import SessionStore
from agent_learning.insurance.workflow import run_comparison


REQUEST = {"question": "比较门诊和续保", "profile": {"focus": ["coverage", "renewal"], "annual_budget": 2000},
           "selections": [{"product_id": "demo_hospital", "version": "demo-v1"},
                          {"product_id": "demo_outpatient", "version": "demo-v1"}]}


def model_reply(name, data):
    def model(messages, tools):
        return NS(choices=[NS(finish_reason="tool_calls", message=NS(content=None, tool_calls=[
            NS(id="turn-tool", function=NS(name=name, arguments=json.dumps(data, ensure_ascii=False))) ]))], usage=None)
    return model


class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.catalog = Catalog()
        self.record = {"request": deepcopy(REQUEST), "brief_version": 1, "result_brief_version": 1,
                       "revision": 1, "result": run_comparison(REQUEST)}

    def test_proposal_does_not_mutate_confirmed_request_or_choose_products(self):
        before = deepcopy(self.record)
        result = propose_needs(self.record, "我30岁，有医保，年预算3000元，关注医院", self.catalog)
        profile = result["proposal"]["request"]["profile"]
        self.assertEqual(profile["age"], 30)
        self.assertEqual(profile["annual_budget"], 3000)
        self.assertEqual(profile["social_insurance"], "yes")
        self.assertEqual(result["proposal"]["request"]["selections"], REQUEST["selections"])
        self.assertEqual(self.record, before)

    def test_unconfirmed_clarification_carries_previous_draft(self):
        record = {"request": {}, "brief_version": 1}
        record["proposal"] = propose_needs(record, "我30岁", self.catalog)["proposal"]
        second = propose_needs(record, "关注普通门诊和续保", self.catalog)
        self.assertEqual(second["proposal"]["request"]["profile"]["age"], 30)
        self.assertEqual(second["proposal"]["request"]["profile"]["focus"], ["coverage", "renewal"])

    def test_live_extraction_requires_current_message_quotes(self):
        result = propose_needs(self.record, "年度预算改为2千元", self.catalog, mode="live",
            request_model=model_reply("propose_needs", {"profile": {"annual_budget": 2000},
                                                       "evidence": {"annual_budget": "2千元"}}))
        self.assertEqual(result["model_calls"], 1)
        for data in ({"profile": {"age": 30}, "evidence": {"age": "没说过"}},
                     {"profile": {"annual_budget": 9000}, "evidence": {"annual_budget": "2千元"}},
                     {"profile": {"social_insurance": "yes"}, "evidence": {"social_insurance": "我在上班"}}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                propose_needs(self.record, "我在上班，年度预算改为2千元", self.catalog, mode="live",
                              request_model=model_reply("propose_needs", data))

    def test_ambiguous_multiple_ages_are_not_auto_selected(self):
        result = propose_needs({"request": {}, "brief_version": 1}, "我30岁，妈妈60岁，想了解续保", self.catalog)
        self.assertIsNone(result["proposal"]["request"]["profile"]["age"])
        self.assertIn("多个年龄", result["content"])

    def test_followup_returns_canonical_conditions_and_not_model_prose(self):
        ids = [f["evidence_id"] for f in self.record["result"]["sources"] if f["dimension"] == "renewal"]
        result = answer_report(self.record, "续保条件怎样？", mode="live",
                               request_model=model_reply("select_report_evidence", {"evidence_ids": ids, "answerable": True}))
        self.assertEqual(result["evidence_ids"], ids)
        for fact in result["sources"]:
            self.assertIn(fact["text"], result["content"])
            self.assertTrue(all(condition in result["content"] for condition in fact["conditions"]))
        self.assertEqual(result["report_revision"], 1)

    def test_unknown_price_and_individual_decisions_remain_partial(self):
        for dimension, question in (("premium", "预算2000元够吗"), ("underwriting", "我能否投保？")):
            ids = [f["evidence_id"] for f in self.record["result"]["sources"] if f["dimension"] == dimension]
            result = answer_report(self.record, question, mode="live",
                request_model=model_reply("select_report_evidence", {"evidence_ids": ids, "answerable": True}))
            self.assertEqual(result["status"], "partial_answer")

    def test_foreign_and_invented_citations_are_rejected(self):
        for ids in (["INVENTED"], ["DEMO-RENEWAL-V1-COVERAGE"], [], [self.record["result"]["sources"][0]["evidence_id"]] * 2):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                answer_report(self.record, "比较保障", mode="live",
                    request_model=model_reply("select_report_evidence", {"evidence_ids": ids, "answerable": True}))

    def test_stale_report_never_calls_model(self):
        self.record["brief_version"] = 2
        result = answer_report(self.record, "普通门诊", mode="live",
                               request_model=lambda *_: self.fail("旧报告不得发起模型请求"))
        self.assertEqual(result["status"], "needs_report")
        self.assertEqual(result["model_calls"], 0)

    def test_service_saves_conversation_without_applying_proposal(self):
        with TemporaryDirectory() as directory:
            store = SessionStore(directory)
            session = store.create(REQUEST)
            result = run_message(store, session, "预算改成3000元", mode="offline", expected_version=1)
            saved = store.load(session)
            self.assertEqual(saved["request"]["profile"]["annual_budget"], 2000)
            self.assertEqual(saved["proposal"]["request"]["profile"]["annual_budget"], 3000)
            self.assertEqual([x["role"] for x in saved["messages"]], ["user", "assistant"])
            self.assertEqual(result["status"], "needs_confirmation")

    def test_transport_failure_is_saved_without_sensitive_error(self):
        def broken(*_):
            raise RuntimeError("DO_NOT_EXPOSE_SECRET")
        with TemporaryDirectory() as directory:
            store = SessionStore(directory)
            session = store.create(REQUEST)
            result = run_message(store, session, "关注续保", mode="live", request_model=broken)
            self.assertEqual(result["status"], "model_error")
            self.assertEqual(result["model_calls"], 1)
            self.assertNotIn("DO_NOT_EXPOSE_SECRET", json.dumps(store.load(session)))

    def test_cancel_after_model_response_prevents_tool_execution(self):
        cancelled = []
        def model(*_):
            cancelled.append(True)
            return model_reply("read_product_clauses", {**REQUEST["selections"][0], "dimensions": list(DIMENSIONS)})(None, None)
        events = []
        report = run_comparison(REQUEST, mode="live", request_model=model, on_event=events.append,
                                should_cancel=lambda: bool(cancelled))
        self.assertEqual(report["status"], "cancelled")
        self.assertEqual(report["model_calls"], 1)
        self.assertEqual(report["tool_calls"], 0)
        self.assertFalse(report["sources"])
        self.assertEqual(events[0]["type"], "checking_request")


if __name__ == "__main__":
    unittest.main()
