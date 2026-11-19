"""Verify that run evidence records the real messages without exposing credentials."""

from types import SimpleNamespace
import unittest

from scripts.record_live import ROOT, Recorder, sanitize, sanitize_record


class RecordingTests(unittest.TestCase):
    def test_nested_paths_are_redacted_before_json_escaping(self):
        source = {"stdout": str(ROOT) + "/file", "calls": [{"content": "key=private-value\n" + ROOT.as_posix()}]}
        result = sanitize_record(source, ["private-value"])
        self.assertEqual(result["stdout"], "[WORKSPACE]/file")
        self.assertEqual(result["calls"][0]["content"], "key=[REDACTED]\n[WORKSPACE]")
        self.assertEqual(source["stdout"], str(ROOT) + "/file")

    def test_snapshot_preserves_tool_feedback_without_authentication_fields(self):
        messages = [{"role": "tool", "tool_call_id": "call-example", "content": "北京：12℃"}]
        response = SimpleNamespace(model="recorded-model", choices=[SimpleNamespace(index=0, finish_reason="stop",
            message=SimpleNamespace(model_dump=lambda **_: {"role": "assistant", "content": "北京12℃", "private": "not-saved"}))],
            usage=SimpleNamespace(model_dump=lambda **_: {"total_tokens": 42}))
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_: response)))
        recorder = Recorder()
        wrapped = recorder.wrap(SimpleNamespace(api_key="test-secret", provider="qwen"), lambda _: client)
        actual = wrapped.chat.completions.create(model="recorded-model", messages=messages,
                                                extra_headers={"Authorization": "do-not-save"})
        messages[0]["content"] = "later mutation"
        self.assertIs(actual, response)
        self.assertEqual(recorder.calls[0]["request"]["messages"][0]["content"], "北京：12℃")
        self.assertNotIn("extra_headers", recorder.calls[0]["request"])
        self.assertNotIn("private", recorder.calls[0]["response"]["choices"][0]["message"])
        self.assertEqual(sanitize("value=test-secret", recorder.secrets), "value=[REDACTED]")

    def test_failed_attempt_is_recorded_without_exception_body(self):
        def fail(**_):
            raise RuntimeError("private-value")
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fail)))
        recorder = Recorder()
        recorder.wrap(SimpleNamespace(api_key="test-secret", provider="qwen"), lambda _: client)
        with self.assertRaises(RuntimeError):
            client.chat.completions.create(model="model", messages=[])
        self.assertEqual(recorder.calls[0]["error_type"], "RuntimeError")
        self.assertNotIn("private-value", str(recorder.calls))
        self.assertNotIn("response", recorder.calls[0])


if __name__ == "__main__":
    unittest.main()
