"""只使用假配置，避免读取本机密钥。"""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_learning.config import Settings, load_settings


class SettingsTests(unittest.TestCase):
    def test_qwen4_uses_documented_non_thinking_parameter(self):
        settings = Settings("qwen", "qwen4-max", "https://qwen.invalid/v1", "fake-key")
        self.assertEqual(settings.request_options, {"max_tokens": 512, "reasoning_effort": "none"})
        legacy = Settings("qwen", "qwen-plus", "https://qwen.invalid/v1", "fake-key")
        self.assertEqual(legacy.request_options["extra_body"], {"enable_thinking": False})

    def test_provider_selects_its_own_key_and_options(self):
        env = {"LLM_PROVIDER": "qwen", "DASHSCOPE_API_KEY": "fake-qwen-key",
               "QWEN_MODEL_ID": "qwen-test", "QWEN_BASE_URL": "https://qwen.invalid/v1",
               "LLM_API_KEY": "fake-openai-key", "LLM_MODEL_ID": "openai-test",
               "LLM_BASE_URL": "https://openai.invalid/v1"}
        with patch.dict(os.environ, env, clear=True), patch("agent_learning.config.load_dotenv"):
            qwen = load_settings()
            other = load_settings("openai")
        self.assertEqual(qwen.api_key, "fake-qwen-key")
        self.assertEqual(other.api_key, "fake-openai-key")
        self.assertIn("max_tokens", qwen.request_options)
        self.assertIn("max_completion_tokens", other.request_options)
        self.assertNotIn("fake-qwen-key", repr(qwen))

    def test_missing_and_placeholder_values_fail_without_exposing_key(self):
        env = {"DASHSCOPE_API_KEY": "fake-private-value", "QWEN_MODEL_ID": "YOUR-MODEL-ID"}
        with patch.dict(os.environ, env, clear=True), patch("agent_learning.config.load_dotenv"):
            with self.assertRaises(ValueError) as caught:
                load_settings("qwen")
        self.assertIn("QWEN_MODEL_ID", str(caught.exception))
        self.assertNotIn("fake-private-value", str(caught.exception))

    def test_process_environment_overrides_dotenv(self):
        with tempfile.TemporaryDirectory() as temp:
            env_file = Path(temp) / ".env"
            env_file.write_text('DASHSCOPE_API_KEY="fake-file-key"\nQWEN_MODEL_ID="file-model"\n'
                                'QWEN_BASE_URL="https://qwen.invalid/v1"\n', encoding="utf-8")
            with patch.dict(os.environ, {"QWEN_MODEL_ID": "process-model"}, clear=True):
                settings = load_settings("qwen", env_file=env_file)
            self.assertEqual(settings.model, "process-model")
            self.assertEqual(settings.api_key, "fake-file-key")
