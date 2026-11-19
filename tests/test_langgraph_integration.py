"""安装 graph extra 后运行真实图；普通核心环境明确跳过。"""

import importlib.util
import unittest

from agent_learning.integrations.langgraph_workflow import (
    build_question_graph, build_weather_graph, initial_weather_state,
)


@unittest.skipUnless(importlib.util.find_spec("langgraph"), "需要可选依赖 .[graph]")
class LangGraphIntegrationTests(unittest.TestCase):
    def test_three_nodes_pass_retrieved_evidence_to_answer(self):
        state = build_question_graph().invoke({"question": "Action Observation", "trace": []})
        self.assertEqual(state["trace"], ["understand", "search", "answer"])
        self.assertEqual([note["id"] for note in state["notes"]], ["N02"])
        self.assertIn("[N02]", state["answer"])

    def test_no_match_preserves_insufficiency(self):
        state = build_question_graph().invoke({"question": "zzzz-unused-query", "trace": []})
        self.assertEqual(state["notes"], [])
        self.assertIn("资料不足", state["answer"])

    def test_checkpoint_threads_keep_separate_values(self):
        from langgraph.checkpoint.memory import InMemorySaver
        app = build_question_graph(checkpointer=InMemorySaver())
        first = {"configurable": {"thread_id": "first"}}
        second = {"configurable": {"thread_id": "second"}}
        app.invoke({"question": "Action Observation", "trace": []}, first)
        app.invoke({"question": "zzzz-unused-query", "trace": []}, second)
        self.assertIn("[N02]", app.get_state(first).values["answer"])
        self.assertIn("资料不足", app.get_state(second).values["answer"])
        self.assertEqual(app.get_state(first).next, ())

    def test_model_tool_cycle_preserves_both_results_and_stops(self):
        replies = iter(['Action: get_weather(city="北京")', 'Action: get_weather(city="上海")',
                        'Action: Finish[模拟数据中上海更暖和。]'])
        received = []
        def decide(messages):
            received.append([m.copy() for m in messages])
            return next(replies)
        state = build_weather_graph(decide, max_steps=3).invoke(initial_weather_state("比较两地"))
        self.assertEqual((state["requests"], state["tool_calls"], state["status"]), (3, 2, "finished"))
        observations = [m["content"] for m in received[2] if m["content"].startswith("Observation:")]
        self.assertEqual(observations, ["Observation: 下雨，12℃", "Observation: 晴天，22℃"])

    def test_step_limit_is_not_graph_recursion_limit(self):
        replies = iter(['Action: get_weather(city="北京")', 'Action: get_weather(city="上海")'])
        state = build_weather_graph(lambda messages: next(replies), max_steps=2).invoke(initial_weather_state("比较两地"))
        self.assertEqual((state["requests"], state["tool_calls"], state["status"]), (2, 2, "step_limit"))
        self.assertIsNone(state["answer"])

    def test_injected_model_must_cite_returned_notes(self):
        replies = iter(["Action Observation", "回答引用未知资料 [N99]"])
        with self.assertRaises(ValueError):
            build_question_graph(lambda messages: next(replies)).invoke({"question": "分工", "trace": []})


if __name__ == "__main__":
    unittest.main()
