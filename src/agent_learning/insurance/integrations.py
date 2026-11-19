"""同一医疗险任务在 LangGraph 与 MCP 中的映射。"""

import asyncio
import json
import sys
from typing import TypedDict

from .agent import execute_tool, run_agent
from .service import load_catalog
from .workflow import EvidenceWorkspace, prepare_request, run_comparison


def run_graph_comparison(request, *, catalog=None, mode="offline", request_model=None, max_calls=6):
    if mode not in ("offline", "live"):
        raise ValueError("运行模式需为 offline 或 live。")
    from langgraph.graph import END, START, StateGraph
    catalog = catalog or load_catalog()

    class State(TypedDict, total=False):
        request: dict
        ready: bool
        report: dict
        nodes: list[str]

    def intake(state):
        prepared = prepare_request(state["request"], catalog)
        return {"ready": prepared["status"] == "ready", "nodes": ["intake"]}

    def research(state):
        return {"report": run_comparison(state["request"], catalog=catalog, mode=mode,
                                          request_model=request_model, max_calls=max_calls),
                "nodes": state["nodes"] + ["research"]}

    def clarify(state):
        return {"report": run_comparison(state["request"], catalog=catalog, mode=mode),
                "nodes": state["nodes"] + ["clarify"]}

    def verify(state):
        report = state["report"]
        if report["status"] in ("completed", "completed_with_gaps"):
            check = EvidenceWorkspace(state["request"], catalog)
            check.remember(report["sources"])
            check.finish([f["evidence_id"] for f in report["sources"]])
        return {"nodes": state["nodes"] + ["verify"]}

    def deliver(state):
        return {"report": {**state["report"], "graph_nodes": state["nodes"] + ["deliver"]}}

    graph = StateGraph(State)
    for name, node in (("intake", intake), ("research", research), ("clarify", clarify), ("verify", verify), ("deliver", deliver)):
        graph.add_node(name, node)
    graph.add_edge(START, "intake")
    graph.add_conditional_edges("intake", lambda state: "research" if state["ready"] else "clarify")
    graph.add_edge("research", "verify")
    graph.add_edge("clarify", "deliver")
    graph.add_edge("verify", "deliver")
    graph.add_edge("deliver", END)
    return graph.compile().invoke({"request": request})["report"]


async def run_mcp_comparison(request, *, catalog_kind="demo", mode="offline", request_model=None, max_calls=6):
    if mode not in ("offline", "live"):
        raise ValueError("运行模式需为 offline 或 live。")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    workspace = EvidenceWorkspace(request, load_catalog(catalog_kind))
    if workspace.state["status"] != "ready":
        return {**workspace.report(), "mode": mode}
    if mode == "live" and request_model is None:
        raise ValueError("模型模式需要提供请求接口。")

    async def exchange():
        server = StdioServerParameters(command=sys.executable,
                   args=["-m", "agent_learning.insurance.mcp_server", "--catalog", catalog_kind],
                   env={"PYTHONUTF8": "1"})
        async with stdio_client(server) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                initialized = await asyncio.wait_for(session.initialize(), timeout=20)
                discovered = await asyncio.wait_for(session.list_tools(), timeout=20)
                names = {t.name for t in discovered.tools}
                if not {"read_product_clauses", "search_product_clauses"} <= names:
                    raise ValueError("MCP 服务缺少必要的取证工具。")

                async def remote(name, args):
                    response = await asyncio.wait_for(session.call_tool(name, args), timeout=20)
                    if response.isError:
                        raise ValueError("MCP 取证工具返回错误。")
                    payload = response.structuredContent
                    if payload is None:
                        payload = json.loads(next(c.text for c in response.content if c.type == "text"))
                    if not isinstance(payload, dict) or not isinstance(payload.get("evidence"), list):
                        raise ValueError("MCP 工具未返回证据列表。")
                    return payload

                if mode == "live":
                    loop = asyncio.get_running_loop()

                    def execute(name, args):
                        if name == "finish_comparison":
                            return execute_tool(workspace, name, args)
                        # 在隔离工作区校验参数，只有协议返回成功后才把证据写入本次任务。
                        preview = EvidenceWorkspace(request, workspace.catalog)
                        expected = execute_tool(preview, name, args)
                        future = asyncio.run_coroutine_threadsafe(remote(name, args), loop)
                        payload = future.result(timeout=25)
                        if payload != expected:
                            raise ValueError("协议返回的证据与固定目录版本不一致。")
                        workspace.remember(payload["evidence"])
                        return payload

                    report = await asyncio.to_thread(run_agent, workspace, request_model,
                                                     max_calls=max_calls, execute=execute)
                else:
                    for step, item in enumerate(workspace.state["request"]["selections"], 1):
                        args = {**item, "dimensions": workspace.state["dimensions"]}
                        payload = await remote("read_product_clauses", args)
                        workspace.remember(payload["evidence"])
                        workspace.trace.append({"step": step, "name": "read_product_clauses", "arguments": args,
                                                "transport": "mcp", "is_error": False,
                                                "evidence_ids": [f["evidence_id"] for f in payload["evidence"]]})
                    report = workspace.finish(list(workspace.evidence))
                    report["tool_calls"] = len(workspace.state["request"]["selections"])
                report.update(mode=mode, transport="mcp", server=initialized.serverInfo.name)
                return report

    return await asyncio.wait_for(exchange(), timeout=40 * max_calls + 40)
