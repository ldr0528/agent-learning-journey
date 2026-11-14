"""有限工具循环：模型选择行动，程序执行并回传结果。

使用 Hello-Agents 第四章 §4.2 的文字协议思路；不执行任意模型代码。
"""

import re

from .llm import ask_model


def run_agent(client, model, question, options, max_steps=5, *,
              system_prompt, tool_executor, finish_validator=None, budget_context=False):
    """max_steps 是模型请求上限，工具执行和引用纠错都在同一预算内。"""
    if max_steps < 1:
        raise ValueError("max_steps 必须至少为 1。")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]
    tool_calls = 0
    for step in range(1, max_steps + 1):
        request_messages = messages
        if budget_context:
            # 包含即将发出的本次请求；预算提示只用于这一轮，不积累到历史。
            remaining_calls = max_steps - step + 1
            budget_hint = (
                f"运行预算：本轮是第 {step}/{max_steps} 次模型请求，"
                f"包含本次，还可以请求模型 {remaining_calls} 次。"
            )
            request_messages = messages + [{"role": "user", "content": budget_hint}]
            print(f"\n[请求上下文] {budget_hint}")
        action = ask_model(client, model, request_messages, options)
        print(f"\n[第 {step} 轮] {action}")
        messages.append({"role": "assistant", "content": action})

        finish = re.fullmatch(r"Action:\s*Finish\[(.+)\]", action, re.DOTALL)
        if finish and finish.group(1).strip():
            answer = finish.group(1).strip()
            error = finish_validator(answer) if finish_validator else None
            if error:
                print(f"Observation: {error}")
                messages.append({"role": "user", "content": f"Observation: {error}"})
                continue
            print(f"\n任务结束：{answer}")
            print(f"模型请求 {step} 次；工具执行 {tool_calls} 次。")
            return {"status": "finished", "answer": answer, "steps": step, "tool_calls": tool_calls}

        result = tool_executor(action)
        if not result.startswith("错误："):
            tool_calls += 1
        print(f"Observation: {result}")
        # 当前为教学文字协议，尚未使用 API 原生 tool 消息。
        messages.append({"role": "user", "content": f"Observation: {result}"})

    print(f"\n达到 {max_steps} 轮上限，任务未完成。")
    print(f"模型请求 {max_steps} 次；工具执行 {tool_calls} 次。")
    return {"status": "step_limit", "answer": None, "steps": max_steps, "tool_calls": tool_calls}
