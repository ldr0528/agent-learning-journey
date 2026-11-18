"""离线比较完整历史、截断历史和较早结果摘要，不调用模型 API。"""

from agent_learning.context import build_weather_context
from agent_learning.tools.weather import get_weather


def show_request(label, messages):
    print(f"\n{label}：{len(messages)} 条消息")
    for index, message in enumerate(messages, start=1):
        print(f"{index}. [{message['role']}] {message['content']}")
    # 固定例子的文本检查，不是通用答案正确性评估。
    content = "\n".join(message["content"] for message in messages)
    beijing_present = all(value in content for value in (
        "北京", "下雨，12℃", 'get_weather(city="北京")',
    ))
    print(f"北京的城市、结果与来源均在请求中：{beijing_present}")


def main():
    print("离线预览：执行本地模拟天气工具，构造请求，不发送给模型。")
    messages = [
        {"role": "system", "content": "根据工具结果比较模拟天气，不编造数据。"},
        {"role": "user", "content": "分别查询北京和上海的模拟天气，再比较哪里更暖和。"},
    ]
    for city in ("北京", "上海"):
        result = get_weather(city)
        messages.extend([
            {"role": "assistant", "content": f'Action: get_weather(city="{city}")'},
            {"role": "user", "content": f"Observation: {result}"},
        ])
    show_request("A. 完整历史", messages)
    show_request("B. 只保留最近两条历史", messages[:2] + messages[-2:])
    show_request("C. 较早证据摘要 + 最近两条历史", build_weather_context(messages))
    print("\n消息条数减少不代表 token 一定减少；此处没有测量 token 或模型回答质量。")


if __name__ == "__main__":
    main()
