"""Smoke-test documented offline entry points; never request a paid model."""

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CORE = [
    ["examples.tool_execution"],
    ["agent_learning.tools.notes", "--query", "最大步数"],
    ["examples.context_preview"],
    ["examples.plan_first", "--demo"],
    ["examples.plan_solve", "--demo"],
    ["examples.reflection", "--demo"],
    ["examples.rag_research", "--output", "outputs/checks/research-report.md"],
    ["examples.evaluate", "--output", "outputs/checks/retrieval-evaluation.json"],
    ["examples.insurance_compare", "--output", "outputs/checks/insurance.json"],
    ["examples.insurance_compare", "--catalog", "official", "--request", "examples/insurance_official_request.json"],
]
INTEGRATIONS = [
    ["examples.langgraph_workflow"],
    ["examples.langgraph_workflow", "--checkpoint"],
    ["examples.langgraph_workflow", "--loop"],
    ["examples.mcp_demo"],
    ["examples.insurance_compare", "--engine", "langgraph"],
    ["examples.insurance_compare", "--engine", "mcp"],
]


def main():
    parser = argparse.ArgumentParser(description="检查课程中无需模型 API 的示例")
    parser.add_argument("--integrations", action="store_true", help="额外检查真实 LangGraph 与 MCP，需要安装 .[all]")
    args = parser.parse_args()
    commands = CORE + (INTEGRATIONS if args.integrations else [])
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    for command in commands:
        try:
            result = subprocess.run([sys.executable, "-m", *command], cwd=ROOT, env=env,
                                    capture_output=True, text=True, encoding="utf-8", timeout=60)
        except subprocess.TimeoutExpired:
            print(f"超时：{' '.join(command)}")
            return 1
        if result.returncode:
            print(f"失败：{' '.join(command)}，退出码 {result.returncode}")
            print((result.stdout + result.stderr)[-6000:])
            return 1
        print(f"通过：{' '.join(command)}")
    print(f"完成 {len(commands)} 个离线入口检查；没有调用付费模型。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
