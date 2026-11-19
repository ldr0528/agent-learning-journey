"""评审与修订的输入、预算和停止条件；不评价真实模型质量。"""

import contextlib
from copy import deepcopy
import io
import json
import unittest

from agent_learning.agents.reflection import parse_review, run_reflection


ACCEPT = '{"verdict":"accept","feedback":"满足给定任务。"}'
REVISE = '{"verdict":"revise","feedback":"请补充结果回传条件。"}'


class ReflectionTests(unittest.TestCase):
    def run_sequence(self, replies, **kwargs):
        replies = iter(replies)
        requests = []

        def model_call(client, model, messages, options):
            requests.append(deepcopy(messages))
            return next(replies)

        with contextlib.redirect_stdout(io.StringIO()):
            state = run_reflection(None, "scripted", "解释回传条件", {}, model_call=model_call, **kwargs)
        return state, requests

    def test_accept_stops_without_revision(self):
        state, requests = self.run_sequence(["完整初稿", ACCEPT], max_revisions=0)
        self.assertEqual((state["status"], state["answer"], state["revisions"]), ("accepted", "完整初稿", 0))
        self.assertEqual(len(requests), 2)

    def test_revision_receives_feedback_and_next_review_sees_latest_draft(self):
        state, requests = self.run_sequence(["初稿", REVISE, "修订稿", ACCEPT])
        revision = json.loads(requests[2][1]["content"])
        review_again = json.loads(requests[3][1]["content"])
        self.assertEqual(revision, {"task": "解释回传条件", "draft": "初稿", "feedback": "请补充结果回传条件。"})
        self.assertEqual(review_again["draft"], "修订稿")
        self.assertEqual((state["status"], state["model_calls"], state["revisions"]), ("accepted", 4, 1))
        self.assertEqual([event["type"] for event in state["history"]], ["draft", "review", "revision", "review"])

    def test_call_limit_keeps_unreviewed_revision_as_draft(self):
        state, requests = self.run_sequence(["初稿", REVISE, "尚未复审的修订稿"], max_calls=3)
        self.assertEqual(len(requests), 3)
        self.assertEqual(state["status"], "call_limit")
        self.assertIsNone(state["answer"])
        self.assertEqual(state["draft"], "尚未复审的修订稿")

    def test_revision_limit_stops_after_final_review_without_another_revision(self):
        state, requests = self.run_sequence(["初稿", REVISE, "稿1", REVISE, "稿2", REVISE],
                                             max_revisions=2, max_calls=10)
        self.assertEqual(state["status"], "revision_limit")
        self.assertEqual(len(requests), 6)
        self.assertEqual([review["version"] for review in state["reviews"]], [0, 1, 2])
        self.assertIsNone(state["answer"])

    def test_review_format_errors_do_not_mean_acceptance(self):
        for raw in ('无需改进', '{}', '{"verdict":true,"feedback":"通过"}',
                    '{"verdict":"accept","feedback":" "}', '["accept"]'):
            with self.subTest(raw=raw):
                state, requests = self.run_sequence(["初稿", raw])
                self.assertEqual(state["status"], "invalid_review")
                self.assertEqual(len(requests), 2)
                self.assertIsNone(state["answer"])
        self.assertEqual(parse_review('```json\n' + ACCEPT + '\n```')["verdict"], "accept")

    def test_separate_runs_do_not_share_history(self):
        first, _ = self.run_sequence(["稿一", REVISE, "修订一", ACCEPT])
        second, requests = self.run_sequence(["稿二", ACCEPT])
        self.assertEqual(len(first["history"]), 4)
        self.assertEqual(len(second["history"]), 2)
        self.assertNotIn("修订一", str(requests))


if __name__ == "__main__":
    unittest.main()
