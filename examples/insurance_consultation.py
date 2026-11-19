"""同一个公开场景：整理需求、显式确认范围、查证、追问。"""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_learning.insurance.service import run_message, run_session
from agent_learning.insurance.store import SessionStore


def main():
    parser = argparse.ArgumentParser(description="医疗险咨询的完整对话场景")
    parser.add_argument("--live", action="store_true", help="请求配置的模型，产生 API 用量")
    parser.add_argument("--output", type=Path, help="保存案例的需求、报告和追问 JSON")
    args = parser.parse_args()
    mode = "live" if args.live else "offline"
    with TemporaryDirectory(prefix="insurance-consultation-") as directory:
        store = SessionStore(directory)
        session_id = store.create({})
        question = "我30岁，有医保，年预算2000元，主要关注普通门诊和续保，想比较两份医疗险资料。"
        print("问题：" + question)
        intake = run_message(store, session_id, question, mode=mode, expected_version=1)
        print("\n需求整理：" + intake["content"])
        if not intake.get("proposal"):
            return 1
        # 本例明确给出用户的确认动作；真实页面由用户选择产品并核对需求。
        request = intake["proposal"]["request"]
        request["selections"] = [{"product_id": "demo_hospital", "version": "demo-v1"},
                                 {"product_id": "demo_outpatient", "version": "demo-v1"}]
        confirmed = store.update_brief(session_id, request, expected_version=1, confirm=True)
        print("\n确认范围：教学计划 A 与 B，资料版本 demo-v1。")
        report = run_session(store, session_id, mode=mode, expected_version=confirmed["brief_version"])
        print(f"比较状态：{report['status']}；维度：{len(report['rows'])}；来源：{len(report['sources'])}。")
        if report["status"] not in ("completed", "completed_with_gaps"):
            return 1
        followup_question = "普通门诊保障有什么区别？这些资料能否说明2000元预算够不够？"
        followup = run_message(store, session_id, followup_question, intent="followup", mode=mode,
                               expected_version=store.load(session_id)["brief_version"])
        print("\n追问：" + followup_question + "\n\n" + followup["content"])
        print("\n模型请求：" + str(sum(item.get("model_calls", 0) for item in (intake, report, followup))))
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps({"scenario": "门诊与续保咨询", "mode": mode,
                "intake": intake, "confirmed_request": request, "report": report,
                "followup_question": followup_question, "followup": followup}, ensure_ascii=False, indent=2), encoding="utf-8")
        return int(followup["status"] not in ("answered", "partial_answer"))


if __name__ == "__main__":
    raise SystemExit(main())
