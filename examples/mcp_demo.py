"""真实本地 MCP stdio 演示；不调用大模型、不读取 API Key。"""

import argparse
import asyncio

from agent_learning.integrations.mcp_client import run_mcp_demo


def main():
    parser = argparse.ArgumentParser(description="本地 MCP 工具发现与调用")
    parser.add_argument("--city", default="北京")
    parser.add_argument("--query", default="Action Observation")
    args = parser.parse_args()
    if not args.city.strip() or not args.query.strip():
        parser.error("city 和 query 不能为空。")
    try:
        result = asyncio.run(run_mcp_demo(city=args.city, query=args.query))
    except RuntimeError as error:
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
