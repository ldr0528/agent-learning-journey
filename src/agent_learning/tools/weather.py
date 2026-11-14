"""独立工具：把工具调用请求交给 Python 执行。

配合 Hello-Agents 第一章 §1.2.3 和 §1.3.3 的教学简化练习。
这里只使用模拟天气，不调用模型，也不查询真实天气。
可由独立示例手动调用，也可作为 Agent Loop 的工具执行器。
"""

import re


def get_weather(city):
    """练习用的模拟天气工具。"""
    weather_data = {
        "北京": "下雨，12℃",
        "上海": "晴天，22℃",
    }
    return weather_data.get(city, "暂无天气数据")


def execute_action(action):
    # 只接受这个约定格式：Action: get_weather(city="城市名称")。
    # fullmatch 检查整行；括号中的捕获组提取城市名。
    match = re.fullmatch(r'Action:\s*get_weather\(city="([^"\r\n]+)"\)', action.strip())
    if match is None:
        return "错误：无法识别工具请求，请检查工具名称和参数格式。"

    city = match.group(1)
    # 真正的工具执行发生在这里：我们调用自己定义的 Python 函数。
    return get_weather(city)
