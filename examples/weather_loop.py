"""两个城市、多个工具结果、一个最终回答。"""

import argparse

from openai import APIConnectionError, APIStatusError

from agent_learning.agents.weather import run_weather
from agent_learning.config import load_settings


def main():
    parser = argparse.ArgumentParser(description="模拟天气的有限工具循环")
    parser.add_argument("--question", default="分别查询北京和上海的模拟天气，再比较哪里更暖和。")
    parser.add_argument("--max-steps", type=int, default=5)
    parser.add_argument("--budget-context", action="store_true",
                        help="在每次模型请求中提供当前轮数与剩余请求预算")
    parser.add_argument("--provider", choices=["qwen", "openai"])
    args = parser.parse_args()
    if args.max_steps < 1 or not args.question.strip():
        parser.error("问题不能为空，--max-steps 必须至少为 1。")
    try:
        settings = load_settings(args.provider)
        print(f"服务：{settings.provider} / {settings.model}；模型请求上限：{args.max_steps}。")
        print(f"预算上下文：{'开启' if args.budget_context else '关闭'}。")
        print(f"问题：{args.question}")
        with settings.create_client() as client:
            result = run_weather(client, settings.model, args.question,
                                 settings.request_options, args.max_steps,
                                 budget_context=args.budget_context)
    except APIConnectionError:
        print("连接失败或超时。")
        return 1
    except APIStatusError as error:
        print(f"API 返回 HTTP {error.status_code}；请检查密钥、权限与额度。")
        return 1
    except ValueError as error:
        print(error)
        return 1
    return 0 if result["status"] == "finished" else 1


if __name__ == "__main__":
    raise SystemExit(main())
