"""咨询边界：提取需确认、数值有原话、追问受报告版本与证据限制。"""

from copy import deepcopy
import json
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

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

    def test_budget_edit_does_not_replace_existing_focus(self):
        message = "年度预算改为3000元，另外关注医院范围"
        for mode in ("offline", "live"):
            with self.subTest(mode=mode):
                result = propose_needs(self.record, message, self.catalog, mode=mode,
                    request_model=model_reply("propose_needs", {
                        "profile": {"annual_budget": 3000, "focus": ["hospital"]},
                        "evidence": {"annual_budget": "年度预算改为3000元", "focus": message}}))
                profile = result["proposal"]["request"]["profile"]
                self.assertEqual(profile["annual_budget"], 3000)
                self.assertTrue({"coverage", "renewal", "hospital"} <= set(profile["focus"]))

    def test_explicit_focus_removal_and_replacement_preserve_other_fields(self):
        for message, expected in (("不再关注门诊", ["renewal"]),
                                  ("只关注医院范围", ["hospital"]),
                                  ("不只是关注门诊，还想了解医院", ["coverage", "renewal", "hospital"])):
            with self.subTest(message=message):
                result = propose_needs(self.record, message, self.catalog)
                profile = result["proposal"]["request"]["profile"]
                self.assertEqual(profile["focus"], expected)
                self.assertEqual(profile["annual_budget"], 2000)
        result = propose_needs(self.record, "不再关注门诊", self.catalog, mode="live",
            request_model=model_reply("propose_needs", {"profile": {"focus": []}, "evidence": {"focus": "不再关注门诊"}}))
        self.assertEqual(result["proposal"]["request"]["profile"]["focus"], ["renewal"])

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

    def test_incomplete_report_followup_never_initializes_model(self):
        for status in ("needs_input", "cancelled", "model_error", "call_limit", "tool_limit"):
            with self.subTest(status=status), TemporaryDirectory() as directory:
                store = SessionStore(directory)
                session = store.create(REQUEST)
                report = deepcopy(self.record["result"])
                report["status"] = status
                store.save(session, report)
                with patch("agent_learning.insurance.service.load_settings") as settings:
                    result = run_message(store, session, "医院范围怎样", intent="followup", mode="live")
                self.assertEqual(result["status"], "needs_report")
                self.assertEqual(result["model_calls"], 0)
                settings.assert_not_called()

    def test_large_offline_followup_is_partial_and_keeps_each_product(self):
        request = deepcopy(REQUEST)
        request["selections"].append({"product_id": "demo_renewal", "version": "demo-v1"})
        record = {**self.record, "result": run_comparison(request)}
        result = answer_report(record, "比较保障、免赔额、赔付比例、医院和等待期")
        self.assertEqual(result["status"], "partial_answer")
        self.assertEqual(len(result["sources"]), 8)
        self.assertEqual({f["product_id"] for f in result["sources"]}, {s["product_id"] for s in request["selections"]})

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

    def test_message_capacity_is_checked_before_model_and_preserves_last_report(self):
        with TemporaryDirectory() as directory:
            store = SessionStore(directory)
            session = store.create(REQUEST)
            for _ in range(199):
                store.append_message(session, "user", "历史消息")
            with patch("agent_learning.insurance.service.load_settings") as settings:
                with self.assertRaises(ValueError):
                    run_message(store, session, "关注医院", mode="live")
                settings.assert_not_called()
            self.assertEqual(len(store.load(session)["messages"]), 199)
            # 比较只需要一条结果消息，仍可使用最后一个位置。
            report = run_session(store, session)
            self.assertEqual(len(store.load(session)["messages"]), 200)
            with patch("agent_learning.insurance.service.load_settings") as settings:
                with self.assertRaises(ValueError):
                    run_session(store, session, mode="live")
                settings.assert_not_called()
            self.assertEqual(store.load(session)["result"], report)

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
