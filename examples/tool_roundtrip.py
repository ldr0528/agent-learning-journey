"""模型请求工具 → 程序执行 → 回传 Observation → 模型回答。"""

import argparse
from openai import APIConnectionError, APIStatusError
from agent_learning.config import load_settings
from agent_learning.llm import ask_model
from agent_learning.tools.weather import execute_action

SYSTEM_PROMPT = """
你是一位天气助手，使用工具中的模拟数据回答问题。

可用工具：
get_weather(city: str)：查询指定城市的模拟天气。

规则：
1. 尚未收到 Observation 时，只输出一行工具请求：
   Action: get_weather(city="城市名称")
2. 收到 Observation 后，用简洁中文回答用户，明确这是模拟数据。
3. 如果工具返回“暂无天气数据”，说明无法依据现有数据回答，不要编造。
4. 不要把模拟结果描述成今天或实时的天气。
"""


def run_roundtrip(client, model, city, options):
    # ① 第一次请求：给模型工具说明与用户的问题。
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{city}天气怎么样？"},
    ]
    action = ask_model(client, model, messages, options)
    print("\n[1] 模型提出请求：", action)

    # ② Python 执行工具：action 来自模型，不再是手动复制的文字。
    result = execute_action(action)
    print("[2] Python 工具结果（模拟数据）：", result)
    if result.startswith("错误："):
        raise ValueError("工具请求格式不符合约定，未继续请求模型。")

    # ③ 关键步骤：把请求与结果追加到消息列表。
    messages.append({"role": "assistant", "content": action})
    messages.append({"role": "user", "content": f"Observation: {result}"})
    # 这是教材文字协议的简化练习；此处 user 消息由程序构造。
    # 尚未使用 API 原生的 tools / tool_calls / tool 消息。

    # ④ 第二次请求：模型这次能看到刚才的 Action 和 Observation。
    answer = ask_model(client, model, messages, options)
    print("[3] 模型根据工具结果回答：", answer)
    return answer


def main():
    parser = argparse.ArgumentParser(description="一次完整的工具结果回传")
    parser.add_argument("--city", default="上海")
    parser.add_argument("--provider", choices=["qwen", "openai"])
    args = parser.parse_args()
    if not args.city.strip():
        parser.error("城市不能为空。")
    try:
        settings = load_settings(args.provider)
        with settings.create_client() as client:
            run_roundtrip(client, settings.model, args.city.strip(), settings.request_options)
    except APIConnectionError:
        print("连接失败或超时。")
        return 1
    except APIStatusError as error:
        print(f"API 返回 HTTP {error.status_code}；请检查密钥、权限与额度。")
        return 1
    except ValueError as error:
        print(error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
