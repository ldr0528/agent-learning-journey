"""真实 LangGraph 离线实验；--live 才调用已配置的模型 API。"""

import argparse
from contextlib import ExitStack

from agent_learning.integrations.langgraph_workflow import (
    build_question_graph, build_weather_graph, initial_weather_state,
)


WEATHER_QUESTION = "分别查询北京和上海的模拟天气，再比较哪里更暖和。"


def main():
    parser = argparse.ArgumentParser(description="LangGraph 三步问答与有限天气循环")
    parser.add_argument("--question")
    parser.add_argument("--live", action="store_true", help="调用已配置模型；默认不读取密钥")
    parser.add_argument("--provider", choices=["qwen", "openai"])
    parser.add_argument("--loop", action="store_true", help="运行 model/tool 条件循环")
    parser.add_argument("--max-steps", type=int, default=3)
    parser.add_argument("--checkpoint", action="store_true", help="查看三步图的进程内快照")
    args = parser.parse_args()
    if args.max_steps < 1 or (args.question is not None and not args.question.strip()):
        parser.error("问题不能为空，--max-steps 必须至少为 1。")
    if args.loop and args.checkpoint:
        parser.error("--checkpoint 用于三步问答图，请去掉 --loop。")
    if args.loop and not args.live and args.question not in (None, WEATHER_QUESTION):
        parser.error("离线循环只演示默认天气问题；自定义问题请加 --live。")
    try:
        with ExitStack() as stack:
            generate = None
            if args.live:
                from agent_learning.config import load_settings
                from agent_learning.llm import ask_model
                settings = load_settings(args.provider)
                client = stack.enter_context(settings.create_client())
                generate = lambda messages: ask_model(client, settings.model, messages, settings.request_options)
                print(f"真实模型模式：{settings.provider} / {settings.model}")
            else:
                print("离线模式：真实 LangGraph 调度、本地工具；回答由确定性摘录或预设回复产生，不调用模型。")

            if args.loop:
                if generate is None:
                    replies = iter(['Action: get_weather(city="北京")', 'Action: get_weather(city="上海")',
                                    'Action: Finish[上海更暖和（22℃ vs 北京12℃），数据为模拟天气。]'])
                    generate = lambda messages: next(replies)
                app = build_weather_graph(generate, max_steps=args.max_steps)
                state = app.invoke(initial_weather_state(args.question or WEATHER_QUESTION),
                                   {"recursion_limit": 2 * args.max_steps + 3})
                print(f'状态：{state["status"]}；模型决策节点 {state["requests"]} 次；工具执行 {state["tool_calls"]} 次。')
                print(f'回答：{state["answer"] or "未取得有效 Finish"}')
                return 0 if state["status"] == "finished" else 1

            checkpointer = None
            if args.checkpoint:
                from langgraph.checkpoint.memory import InMemorySaver
                checkpointer = InMemorySaver()
            app = build_question_graph(generate, checkpointer=checkpointer)
            config = {"configurable": {"thread_id": "learning-demo"}} if args.checkpoint else {}
            state = app.invoke({"question": args.question or "Action 和 Observation 分别由谁产生？", "trace": []}, config)
            print("节点：" + " -> ".join(state["trace"]))
            print("检索词：" + state["query"])
            print("资料：" + (", ".join(note["id"] for note in state["notes"]) or "无"))
            print("回答：" + state["answer"])
            if args.checkpoint:
                snapshot = app.get_state(config)
                print(f'进程内快照：trace={snapshot.values["trace"]}；待执行节点={snapshot.next}')
    except (ImportError, RuntimeError) as error:
        print(str(error) if isinstance(error, RuntimeError) else '缺少可选依赖，请运行 python -m pip install -e ".[graph]"。')
        return 1
    except ValueError as error:
        print(error)
        return 1
    except Exception as error:
        # API 异常不打印原始响应或认证内容。
        print(f"工作流未完成：{type(error).__name__}。请检查连接、配置和当前步骤。")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
