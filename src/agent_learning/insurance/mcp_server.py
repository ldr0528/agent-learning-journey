"""以 MCP stdio 提供与本地比较相同的只读产品资料。"""

import argparse

from .service import load_catalog


def build_server(catalog):
    from mcp.server.fastmcp import FastMCP
    server = FastMCP("insurance-evidence")

    @server.tool()
    def search_product_clauses(product_id: str, version: str, query: str, limit: int = 3) -> dict:
        """在指定产品资料版本中检索事实。"""
        if not 1 <= limit <= 5:
            raise ValueError("返回数量需要为1–5。")
        return {"evidence": catalog.search(product_id, version, query, limit=limit)}

    @server.tool()
    def read_product_clauses(product_id: str, version: str, dimensions: list[str]) -> dict:
        """读取指定产品版本的维度事实，保留条件、状态和出处。"""
        if not 1 <= len(dimensions) <= 9:
            raise ValueError("需要1–9个维度。")
        return {"evidence": [fact for dimension in dict.fromkeys(dimensions)
                             for fact in catalog.facts(product_id, version, dimension)]}

    return server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", choices=["demo", "official"], default="demo")
    args = parser.parse_args()
    build_server(load_catalog(args.catalog)).run(transport="stdio")


if __name__ == "__main__":
    main()
