"""Run one live course example and save a reviewable, credential-free transcript.

Explicit invocation makes real API requests. CI never invokes this script.
Only request/response fields needed to explain the lesson are recorded.
"""

import argparse
from contextlib import redirect_stdout
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
import io
import json
from pathlib import Path
import platform
import runpy
import subprocess
import sys
from time import perf_counter
from unittest.mock import patch

from agent_learning.config import Settings


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CASES = {
    "planning": ("examples.plan_solve", ["--provider", "qwen"]),
    "reflection": ("examples.reflection", ["--provider", "qwen"]),
    "rag-answer": ("examples.rag_research", ["--live", "--provider", "qwen", "--question", "RAG 为什么要保留来源与引用？"]),
    "rag-missing": ("examples.rag_research", ["--live", "--provider", "qwen", "--question", "RAG 服务每月收费多少钱？"]),
    "langgraph-checkpoint": ("examples.langgraph_workflow", ["--live", "--provider", "qwen", "--checkpoint"]),
    "langgraph-loop": ("examples.langgraph_workflow", ["--live", "--provider", "qwen", "--loop"]),
    "mcp": ("examples.mcp_demo", ["--live", "--provider", "qwen"]),
    "insurance-demo": ("examples.insurance_compare", ["--live", "--output", "outputs/insurance-demo-result.json"]),
    "insurance-official": ("examples.insurance_compare", ["--live", "--catalog", "official",
        "--request", "examples/insurance_official_request.json", "--output", "outputs/insurance-official-result.json"]),
    "insurance-consultation": ("examples.insurance_consultation", ["--live", "--output", "outputs/insurance-consultation-result.json"]),
}
REQUEST_FIELDS = ("model", "messages", "tools", "tool_choice", "max_tokens", "max_completion_tokens",
                  "temperature", "reasoning_effort", "extra_body", "parallel_tool_calls", "response_format")


def clone(value):
    return json.loads(json.dumps(value, ensure_ascii=False))


def sanitize(text, secrets):
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    text = text.replace(str(ROOT), "[WORKSPACE]").replace(ROOT.as_posix(), "[WORKSPACE]")
    return text


def sanitize_record(value, secrets):
    """Redact strings before JSON escaping, including nested Windows paths."""
    if isinstance(value, str):
        return sanitize(value, secrets)
    if isinstance(value, list):
        return [sanitize_record(item, secrets) for item in value]
    if isinstance(value, dict):
        return {sanitize(key, secrets): sanitize_record(item, secrets) for key, item in value.items()}
    return value


class Recorder:
    def __init__(self):
        self.calls = []
        self.secrets = []
        self.provider = None

    def wrap(self, settings, create_client):
        self.secrets.append(settings.api_key)
        self.provider = settings.provider
        client = create_client(settings)
        original = client.chat.completions.create

        def create(**kwargs):
            call = {"index": len(self.calls) + 1,
                    "started_at_utc": datetime.now(timezone.utc).isoformat(),
                    "request": clone({key: kwargs[key] for key in REQUEST_FIELDS if key in kwargs})}
            self.calls.append(call)
            started = perf_counter()
            try:
                response = original(**kwargs)
                # Never save authentication, raw HTTP headers, request IDs or client repr.
                call["response"] = {
                    "model": response.model,
                    "choices": [{"index": choice.index, "finish_reason": choice.finish_reason,
                                 "message": {key: value for key, value in choice.message.model_dump(mode="json").items()
                                             if key in ("role", "content", "tool_calls") and value is not None}}
                                for choice in response.choices],
                    "usage": response.usage.model_dump(mode="json") if response.usage else None,
                }
                return response
            except Exception as error:
                call["error_type"] = type(error).__name__
                raise
            finally:
                call["elapsed_seconds"] = round(perf_counter() - started, 3)

        client.chat.completions.create = create
        return client


def source_manifest():
    files = [ROOT / "pyproject.toml"]
    for folder in ("src", "examples", "scripts"):
        files.extend((ROOT / folder).rglob("*.py"))
    files.extend((ROOT / "src/agent_learning/data").glob("*.json"))
    files.extend((ROOT / "examples").glob("*.json"))
    files.extend(path for path in (ROOT / "src/agent_learning/insurance/static").glob("*") if path.is_file())
    return {path.relative_to(ROOT).as_posix(): sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for path in sorted(files) if "__pycache__" not in path.parts}


