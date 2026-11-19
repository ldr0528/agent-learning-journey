"""默认真实本地 MCP 协议演示；--live 才让模型发现、选择并读取工具结果。"""

import argparse
import asyncio
import json

from agent_learning.integrations.mcp_client import run_mcp_demo


def main():
    parser = argparse.ArgumentParser(description="本地 MCP 工具发现与调用")
    parser.add_argument("--city", default="北京")
    parser.add_argument("--query", default="Action Observation")
    parser.add_argument("--live", action="store_true", help="调用模型决定工具并根据结果回答")
    parser.add_argument("--provider", choices=["qwen", "openai"])
    parser.add_argument("--question", default="分别查询北京和上海的模拟天气，再比较哪里更暖和。")
    parser.add_argument("--max-calls", type=int, default=4, help="真实模式模型请求上限，默认 4")
    args = parser.parse_args()
    if not args.city.strip() or not args.query.strip():
        parser.error("city 和 query 不能为空。")
    if not args.question.strip() or args.max_calls < 1:
        parser.error("question 不能为空，max-calls 必须至少为 1。")
    try:
        if args.live:
            from agent_learning.config import load_settings
            from agent_learning.integrations.mcp_agent import run_mcp_agent
            settings = load_settings(args.provider)
            print(f"真实模型 + MCP：{settings.provider} / {settings.model}；模型请求上限 {args.max_calls}。")
            print("问题：" + args.question)
            with settings.create_client() as client:
                result = asyncio.run(run_mcp_agent(client, settings, question=args.question,
                                                  max_calls=args.max_calls))
            print(f'initialize：{result["server"]}；协商协议版本：{result["protocol_version"]}')
            print("list_tools：" + ", ".join(sorted(result["tools"])))
            for event in result["trace"]:
                print(f'[第 {event["request"]} 次模型请求] tool_call：{event["name"]}'
                      f'({json.dumps(event["arguments"], ensure_ascii=False)})')
                print("tool 结果：" + json.dumps(event["content"], ensure_ascii=False))
            print(f'状态：{result["status"]}；模型请求 {result["model_calls"]} 次；'
                  f'MCP 工具请求 {result["tool_calls"]} 次；错误反馈 {result["tool_errors"]} 次。')
            print("回答：" + (result["answer"] or "预算内未取得最终回答。"))
            return 0 if result["status"] == "finished" else 1
        result = asyncio.run(run_mcp_demo(city=args.city, query=args.query))
    except RuntimeError as error:
        print(error)
        return 1
    except ValueError as error:
        print(error)
        return 1
    except Exception as error:
        print(f"MCP 会话未完成：{type(error).__name__}。请检查可选依赖、子进程和参数。")
        return 1
    print("真实 MCP stdio 会话；工具在子进程执行，本次模型请求 0 次。")
    print(f'initialize：{result["server"]}；协商协议版本：{result["protocol_version"]}')
    print("list_tools：" + ", ".join(sorted(tool["name"] for tool in result["tools"])))
    print(f'call_tool weather：{result["weather"]["city"]}，{result["weather"]["weather"]}，模拟数据。')
    notes = result["search"]["notes"]
    print("call_tool search_notes：" + (", ".join(note["id"] for note in notes) or "没有命中"))
    for note in notes:
        print(f'[{note["id"]}] {note["content"]}\n来源：{note["source_url"]}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
