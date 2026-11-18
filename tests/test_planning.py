"""规划器的输入与解析检查，不请求外部 API，不评价真实计划质量。"""

import contextlib
import io
import unittest
from unittest.mock import patch

from agent_learning.agents.planning import PLANNER_PROMPT, make_plan, parse_plan


class PlanningTests(unittest.TestCase):
    def test_plan_is_parsed_in_order_without_evaluating_steps(self):
        self.assertEqual(parse_plan('[" 计算周二销量 ", "计算周三销量", "合计三天销量"]'),
                         ["计算周二销量", "计算周三销量", "合计三天销量"])
        self.assertEqual(parse_plan('```json\n["计算周二", "计算周三", "合计"]\n```'),
                         ["计算周二", "计算周三", "合计"])

    def test_invalid_plan_formats_are_rejected(self):
        for raw in ('[]', '{}', 'null', 'true', '"计划"', '[" "]', '[1]',
                    '["计算周二", null]', '["第一步", ["第二步"]]',
                    '我的计划如下：\n["计算周二"]', "['计算周二']"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_plan(raw)

    def test_planner_sends_question_and_rules_once(self):
        question = "先计算周二，再计算周三，最后合计。"
        options = {"max_tokens": 512}
        with patch("agent_learning.agents.planning.ask_model", return_value='["计算周二", "计算周三", "合计"]') as ask:
            with contextlib.redirect_stdout(io.StringIO()):
                result = make_plan(None, "mock", question, options)
        ask.assert_called_once_with(None, "mock", [
            {"role": "system", "content": PLANNER_PROMPT},
            {"role": "user", "content": question},
        ], options)
        self.assertEqual(result, ["计算周二", "计算周三", "合计"])

    def test_empty_question_is_rejected_before_request(self):
        with patch("agent_learning.agents.planning.ask_model") as ask:
            with self.assertRaises(ValueError):
                make_plan(None, "mock", " ", {})
        ask.assert_not_called()


if __name__ == "__main__":
    unittest.main()
