"""Hello-Agents 第四章 §4.3.2 的规划阶段练习。

复用已有模型接口；本项目采用 JSON 字符串数组承载计划。
仅生成、解析计划，尚未实现 §4.3.3 的执行器。
"""

import json

from ..llm import ask_model


PLANNER_PROMPT = """请将用户的问题拆成一组按依赖顺序排列、可以逐步完成的任务。
这里只规划要做什么，暂不计算中间数值或最终答案，也不调用工具。
每个步骤写清要处理的对象；需要先前步骤的结果时明确指出。
最后一步应当完成用户的目标。不要把一个步骤拆成大量琐碎动作。
只输出一个非空 JSON 数组，每个元素是非空的步骤说明字符串。
不要输出 Markdown 代码块、标题或数组外的说明。
"""


def parse_plan(text):
    """检查数据形状；这不代表计划在语义上正确或完整。"""
    lines = text.strip().splitlines()
    if len(lines) >= 3 and lines[0] in {"```json", "```"} and lines[-1] == "```":
        text = "\n".join(lines[1:-1])
    try:
        plan = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError("计划解析失败：模型需要输出 JSON 字符串数组。") from error
    if not isinstance(plan, list) or not plan:
        raise ValueError("计划必须是非空的步骤列表。")
    if any(not isinstance(step, str) or not step.strip() for step in plan):
        raise ValueError("计划中的每一步都必须是非空字符串。")
    return [step.strip() for step in plan]


def make_plan(client, model, question, options):
    if not question.strip():
        raise ValueError("问题不能为空。")
    messages = [
        {"role": "system", "content": PLANNER_PROMPT},
        {"role": "user", "content": question},
    ]
    raw_plan = ask_model(client, model, messages, options)
    print(f"\n[规划器原始输出]\n{raw_plan}")
    return parse_plan(raw_plan)
