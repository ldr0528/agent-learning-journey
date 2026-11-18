"""先生成计划：python -m examples.plan_first；--demo 为固定离线示意。"""

import argparse

from openai import APIConnectionError, APIStatusError

from agent_learning.agents.planning import make_plan, parse_plan
from agent_learning.config import load_settings


QUESTION = "水果店三天卖苹果：周一15个；周二销量为周一的2倍；周三比周二少5个。求三天总销量。"
DEMO_PLAN = '["根据周一销量计算周二销量", "根据周二销量计算周三销量", "将三天的销量相加得到总销量"]'


def main():
    parser = argparse.ArgumentParser(description="Plan-and-Solve 第一部分：规划器")
    parser.add_argument("--provider", choices=["qwen", "openai"])
    parser.add_argument("--question", default=QUESTION)
    parser.add_argument("--demo", action="store_true", help="展示固定示意计划，不读取配置或请求 API")
    args = parser.parse_args()
    if not args.question.strip():
        parser.error("问题不能为空。")
    if args.demo and args.question != QUESTION:
        parser.error("--demo 只演示默认题；自定义问题请去掉 --demo。")

    print(f"问题：{args.question}")
    if args.demo:
        print("离线示意：以下计划由程序预设，不是模型实测输出。")
        plan = parse_plan(DEMO_PLAN)
    else:
        try:
            settings = load_settings(args.provider)
            print(f"服务：{settings.provider} / {settings.model}；仅请求一次模型生成计划。")
            with settings.create_client() as client:
                plan = make_plan(client, settings.model, args.question, settings.request_options)
        except APIConnectionError:
            print("连接失败或超时。")
            return 1
        except APIStatusError as error:
            print(f"API 返回 HTTP {error.status_code}；请检查密钥、权限与额度。")
            return 1
        except ValueError as error:
            print(error)
            return 1

    print(f"\n计划已解析：{len(plan)} 步。")
    for index, step in enumerate(plan, start=1):
        print(f"{index}. {step}")
    print("\n当前只完成计划生成与格式检查，尚未执行任何步骤。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
