"""天气文字协议的上下文整理：较早结果摘要 + 最近一组消息。

参考 Hello-Agents 第九章 §9.2.3；这是规则整理的教学扩展，
不是模型生成摘要、token 预算管理或通用上下文压缩器。
"""

import re


def summarize_records(records):
    """将每条记录的城市、结果、来源写成一行。"""
    lines = []
    for record in records:
        lines.append(
            f'{record["city"]}：{record["result"]}（来源：{record["source"]}）'
        )
    return "\n".join(lines)


def build_weather_context(messages):
    """根据完整历史生成本轮输入，不修改原历史。

仅整理能够配对的天气 Action 和 Observation。
遇到格式错误等其他历史时保留完整消息，避免遗漏纠错信息。
"""
    base_messages = messages[:2]
    history = messages[2:]
    if len(history) <= 2 or len(history) % 2:
        return list(messages)

    records = []
    for index in range(0, len(history) - 2, 2):
        action, observation = history[index:index + 2]
        if action["role"] != "assistant" or observation["role"] != "user":
            return list(messages)
        match = re.fullmatch(r'Action:\s*(get_weather\(city="([^"\r\n]+)"\))',
                             action["content"].strip())
        if match is None or not observation["content"].startswith("Observation: "):
            return list(messages)
        result = observation["content"][len("Observation: "):]
        if not result.strip() or result.startswith("错误："):
            return list(messages)
        records.append({"city": match.group(2), "result": result, "source": match.group(1)})

    summary = summarize_records(records)
    summary_message = {"role": "user", "content": "较早工具结果摘要（模拟数据）：\n" + summary}
    recent_history = history[-2:]
    print(f"\n[历史摘要] {len(history) - 2} 条较早消息整理为 1 条；保留最近 2 条。")
    print(summary_message["content"])
    return base_messages + [summary_message] + recent_history
