"""集中读取服务配置；密钥不进入打印内容或对象 repr。"""

from dataclasses import dataclass, field
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


@dataclass(frozen=True)
class Settings:
    provider: str
    model: str
    base_url: str
    api_key: str = field(repr=False)

    @property
    def request_options(self):
        if self.provider == "qwen":
            return {"max_tokens": 512, "extra_body": {"enable_thinking": False}}
        return {"max_completion_tokens": 2048, "reasoning_effort": "low"}

    def create_client(self):
        return OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=30, max_retries=0)


def load_settings(provider=None, env_file=None):
    # 从运行目录加载；系统环境变量优先，方便 CI 或部署时注入配置。
    load_dotenv(Path(env_file) if env_file is not None else Path.cwd() / ".env", override=False)
    provider = (provider or os.getenv("LLM_PROVIDER", "qwen")).strip().lower()
    if provider == "qwen":
        names = ("DASHSCOPE_API_KEY", "QWEN_MODEL_ID", "QWEN_BASE_URL")
    elif provider == "openai":
        names = ("LLM_API_KEY", "LLM_MODEL_ID", "LLM_BASE_URL")
    else:
        raise ValueError("LLM_PROVIDER 只能是 qwen 或 openai。")
    values = [os.getenv(name, "").strip() for name in names]
    missing = [name for name, value in zip(names, values) if not value or value.startswith("YOUR-")]
    if missing:
        raise ValueError("请在 .env 或环境变量中填写：" + ", ".join(missing))
    api_key, model, base_url = values
    return Settings(provider=provider, model=model, base_url=base_url, api_key=api_key)
