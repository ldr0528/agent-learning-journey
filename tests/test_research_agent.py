"""离线检查资料回传、来源范围与预算；不是模型答案质量评估。"""

import contextlib
from copy import deepcopy
import io
import unittest
from unittest.mock import patch

from agent_learning.agents.research import run_research


class ResearchAgentTests(unittest.TestCase):
    def run_sequence(self, replies, max_steps=5):
        replies = iter(replies)
        requests = []

        def fake_model(client, model, messages, options):
            requests.append(deepcopy(messages))
            return next(replies)

        with patch("agent_learning.loop.ask_model", side_effect=fake_model), contextlib.redirect_stdout(io.StringIO()):
            result = run_research(None, "mock", "Agent Loop 为什么要有最大步数？", {}, max_steps)
        return result, requests

    def test_search_observation_reaches_model_and_sources_come_from_file(self):
        result, requests = self.run_sequence([
            'Action: search_notes(query="Agent Loop 为什么要有最大步数？")',
            'Action: Finish[最大步数限制执行预算，防止持续运行和资源耗尽。[N03]]',
        ])
        self.assertEqual((result["status"], result["steps"], result["tool_calls"]), ("finished", 2, 1))
        self.assertIn("[N01]", requests[1][-1]["content"])
        self.assertIn("[N03]", requests[1][-1]["content"])
        self.assertEqual([note["id"] for note in result["sources"]], ["N03"])
        self.assertIn("docs/chapter4/", result["sources"][0]["source_url"])

    def test_finish_before_search_is_rejected_then_can_recover(self):
        result, requests = self.run_sequence([
            'Action: Finish[资料不足。]',
            'Action: search_notes(query="最大步数")',
            'Action: Finish[限制执行预算。[N03]]',
        ])
        self.assertIn("请先调用 search_notes", requests[1][-1]["content"])
        self.assertEqual((result["steps"], result["tool_calls"]), (3, 1))

    def test_citation_spaces_are_allowed_but_unknown_ids_are_still_rejected(self):
        result, requests = self.run_sequence([
            'Action: search_notes(query="最大步数")',
            'Action: Finish[限制预算。[ N99 ]]',
            'Action: Finish[限制预算。[ N03 ]]',
        ])
        self.assertIn("本次检索未返回的编号：N99", requests[2][-1]["content"])
        self.assertEqual(result["status"], "finished")
        self.assertEqual([note["id"] for note in result["sources"]], ["N03"])

    def test_existing_but_unretrieved_id_is_rejected_and_correction_uses_a_step(self):
        result, requests = self.run_sequence([
            'Action: search_notes(query="最大步数")',
            'Action: Finish[限制预算。[N01]]',
            'Action: Finish[限制预算。[N03]]',
        ])
        self.assertIn("本次检索未返回的编号：N01", requests[2][-1]["content"])
        self.assertEqual((result["steps"], result["tool_calls"]), (3, 1))
        self.assertEqual([note["id"] for note in result["sources"]], ["N03"])

    def test_missing_citation_does_not_bypass_step_limit(self):
        result, requests = self.run_sequence([
            'Action: search_notes(query="最大步数")',
            'Action: Finish[限制预算。]',
        ], max_steps=2)
        self.assertEqual(len(requests), 2)
        self.assertEqual(result["status"], "step_limit")
        self.assertIsNone(result["answer"])
        self.assertEqual(result["sources"], [])

    def test_no_match_can_finish_with_explicit_insufficient_evidence(self):
        result, requests = self.run_sequence([
            'Action: search_notes(query="广州天气")',
            'Action: Finish[资料不足：本地摘要未匹配到广州天气，无法据此回答。]',
        ])
        self.assertIn("没有匹配到本地摘要", requests[1][-1]["content"])
        self.assertEqual(result["status"], "finished")
        self.assertEqual(result["sources"], [])

    def test_invalid_tool_is_not_executed_or_counted(self):
        result, requests = self.run_sequence([
            'Action: get_weather(city="上海")',
            'Action: search_notes(query="最大步数")',
            'Action: Finish[限制预算。[N03]]',
        ])
        self.assertIn("错误：无法识别 Action", requests[1][-1]["content"])
        self.assertEqual(result["tool_calls"], 1)

    def test_prefixed_finish_then_missing_citation_can_recover_without_new_search(self):
        from agent_learning.tools.notes import search_notes

        with patch("agent_learning.agents.research.search_notes", wraps=search_notes) as search:
            result, requests = self.run_sequence([
                'Action: search_notes(query="Action Observation 产生者")',
                'Action 由模型产生，Observation 由程序组织。[N02]\n\n'
                'Action: Finish[Action 由模型产生，Observation 由程序组织。]',
                'Action: Finish[Action 由模型产生，Observation 由程序组织。]',
                'Action: Finish[Action 由模型产生，Observation 由程序组织。[N02]]',
            ])
        search.assert_called_once()
        format_error = requests[2][-1]["content"]
        self.assertIn("删除 Finish 外的文字", format_error)
        self.assertIn("不是检索失败", format_error)
        self.assertIn("[N02]", format_error)
        citation_error = requests[3][-1]["content"]
        self.assertIn("Finish 内的最终答案缺少引用编号", citation_error)
        self.assertIn("[N02]", citation_error)
        self.assertEqual((result["status"], result["steps"], result["tool_calls"]), ("finished", 4, 1))
        self.assertEqual([note["id"] for note in result["sources"]], ["N02"])

    def test_prefixed_insufficient_evidence_reply_gets_finish_guidance_without_citations(self):
        result, requests = self.run_sequence([
            'Action: search_notes(query="LangGraph checkpoint")',
            '资料不足。\nAction: Finish[资料不足：未检索到 checkpoint 资料。]',
            'Action: Finish[资料不足：未检索到 checkpoint 资料。]',
        ])
        self.assertIn("Action: Finish[资料不足", requests[2][-1]["content"])
        self.assertIn("不要编造引用", requests[2][-1]["content"])
        self.assertEqual(result["status"], "finished")
        self.assertEqual(result["sources"], [])

    def test_repeated_query_does_not_execute_tool_twice(self):
        from agent_learning.tools.notes import search_notes

        with patch("agent_learning.agents.research.search_notes", wraps=search_notes) as search:
            result, requests = self.run_sequence([
                'Action: search_notes(query="Action Observation 产生者")',
                'Action: search_notes(query="  action   observation  产生者  ")',
                'Action: Finish[Action 由模型提出，程序组织 Observation。[N02]]',
            ])
        search.assert_called_once()
        self.assertIn("本次未重复执行工具", requests[2][-1]["content"])
        self.assertIn("[N02]", requests[2][-1]["content"])
        self.assertEqual((result["status"], result["steps"], result["tool_calls"]), ("finished", 3, 1))

    def test_sources_do_not_leak_from_previous_run(self):
        self.run_sequence([
            'Action: search_notes(query="最大步数")',
            'Action: Finish[限制预算。[N03]]',
        ])
        result, _ = self.run_sequence([
            'Action: search_notes(query="广州天气")',
            'Action: Finish[广州晴天。[N03]]',
        ], max_steps=2)
        self.assertEqual(result["status"], "step_limit")
        self.assertEqual(result["sources"], [])


if __name__ == "__main__":
    unittest.main()
