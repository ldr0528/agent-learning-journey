"""离线检查循环控制，不读取密钥、不调用外部 API。

这些是程序逻辑测试，不是模型回答质量的评估集。
"""

import contextlib
from copy import deepcopy
import io
import unittest
from unittest.mock import patch

from agent_learning.agents.weather import run_weather as run_agent


class AgentLoopTests(unittest.TestCase):
    def run_sequence(self, replies, max_steps=5):
        replies = iter(replies)
        requests = []

        def fake_model(client, model, messages, options):
            requests.append(deepcopy(messages))
            return next(replies)

        with patch("agent_learning.loop.ask_model", side_effect=fake_model), contextlib.redirect_stdout(io.StringIO()):
            result = run_agent(None, "mock", "比较北京和上海", {}, max_steps)
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


if __name__ == "__main__":
    unittest.main()
