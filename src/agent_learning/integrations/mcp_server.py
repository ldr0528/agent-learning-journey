"""本地 MCP stdio 服务端；stdout 专供协议消息，业务日志使用 SDK 的 stderr。"""

from ..tools.notes import search_notes as local_search_notes
from ..tools.weather import get_weather


def create_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as error:
        raise RuntimeError('缺少 MCP 1.x SDK，请运行 python -m pip install -e ".[mcp]"。') from error
    server = FastMCP("agent-learning-tools", log_level="WARNING")

    @server.tool()
    def weather(city: str) -> dict:
        """查询本项目模拟天气；北京和上海有数据，其他城市返回暂无天气数据。"""
        if not city.strip():
            raise ValueError("city 不能为空。")
        return {"city": city.strip(), "weather": get_weather(city.strip()), "simulated": True}

    @server.tool()
    def search_notes(query: str) -> dict:
        """检索本地 Hello-Agents 教学摘要，返回资料编号、内容和原文链接。"""
        if not query.strip():
            raise ValueError("query 不能为空。")
        return {"notes": local_search_notes(query), "content_type": "本地教学摘要，非教材原文"}

    return server


def main():
    import sys
    try:
        create_server().run(transport="stdio")
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
