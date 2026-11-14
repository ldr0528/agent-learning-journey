"""使用模拟天气工具的 Agent。"""

from ..loop import run_agent
from ..tools.weather import execute_action

SYSTEM_PROMPT = """
你是一位使用模拟天气工具的助手，根据问题和已经收到的工具结果决定下一步。

可用工具：get_weather(city: str)，查询一个城市的模拟天气。
每次只输出一个 Action，格式只能是以下两种之一：
1. Action: get_weather(city="城市名称")
2. Action: Finish[最终回答]

规则：
- 需要某城市的数据且尚未查询时，调用工具；一次只查询一个城市。
- 收到 Observation 后检查信息是否足够；不足时继续查询其他需要的城市。
- 不要重复查询已经得到结果的城市；“暂无天气数据”也是查询结果。
- 信息足够时用 Finish 回答，明确注明是模拟数据。
- 如果缺少数据导致无法比较，用 Finish 说明缺少什么，不要编造。
- 不要把模拟数据说成实时天气。不输出额外说明或代码块。
"""


def run_weather(client, model, question, options, max_steps=5):
    return run_agent(client, model, question, options, max_steps,
                     system_prompt=SYSTEM_PROMPT, tool_executor=execute_action)
