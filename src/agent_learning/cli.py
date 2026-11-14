"""研究助手命令行入口。"""

import argparse

from openai import APIConnectionError, APIStatusError

from .agents.research import run_research
from .config import load_settings


def main():
    parser = argparse.ArgumentParser(description="检索本地教学摘要，生成带来源的简答")
    parser.add_argument("--question", default="Agent Loop 为什么要有最大步数？")
    parser.add_argument("--max-steps", type=int, default=5, help="模型请求次数上限")
    parser.add_argument("--provider", choices=["qwen", "openai"], help="临时选择服务")
    parser.add_argument("--check", action="store_true", help="只检查配置，不请求 API")
    args = parser.parse_args()
    if args.max_steps < 1 or not args.question.strip():
        parser.error("问题不能为空，--max-steps 必须至少为 1。")
    try:
        settings = load_settings(args.provider)
        if args.check:
            print(f"配置已填写：{settings.provider} / {settings.model}；未联网验证权限或额度。")
            return 0
        print(f"服务：{settings.provider} / {settings.model}；模型请求上限：{args.max_steps}。")
        print(f"问题：{args.question}")
        with settings.create_client() as client:
            result = run_research(client, settings.model, args.question,
                                  settings.request_options, args.max_steps)
    except APIConnectionError:
        print("连接失败或超时，请检查网络与服务地址。")
        return 1
    except APIStatusError as error:
        print(f"API 返回 HTTP {error.status_code}；请检查密钥、权限与额度。")
        return 1
    except OSError:
        print("无法读取本地摘要文件，请检查安装是否完整。")
        return 1
    except ValueError as error:
        print(error)
        return 1
    return 0 if result["status"] == "finished" else 1


if __name__ == "__main__":
    raise SystemExit(main())
