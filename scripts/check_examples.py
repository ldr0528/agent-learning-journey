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
    ["examples.insurance_consultation", "--output", "outputs/checks/insurance-consultation.json"],
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
BOUNDARIES = [
    (["examples.plan_solve", "--demo", "--max-calls", "1"], 1, "call_limit"),
    (["examples.reflection", "--demo", "--max-revisions", "0"], 1, "revision_limit"),
    (["examples.rag_research", "--context-chars", "1"], 0, "insufficient_evidence"),
]
INTEGRATION_BOUNDARIES = [
    (["examples.langgraph_workflow", "--loop", "--max-steps", "2"], 1, "step_limit"),
]


def main():
    parser = argparse.ArgumentParser(description="检查课程中无需模型 API 的示例")
    parser.add_argument("--integrations", action="store_true", help="额外检查真实 LangGraph 与 MCP，需要安装 .[all]")
    args = parser.parse_args()
    commands = [(command, 0, None) for command in CORE + (INTEGRATIONS if args.integrations else [])]
    commands += BOUNDARIES + (INTEGRATION_BOUNDARIES if args.integrations else [])
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    for command, expected_code, expected_status in commands:
        try:
            result = subprocess.run([sys.executable, "-m", *command], cwd=ROOT, env=env,
                                    capture_output=True, text=True, encoding="utf-8", timeout=60)
        except subprocess.TimeoutExpired:
            print(f"超时：{' '.join(command)}")
            return 1
        if result.returncode != expected_code or (expected_status and expected_status not in result.stdout):
            print(f"失败：{' '.join(command)}，退出码 {result.returncode}（预期 {expected_code}）")
            if expected_status:
                print(f"预期输出包含状态：{expected_status}")
            print((result.stdout + result.stderr)[-6000:])
            return 1
        suffix = f"（预期停止：{expected_status}）" if expected_status else ""
        print(f"通过：{' '.join(command)}{suffix}")
    print(f"完成 {len(commands)} 个离线入口检查；没有调用付费模型。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
