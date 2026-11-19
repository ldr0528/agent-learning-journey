"""有限的初稿、评审、修订循环；状态与结果的正确性分开表达。

参考 Hello-Agents 第四章 §4.4，将代码优化案例改为文字解释修订。
不执行模型生成的代码；评审通过仍是模型判断，不是外部事实认证。
"""

import json

from ..llm import ask_model


DRAFT_PROMPT = "请依据用户任务及其中给定的事实写出简洁答案，保留必要条件和资料不足说明。"
REVIEW_PROMPT = """请根据原任务的目标、约束和给定事实评审当前草稿。
检查事实错误、遗漏条件及含混表述，不凭空引入额外事实。
只输出 JSON 对象，含 verdict 和 feedback 两项。
verdict 只能为 accept 或 revise；feedback 是非空字符串，指出通过依据或具体改进点。
满足任务时 accept，需要修改时 revise。不要直接替换成新答案。
"""
REVISE_PROMPT = """请结合原任务、当前草稿和评审反馈，输出修订后的完整答案。
保持对原任务及给定事实的遵守；反馈有误时以原任务中的事实为准。
只输出修订答案，不输出修改过程或额外对话。
"""


def parse_review(text):
    lines = text.strip().splitlines()
    if len(lines) >= 3 and lines[0] in {"```json", "```"} and lines[-1] == "```":
        text = "\n".join(lines[1:-1])
    try:
        review = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError("评审需要返回 JSON 对象。") from error
    if not isinstance(review, dict) or review.get("verdict") not in ("accept", "revise"):
        raise ValueError("评审 verdict 必须为 accept 或 revise。")
    feedback = review.get("feedback")
    if not isinstance(feedback, str) or not feedback.strip():
        raise ValueError("评审 feedback 必须是非空字符串。")
    return {"verdict": review["verdict"], "feedback": feedback.strip()}


def run_reflection(client, model, task, options, *, max_revisions=2,
                   max_calls=6, model_call=None):
    """总预算覆盖初稿、每次评审和每次修订；只有 accept 才设置 answer。"""
    if not task.strip():
        raise ValueError("任务不能为空。")
    if max_revisions < 0 or max_calls < 1:
        raise ValueError("max_revisions 不能为负，max_calls 必须至少为 1。")
    request = model_call or ask_model
    state = {"status": "running", "draft": None, "answer": None, "history": [],
             "reviews": [], "revisions": 0, "model_calls": 0, "tool_calls": 0, "error": None}

    def call(prompt, data):
        state["model_calls"] += 1
        messages = [{"role": "system", "content": prompt},
                    {"role": "user", "content": json.dumps(data, ensure_ascii=False, indent=2)}]
        return request(client, model, messages, options)

    draft = call(DRAFT_PROMPT, {"task": task})
    if not isinstance(draft, str) or not draft.strip():
        state.update(status="invalid_result", error="初稿没有返回非空文本。")
        return state
    state["draft"] = draft.strip()
    state["history"].append({"type": "draft", "version": 0, "content": state["draft"]})
    print(f"[初稿]\n{state['draft']}")

    while True:
        if state["model_calls"] >= max_calls:
            state["status"] = "call_limit"
            return state
        raw_review = call(REVIEW_PROMPT, {"task": task, "draft": state["draft"]})
        try:
            if not isinstance(raw_review, str):
                raise ValueError("评审没有返回文本。")
            review = parse_review(raw_review)
        except ValueError as error:
            state.update(status="invalid_review", error=str(error))
            return state
        state["reviews"].append({**review, "version": state["revisions"]})
        state["history"].append({"type": "review", "version": state["revisions"], **review})
        print(f"\n[评审 {len(state['reviews'])}] {review['verdict']}\n反馈：{review['feedback']}")
        if review["verdict"] == "accept":
            state.update(status="accepted", answer=state["draft"])
            return state
        if state["revisions"] >= max_revisions:
            state["status"] = "revision_limit"
            return state
        if state["model_calls"] >= max_calls:
            state["status"] = "call_limit"
            return state

        revised = call(REVISE_PROMPT, {"task": task, "draft": state["draft"], "feedback": review["feedback"]})
        if not isinstance(revised, str) or not revised.strip():
            state.update(status="invalid_result", error="修订没有返回非空文本。")
            return state
        state["revisions"] += 1
        state["draft"] = revised.strip()
        state["history"].append({"type": "revision", "version": state["revisions"], "content": state["draft"]})
        print(f"\n[修订 {state['revisions']}]\n{state['draft']}")
