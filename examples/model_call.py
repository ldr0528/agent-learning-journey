"""最小模型调用：python -m examples.model_call。"""

import argparse

from openai import APIConnectionError, APIStatusError

from agent_learning.config import load_settings
from agent_learning.llm import ask_model


def main():
    parser = argparse.ArgumentParser(description="单次模型调用")
    parser.add_argument("--provider", choices=["qwen", "openai"])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        settings = load_settings(args.provider)
        if args.check:
            print(f"配置已填写：{settings.provider} / {settings.model}；未请求 API。")
            return 0
        messages = [
            {"role": "system", "content": "请用简洁中文解释 Python 概念，给出一个短例子。"},
            {"role": "user", "content": "Python 字典是什么？"},
        ]
        with settings.create_client() as client:
            print(ask_model(client, settings.model, messages, settings.request_options))
    except APIConnectionError:
        print("连接失败或超时。")
        return 1
    except APIStatusError as error:
        print(f"API 返回 HTTP {error.status_code}；请检查密钥、权限与额度。")
        return 1
    except ValueError as error:
        print(error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
