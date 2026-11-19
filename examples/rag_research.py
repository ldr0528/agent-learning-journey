"""课程研究工作流；默认离线摘录，--live 请求一次真实模型。"""

import argparse
from pathlib import Path

from openai import APIConnectionError, APIStatusError

from agent_learning.agents.rag import render_report, run_rag
from agent_learning.config import load_settings
from agent_learning.llm import ask_model


def main():
    parser = argparse.ArgumentParser(description="带来源的课程研究报告")
    parser.add_argument("--question", default="RAG 为什么要保留来源？")
    parser.add_argument("--live", action="store_true", help="使用配置的模型生成回答，会产生 API 用量")
    parser.add_argument("--provider", choices=["qwen", "openai"])
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--context-chars", type=int, default=1800)
    parser.add_argument("--output", type=Path, help="另存 Markdown 报告")
    args = parser.parse_args()
    try:
        kwargs = {"top_k": args.top_k, "max_context_chars": args.context_chars}
        if args.live:
            settings = load_settings(args.provider)
            with settings.create_client() as client:
                report = run_rag(args.question, generation_mode="live", generate=lambda messages: ask_model(
                    client, settings.model, messages, settings.request_options), **kwargs)
        else:
            report = run_rag(args.question, **kwargs)
        text = render_report(report)
        print(text)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
    except APIConnectionError:
        print("模型连接失败或超时。")
        return 1
    except APIStatusError as error:
        print(f"API 返回 HTTP {error.status_code}；请检查权限与额度。")
        return 1
    except (ValueError, OSError) as error:
        print(str(error))
        return 1
    return 1 if report["status"] == "invalid_answer" else 0


if __name__ == "__main__":
    raise SystemExit(main())
