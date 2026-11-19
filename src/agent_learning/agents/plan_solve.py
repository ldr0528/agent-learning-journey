"""先规划、再依序求解；总调用预算同时覆盖两个阶段。

参考 Hello-Agents 第四章 §4.3。本例是文本推理，不调用外部工具。
finished 表示执行完计划，不证明计划或答案在语义上正确。
"""

import json

from ..llm import ask_model
from .planning import PLANNER_PROMPT, parse_plan


EXECUTOR_PROMPT = """请依据原问题、完整计划、已完成步骤及其结果，完成当前步骤。
只返回当前步骤的结果和必要算式；若当前步骤是最终汇总，直接回答原问题。
已有结果与题目冲突时指出冲突，不把未经验证的中间结果当作正确事实。
不要声称调用了工具，不要提前执行后面的步骤。
"""


def run_plan_solve(client, model, question, options, *, max_calls=6,
                   max_plan_steps=5, model_call=None):
    """model_call 可注入离线回复；默认使用真实模型适配器。"""
    if not question.strip():
        raise ValueError("问题不能为空。")
    if max_calls < 1 or max_plan_steps < 1:
        raise ValueError("max_calls 与 max_plan_steps 必须至少为 1。")
    request = model_call or ask_model
    state = {"status": "running", "plan": [], "history": [], "answer": None,
             "model_calls": 0, "tool_calls": 0, "error": None}
    planner_messages = [
        {"role": "system", "content": PLANNER_PROMPT + f"\n计划最多包含 {max_plan_steps} 个步骤。"},
        {"role": "user", "content": question},
    ]
    state["model_calls"] += 1
    raw_plan = request(client, model, planner_messages, options)
    print(f"[规划器原始输出]\n{raw_plan}")
    try:
        if not isinstance(raw_plan, str):
            raise ValueError("规划器没有返回文本。")
        state["plan"] = parse_plan(raw_plan)
        if len(state["plan"]) > max_plan_steps:
            raise ValueError(f"计划超过 {max_plan_steps} 步上限。")
    except ValueError as error:
        state.update(status="invalid_plan", error=str(error))
        return state

    for index, step in enumerate(state["plan"], start=1):
        if state["model_calls"] >= max_calls:
            state["status"] = "call_limit"
            return state
        step_input = {"question": question, "plan": state["plan"],
                      "history": state["history"], "current_step": {"number": index, "task": step}}
        messages = [
            {"role": "system", "content": EXECUTOR_PROMPT},
            {"role": "user", "content": json.dumps(step_input, ensure_ascii=False, indent=2)},
        ]
        state["model_calls"] += 1
        result = request(client, model, messages, options)
        if not isinstance(result, str) or not result.strip():
            state.update(status="invalid_result", error=f"第 {index} 步没有返回非空文本。")
            return state
        state["history"].append({"step": index, "task": step, "result": result.strip()})
        print(f"\n[执行 {index}/{len(state['plan'])}] {step}\n结果：{result.strip()}")

    state.update(status="finished", answer=state["history"][-1]["result"])
    return state
