"""计划执行的上下文传递、边界和失败检查；全部离线。"""

import contextlib
from copy import deepcopy
import io
import json
import unittest

from agent_learning.agents.plan_solve import run_plan_solve


class PlanSolveTests(unittest.TestCase):
    def run_sequence(self, replies, **kwargs):
        replies = iter(replies)
        requests = []

        def model_call(client, model, messages, options):
            requests.append(deepcopy(messages))
            return next(replies)

        with contextlib.redirect_stdout(io.StringIO()):
            state = run_plan_solve(None, "scripted", "销量题", {}, model_call=model_call, **kwargs)
        return state, requests

    def test_each_step_receives_complete_plan_and_prior_results(self):
        state, requests = self.run_sequence(['["计算周二", "计算周三", "合计"]', "30", "25", "70"])
        self.assertEqual((state["status"], state["answer"], state["model_calls"], state["tool_calls"]),
                         ("finished", "70", 4, 0))
        first = json.loads(requests[1][1]["content"])
        third = json.loads(requests[3][1]["content"])
        self.assertEqual(first["history"], [])
        self.assertEqual(third["question"], "销量题")
        self.assertEqual(third["plan"], ["计算周二", "计算周三", "合计"])
        self.assertEqual(third["current_step"], {"number": 3, "task": "合计"})
        self.assertEqual([item["result"] for item in third["history"]], ["30", "25"])

    def test_call_limit_preserves_partial_work_without_final_answer(self):
        state, requests = self.run_sequence(['["计算周二", "计算周三", "合计"]', "30"], max_calls=2)
        self.assertEqual(len(requests), 2)
        self.assertEqual(state["status"], "call_limit")
        self.assertIsNone(state["answer"])
        self.assertEqual([item["result"] for item in state["history"]], ["30"])

    def test_invalid_or_oversized_plan_never_starts_execution(self):
        for raw in ('[]', '[1]', '不是计划', '["一", "二", "三"]'):
            with self.subTest(raw=raw):
                state, requests = self.run_sequence([raw], max_plan_steps=2)
                self.assertEqual(len(requests), 1)
                self.assertEqual(state["status"], "invalid_plan")
                self.assertEqual(state["history"], [])

    def test_empty_step_response_does_not_become_a_successful_answer(self):
        state, requests = self.run_sequence(['["求解"]', " "])
        self.assertEqual(state["status"], "invalid_result")
        self.assertEqual(len(requests), 2)
        self.assertIsNone(state["answer"])


if __name__ == "__main__":
    unittest.main()
