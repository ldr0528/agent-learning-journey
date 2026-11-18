"""离线检查循环控制，不读取密钥、不调用外部 API。

这些是程序逻辑测试，不是模型回答质量的评估集。
"""

import contextlib
from copy import deepcopy
import io
import unittest
from unittest.mock import patch

from agent_learning.agents.weather import run_weather as run_agent
from agent_learning.context import build_weather_context


class AgentLoopTests(unittest.TestCase):
    def run_sequence(self, replies, max_steps=5, *, budget_context=False, context_mode="full"):
        replies = iter(replies)
        requests = []

        def fake_model(client, model, messages, options):
            requests.append(deepcopy(messages))
            return next(replies)

        with patch("agent_learning.loop.ask_model", side_effect=fake_model), contextlib.redirect_stdout(io.StringIO()):
            result = run_agent(None, "mock", "比较北京和上海", {}, max_steps,
                               budget_context=budget_context, context_mode=context_mode)
        return result, requests

    def test_two_tools_then_finish_preserves_both_observations(self):
        result, requests = self.run_sequence([
            'Action: get_weather(city="北京")',
            'Action: get_weather(city="上海")',
            'Action: Finish[模拟数据中上海比北京暖和10℃。]',
        ])
        self.assertEqual((result["status"], result["steps"], result["tool_calls"]), ("finished", 3, 2))
        observations = [m["content"] for m in requests[2] if m["content"].startswith("Observation:")]
        self.assertEqual(observations, ["Observation: 下雨，12℃", "Observation: 晴天，22℃"])

    def test_step_limit_does_not_make_extra_request_or_claim_answer(self):
        result, requests = self.run_sequence(['Action: get_weather(city="北京")'] * 2, max_steps=2)
        self.assertEqual(len(requests), 2)
        self.assertEqual(result["status"], "step_limit")
        self.assertIsNone(result["answer"])

    def test_invalid_action_returns_error_then_can_finish_without_tool(self):
        result, requests = self.run_sequence(['Action: unknown_tool()', 'Action: Finish[工具不可用。]'])
        self.assertTrue(requests[1][-1]["content"].startswith("Observation: 错误："))
        self.assertEqual(result["tool_calls"], 0)
        self.assertEqual(result["status"], "finished")

    def test_missing_city_data_is_preserved(self):
        result, requests = self.run_sequence(['Action: get_weather(city="广州")', 'Action: Finish[模拟数据中暂无广州天气。]'])
        self.assertEqual(requests[1][-1]["content"], "Observation: 暂无天气数据")
        self.assertEqual(result["tool_calls"], 1)

    def test_budget_context_updates_without_accumulating_or_losing_history(self):
        replies = [
            'Action: get_weather(city="北京")',
            'Action: get_weather(city="上海")',
            'Action: Finish[模拟数据中上海更暖和。]',
        ]
        baseline_result, baseline_requests = self.run_sequence(replies, max_steps=3)
        result, requests = self.run_sequence(replies, max_steps=3, budget_context=True)
        expected_hints = [
            "运行预算：本轮是第 1/3 次模型请求，包含本次，还可以请求模型 3 次。",
            "运行预算：本轮是第 2/3 次模型请求，包含本次，还可以请求模型 2 次。",
            "运行预算：本轮是第 3/3 次模型请求，包含本次，还可以请求模型 1 次。",
        ]
        self.assertEqual(len(requests), 3)
        for request, baseline, hint in zip(requests, baseline_requests, expected_hints):
            self.assertEqual(request[:-1], baseline)
            self.assertEqual(request[-1], {"role": "user", "content": hint})
        self.assertEqual(result, baseline_result)

    def test_budget_context_does_not_extend_request_limit(self):
        result, requests = self.run_sequence([
            'Action: get_weather(city="北京")',
            'Action: get_weather(city="上海")',
        ], max_steps=2, budget_context=True)
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[-1][-1]["content"],
                         "运行预算：本轮是第 2/2 次模型请求，包含本次，还可以请求模型 1 次。")
        self.assertEqual(result, {
            "status": "step_limit", "answer": None, "steps": 2, "tool_calls": 2,
        })

    def test_summary_and_budget_preserve_evidence_across_rounds(self):
        replies = [
            'Action: get_weather(city="北京")',
            'Action: get_weather(city="上海")',
            'Action: get_weather(city="广州")',
            'Action: Finish[模拟天气中上海比北京暖和，广州资料不足。]',
        ]
        baseline, full = self.run_sequence(replies, max_steps=4, budget_context=True)
        result, requests = self.run_sequence(replies, max_steps=4, budget_context=True,
                                             context_mode="summary")
        self.assertEqual(result, baseline)
        self.assertEqual(requests[:2], full[:2])
        for index in (2, 3):
            self.assertEqual(requests[index][:2], full[index][:2])
            self.assertEqual(requests[index][-3:], full[index][-3:])
            self.assertEqual(len(requests[index]), 6)
        self.assertIn('北京：下雨，12℃（来源：get_weather(city="北京")）', requests[2][2]["content"])
        final_summary = requests[3][2]["content"]
        self.assertEqual(final_summary.count('北京：下雨，12℃'), 1)
        self.assertEqual(final_summary.count('上海：晴天，22℃'), 1)
        self.assertIn('get_weather(city="上海")', final_summary)
        self.assertNotIn("运行预算", final_summary)

    def test_summary_keeps_missing_city_result(self):
        result, requests = self.run_sequence([
            'Action: get_weather(city="广州")',
            'Action: get_weather(city="上海")',
            'Action: Finish[模拟数据缺少广州天气，无法比较。]',
        ], max_steps=3, context_mode="summary")
        self.assertIn('广州：暂无天气数据（来源：get_weather(city="广州")）', requests[2][2]["content"])
        self.assertEqual(requests[2][-1]["content"], "Observation: 晴天，22℃")
        self.assertEqual((result["steps"], result["tool_calls"]), (3, 2))

    def test_summary_preserves_unrecognized_history_in_full(self):
        replies = [
            'Action: unknown_tool()',
            'Action: get_weather(city="北京")',
            'Action: get_weather(city="上海")',
            'Action: Finish[模拟数据中上海更暖和。]',
        ]
        baseline, full = self.run_sequence(replies, budget_context=True)
        result, requests = self.run_sequence(replies, budget_context=True, context_mode="summary")
        self.assertEqual(requests, full)
        self.assertEqual(result, baseline)
        self.assertEqual(result["tool_calls"], 2)

    def test_weather_context_keeps_original_history_unchanged(self):
        _, requests = self.run_sequence([
            'Action: get_weather(city="北京")',
            'Action: get_weather(city="上海")',
            'Action: Finish[模拟数据中上海更暖和。]',
        ])
        messages = requests[2]
        original = deepcopy(messages)
        with contextlib.redirect_stdout(io.StringIO()):
            selected = build_weather_context(messages)
            selected_again = build_weather_context(messages)
        self.assertEqual(messages, original)
        self.assertEqual(selected, selected_again)
        self.assertEqual(len(selected), 5)


if __name__ == "__main__":
    unittest.main()