def render_transcript(record):
    lines = [f'# 运行记录：{record["case"]}', "",
             f'- 开始时间（UTC）：{record["started_at_utc"]}',
             f'- 服务：{record["provider"]}；请求模型：{record["requested_models"]}',
             f'- API 尝试：{record["api_attempts"]}；成功返回：{record["api_responses"]}；退出码：{record["exit_code"]}',
             f'- 服务商报告 token：{record["total_tokens"]}；未返回用量的调用：{record["calls_without_usage"]}',
             f'- 源码基准提交：`{record["source_commit"]}`；执行时源码有未提交改动：`{record["source_dirty"]}`',
             '- 完整请求、响应与源码文件指纹见同名 JSON；资料性质以各例的目录标记为准。',
             '- Markdown 展示仅去除行尾空格和文件末尾空行；JSON 保留原始文本。', "",
             "## 复现命令", "", "```bash", record["command"], "```", "", "## 程序输出", "", "```text",
             record["stdout"].rstrip(), "```", "", "## 逐次模型响应", ""]
    for call in record["calls"]:
        lines.extend([f'### 请求 {call["index"]}', ""])
        response = call.get("response")
        if not response:
            lines.extend([f'未取得响应：{call.get("error_type", "unknown")}。', ""])
            continue
        for choice in response["choices"]:
            lines.extend([f'结束原因：`{choice["finish_reason"]}`；响应模型：`{response["model"]}`。', ""])
            message = choice["message"]
            if message.get("content"):
                lines.extend(["````text", message["content"], "````", ""])
            if message.get("tool_calls"):
                lines.extend(["```json", json.dumps(message["tool_calls"], ensure_ascii=False, indent=2), "```", ""])
    return "\n".join(line.rstrip() for line in "\n".join(lines).splitlines()).rstrip()


def main():
    parser = argparse.ArgumentParser(description="调用模型并保存请求与响应记录")
    parser.add_argument("case", choices=CASES)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/live-runs"))
    args = parser.parse_args()
    target = args.output_dir / args.case
    if target.with_suffix(".json").exists() or target.with_suffix(".md").exists():
        parser.error("目标记录已存在；请用新的目录保留下一次运行，不覆盖已有样本。")
    module, arguments = CASES[args.case]
    recorder = Recorder()
    original_create = Settings.create_client
    captured = io.StringIO()
    manifest = source_manifest()
    record = {"case": args.case, "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "command": "python -m " + module + " " + " ".join(json.dumps(arg, ensure_ascii=False) if " " in arg else arg for arg in arguments),
              "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "source_dirty": bool(subprocess.run(["git", "status", "--porcelain", "--", "src", "examples", "scripts", "pyproject.toml"], cwd=ROOT, capture_output=True).stdout),
              "source_files_sha256": manifest,
              "python": platform.python_version(), "platform": platform.system(),
              "packages": {name: version(name) for name in ("openai", "python-dotenv", "agent-learning-journey")}}
    for name in ("langgraph", "mcp"):
        try:
            record["packages"][name] = version(name)
        except Exception:
            pass
    started = perf_counter()
    with patch.object(Settings, "create_client", lambda settings: recorder.wrap(settings, original_create)), \
            patch.object(sys, "argv", [module, *arguments]), redirect_stdout(captured):
        try:
            runpy.run_module(module, run_name="__main__")
            exit_code = 0
        except SystemExit as error:
            exit_code = error.code if isinstance(error.code, int) else 1
        except Exception as error:
            print(f"运行异常：{type(error).__name__}；不记录可能含敏感信息的异常正文。")
            exit_code = 1
    record.update({"elapsed_seconds": round(perf_counter() - started, 3), "exit_code": exit_code,
                   "provider": recorder.provider, "calls": recorder.calls, "stdout": captured.getvalue(),
                   "api_attempts": len(recorder.calls),
                   "api_responses": sum("response" in call for call in recorder.calls),
                   "requested_models": sorted({call["request"]["model"] for call in recorder.calls})})
    usage = [call.get("response", {}).get("usage") for call in recorder.calls]
    record["total_tokens"] = sum(item["total_tokens"] for item in usage if item and item.get("total_tokens") is not None)
    record["calls_without_usage"] = sum(not item or item.get("total_tokens") is None for item in usage)
    record = sanitize_record(record, recorder.secrets)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.with_suffix(".json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    target.with_suffix(".md").write_text(render_transcript(record) + "\n", encoding="utf-8")
    print(json.dumps({key: record[key] for key in ("case", "exit_code", "api_attempts", "api_responses", "total_tokens")}, ensure_ascii=False))
    print(f"记录已保存：{target.with_suffix('.md')}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
