"""医疗险比较的命令行入口，网页与命令行共享同一业务模块。"""

import argparse
import json
from pathlib import Path

from .service import load_catalog, run_session
from .store import SessionStore
from .workflow import render_markdown


def main(argv=None):
    parser = argparse.ArgumentParser(description="医疗险需求梳理与资料比较")
    sub = parser.add_subparsers(dest="command", required=True)
    products = sub.add_parser("products", help="查看资料目录中的产品与版本")
    products.add_argument("--catalog", choices=["demo", "official"], default="demo")
    compare = sub.add_parser("compare", help="读取需求文件并创建比较会话")
    compare.add_argument("--request", type=Path, required=True)
    compare.add_argument("--catalog", choices=["demo", "official"], default="demo")
    resume = sub.add_parser("resume", help="恢复会话；可提供补充后的完整需求文件")
    resume.add_argument("session_id")
    resume.add_argument("--request", type=Path)
    show = sub.add_parser("show", help="查看已保存的结果，不请求模型")
    show.add_argument("session_id")
    for command in (compare, resume):
        command.add_argument("--live", action="store_true", help="启用模型工具调用")
        command.add_argument("--max-calls", type=int, default=6)
    for command in (compare, resume, show):
        command.add_argument("--sessions", type=Path, default=Path("outputs/insurance-sessions"))
        command.add_argument("--output", type=Path, help="导出 Markdown 报告")
    args = parser.parse_args(argv)
    try:
        if args.command == "products":
            print(json.dumps(load_catalog(args.catalog).list_products(), ensure_ascii=False, indent=2))
            return 0
        store = SessionStore(args.sessions)
        request = None
        if getattr(args, "request", None):
            if args.request.stat().st_size > 30000:
                raise ValueError("需求文件过大。")
            request = json.loads(args.request.read_text(encoding="utf-8-sig"))
        if args.command == "show":
            report = store.load(args.session_id)["result"]
            if report is None:
                raise ValueError("该会话尚无运行结果。")
        else:
            session_id = store.create(request, args.catalog) if args.command == "compare" else args.session_id
            report = run_session(store, session_id, request=request,
                                 mode="live" if args.live else "offline", max_calls=args.max_calls)
        text = render_markdown(report)
        print(text)
        print(f'会话：{report["session_id"]}；模型请求：{report["model_calls"]}；工具操作：{report["tool_calls"]}。')
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
        return 0 if report["status"] in ("completed", "completed_with_gaps", "needs_input") else 1
    except (ValueError, OSError) as error:
        print(f"无法完成比较：{error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
