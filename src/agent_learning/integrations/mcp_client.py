"""通过官方 MCP SDK 启动真实子进程并完成 initialize/list_tools/call_tool。"""

import asyncio
from contextlib import asynccontextmanager
import json
import sys


@asynccontextmanager
async def open_mcp_session():
    """启动本课程的只读工具服务；调用方负责初始化和业务请求。"""
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError as error:
        raise RuntimeError('缺少 MCP 1.x SDK，请运行 python -m pip install -e ".[mcp]"。') from error
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "agent_learning.integrations.mcp_server"],
        env={"PYTHONUTF8": "1"},
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            yield session


def unpack_result(result):
    if result.isError:
        raise ValueError("MCP 工具返回错误，未将错误结果当成成功数据。")
    if result.structuredContent is not None:
        return result.structuredContent
    text = "\n".join(block.text for block in result.content if block.type == "text")
    return json.loads(text)


async def run_mcp_demo(*, city="北京", query="Action Observation", timeout=20):
    async def exchange():
        async with open_mcp_session() as session:
            initialized = await session.initialize()
            tools = await session.list_tools()
            weather = await session.call_tool("weather", {"city": city})
            notes = await session.call_tool("search_notes", {"query": query})
            return {
                "server": initialized.serverInfo.name,
                "protocol_version": initialized.protocolVersion,
                "tools": [{"name": tool.name, "input_schema": tool.inputSchema} for tool in tools.tools],
                "weather": unpack_result(weather), "search": unpack_result(notes),
            }
    return await asyncio.wait_for(exchange(), timeout=timeout)
