"""有限评审与修订；--demo 使用预设回复，不调用 API。"""

import argparse

from openai import APIConnectionError, APIStatusError

from agent_learning.agents.reflection import run_reflection
from agent_learning.config import load_settings


TASK = ("请用不超过120字解释 Action、Observation 的分工及工具结果如何进入下一轮模型请求。"
        "给定事实：Action 表达模型请求；工具由程序执行；Observation 由程序组织；打印不等于回传。")
DEMO_REPLIES = [
    "模型输出 Action，工具执行后产生 Observation，模型会自动记住工具结果。",
    '{"verdict":"revise","feedback":"自动记住的表述有误，应说明程序组织 Observation 并将结果加入下一轮请求。"}',
    "Action 表达模型希望执行的操作；程序执行工具并组织 Observation，再把结果加入下一轮请求。仅打印结果不会让模型收到它。",
    '{"verdict":"accept","feedback":"已说明模型与程序的分工，并明确回传结果与打印结果的区别。"}',
]


def main():
    parser = argparse.ArgumentParser(description="初稿、评审、有限修订")
    parser.add_argument("--task", default=TASK)
    parser.add_argument("--provider", choices=["qwen", "openai"])
    parser.add_argument("--max-calls", type=int, default=6)
    parser.add_argument("--max-revisions", type=int, default=2)
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    if not args.task.strip() or args.max_calls < 1 or args.max_revisions < 0:
        parser.error("任务不能为空，调用预算至少为 1，修订上限不能为负。")
    if args.demo and args.task != TASK:
        parser.error("--demo 仅支持默认任务；自定义任务请去掉 --demo。")
    print(f"任务：{args.task}")
    kwargs = {"max_calls": args.max_calls, "max_revisions": args.max_revisions}
    try:
        if args.demo:
            print("离线演示：初稿、评审和修订均为预设文本，实际 API 请求 0 次。")
            replies = iter(DEMO_REPLIES)
            state = run_reflection(None, "scripted", args.task, {},
                                   model_call=lambda *unused: next(replies), **kwargs)
        else:
            settings = load_settings(args.provider)
            print(f"服务：{settings.provider} / {settings.model}；总模型调用上限：{args.max_calls}。")
            with settings.create_client() as client:
                state = run_reflection(client, settings.model, args.task, settings.request_options, **kwargs)
    except APIConnectionError:
        print("API 连接失败或超时，任务未完成。")
        return 1
    except APIStatusError as error:
        print(f"API 返回 HTTP {error.status_code}，任务未完成。")
        return 1
    except ValueError as error:
        print(error)
        return 1
    print(f"\n状态：{state['status']}；评审 {len(state['reviews'])} 次；修订 {state['revisions']} 次。")
    print(f"模型适配器调用 {state['model_calls']} 次；工具执行 {state['tool_calls']} 次。")
    if state["answer"] is not None:
        print(f"评审接受的答案：{state['answer']}")
    else:
        print(f"尚未获评审接受的草稿：{state['draft'] or '无'}")
        if state["error"]:
            print(f"原因：{state['error']}")
    return 0 if state["status"] == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
