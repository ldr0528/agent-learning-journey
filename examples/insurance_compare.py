"""同一需求可用 Python、LangGraph 或 MCP 执行；默认无需模型。"""

import argparse
import asyncio
import json
from pathlib import Path

from agent_learning.config import load_settings
from agent_learning.insurance.service import load_catalog, model_adapter
from agent_learning.insurance.workflow import prepare_request, render_markdown, run_comparison


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, default=Path(__file__).with_name("insurance_request.json"))
    parser.add_argument("--catalog", choices=["demo", "official"], default="demo")
    parser.add_argument("--engine", choices=["python", "langgraph", "mcp"], default="python")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--max-calls", type=int, default=6)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    client, model = None, None
    try:
        if args.request.stat().st_size > 30000:
            raise ValueError("需求文件过大。")
        request = json.loads(args.request.read_text(encoding="utf-8-sig"))
        catalog = load_catalog(args.catalog)
        ready = prepare_request(request, catalog)
        if args.live and ready["status"] == "ready":
            settings = load_settings()
            client = settings.create_client()
            model = model_adapter(client, settings)
        options = {"mode": "live" if args.live else "offline", "request_model": model, "max_calls": args.max_calls}
        if args.engine == "python":
            report = run_comparison(request, catalog=catalog, **options)
        elif args.engine == "langgraph":
            from agent_learning.insurance.integrations import run_graph_comparison
            report = run_graph_comparison(request, catalog=catalog, **options)
        else:
            from agent_learning.insurance.integrations import run_mcp_comparison
            report = asyncio.run(run_mcp_comparison(request, catalog_kind=args.catalog, **options))
        print(render_markdown(report))
        print(f'模型请求：{report["model_calls"]}；工具操作：{report["tool_calls"]}。')
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0 if report["status"] in ("completed", "completed_with_gaps", "needs_input") else 1
    except (ValueError, OSError) as error:
        print(f"无法完成比较：{error}")
        return 1
    finally:
        if client:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
