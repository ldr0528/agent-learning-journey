"""手动给定 Action，独立执行工具；不调用模型。"""

from agent_learning.tools.weather import execute_action


def main():
    action = 'Action: get_weather(city="上海")'
    print(f"工具请求：{action}")
    print(f"Observation（模拟天气）：{execute_action(action)}")


if __name__ == "__main__":
    main()
