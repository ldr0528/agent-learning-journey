"""有界 Plan-and-Solve；--demo 使用预设模型回复，不调用 API。"""

import argparse

from openai import APIConnectionError, APIStatusError

from agent_learning.agents.plan_solve import run_plan_solve
from agent_learning.config import load_settings
from .plan_first import DEMO_PLAN, QUESTION


def main():
    parser = argparse.ArgumentParser(description="先规划，再逐步执行")
    parser.add_argument("--question", default=QUESTION)
    parser.add_argument("--provider", choices=["qwen", "openai"])
    parser.add_argument("--max-calls", type=int, default=6)
    parser.add_argument("--max-plan-steps", type=int, default=5)
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    if not args.question.strip() or args.max_calls < 1 or args.max_plan_steps < 1:
        parser.error("问题不能为空，调用预算与计划步数上限必须至少为 1。")
    if args.demo and args.question != QUESTION:
        parser.error("--demo 仅支持默认题；自定义问题请去掉 --demo。")
    print(f"问题：{args.question}")
    kwargs = {"max_calls": args.max_calls, "max_plan_steps": args.max_plan_steps}
    try:
        if args.demo:
            print("离线演示：模型回复全部预设，实际 API 请求 0 次。")
            replies = iter([DEMO_PLAN, "15 × 2 = 30 个。", "30 - 5 = 25 个。", "15 + 30 + 25 = 70 个。"])
            state = run_plan_solve(None, "scripted", args.question, {},
                                   model_call=lambda *unused: next(replies), **kwargs)
        else:
            settings = load_settings(args.provider)
            print(f"服务：{settings.provider} / {settings.model}；总模型调用上限：{args.max_calls}。")
            with settings.create_client() as client:
                state = run_plan_solve(client, settings.model, args.question, settings.request_options, **kwargs)
    except APIConnectionError:
        print("API 连接失败或超时，任务未完成。")
        return 1
    except APIStatusError as error:
        print(f"API 返回 HTTP {error.status_code}，任务未完成。")
        return 1
    except ValueError as error:
        print(error)
        return 1
    print(f"\n状态：{state['status']}；完成步骤：{len(state['history'])}/{len(state['plan'])}。")
    print(f"模型适配器调用 {state['model_calls']} 次；工具执行 {state['tool_calls']} 次。")
    if state["answer"] is not None:
        print(f"最终结果：{state['answer']}")
    elif state["error"]:
        print(f"原因：{state['error']}")
    else:
        print("调用预算耗尽；已保留中间结果，未产生完整答案。")
    return 0 if state["status"] == "finished" else 1


if __name__ == "__main__":
    raise SystemExit(main())
