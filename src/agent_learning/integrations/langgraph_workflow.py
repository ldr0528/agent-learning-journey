"""真实 LangGraph 工作流；模型调用由调用方显式注入。"""

import re
from typing import TypedDict

from ..agents.weather import SYSTEM_PROMPT
from ..tools.notes import format_results, search_notes
from ..tools.weather import execute_action


class QuestionState(TypedDict, total=False):
    question: str
    query: str
    notes: list
    answer: str
    trace: list[str]


class WeatherState(TypedDict, total=False):
    messages: list[dict]
    action: str
    answer: str | None
    requests: int
    tool_calls: int
    status: str


def graph_api():
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as error:
        raise RuntimeError('缺少 LangGraph，请先运行 python -m pip install -e ".[graph]"。') from error
    return StateGraph, START, END


def build_question_graph(generate=None, *, checkpointer=None):
    """理解→检索→回答；generate(messages) 可注入真实模型请求。"""
    StateGraph, START, END = graph_api()

    def understand(state):
        question = state["question"].strip()
        if not question:
            raise ValueError("问题不能为空。")
        query = generate([
            {"role": "system", "content": "将问题整理为简短检索词，只输出检索词，保留 Action、Observation、Agent Loop 等原术语。"},
            {"role": "user", "content": question},
        ]) if generate else question
        return {"query": query, "trace": [*state.get("trace", []), "understand"]}

    def search(state):
        notes = search_notes(state["query"])
        return {"notes": notes, "trace": [*state["trace"], "search"]}

    def answer(state):
        notes = state["notes"]
        if not notes:
            text = "资料不足：当前本地摘要没有匹配结果，不能据此判断教材没有相关内容。"
        elif generate:
            text = generate([
                {"role": "system", "content": "仅依据给定教学摘要回答，引用对应的 [Nxx] 编号。命中不等于能回答；资料不足时以“资料不足：”开头，只说明缺少什么，不补写答案。"},
                {"role": "user", "content": f'问题：{state["question"]}\n资料：\n{format_results(notes)}'},
            ])
            ids = set(re.findall(r"\[\s*(N\d+)\s*\]", text))
            allowed = {note["id"] for note in notes}
            insufficient = text.strip().startswith("资料不足：")
            if not ids <= allowed or (not ids and not insufficient):
                raise ValueError("回答未引用本次资料或引用了未知编号；本示例停止，不自动修补引用。")
        else:
            text = "\n".join(f'{note["content"]} [{note["id"]}]' for note in notes)
        return {"answer": text, "trace": [*state["trace"], "answer"]}

    graph = StateGraph(QuestionState)
    graph.add_node("understand", understand)
    graph.add_node("search", search)
    graph.add_node("answer", answer)
    graph.add_edge(START, "understand")
    graph.add_edge("understand", "search")
    graph.add_edge("search", "answer")
    graph.add_edge("answer", END)
    return graph.compile(checkpointer=checkpointer)


def build_weather_graph(decide, *, max_steps=5):
    """将有限天气循环映射为 model/tool 节点；max_steps 仍限制模型请求。"""
    if max_steps < 1:
        raise ValueError("max_steps 必须至少为 1。")
    StateGraph, START, END = graph_api()

    def model(state):
        action = decide(state["messages"])
        finish = re.fullmatch(r"Action:\s*Finish\[(.+)\]", action, re.DOTALL)
        finished = bool(finish and finish.group(1).strip())
        return {
            "messages": state["messages"] + [{"role": "assistant", "content": action}],
            "action": action, "requests": state["requests"] + 1,
            "status": "finished" if finished else "running",
            "answer": finish.group(1).strip() if finished else None,
        }

    def tool(state):
        observation = execute_action(state["action"])
        return {
            "messages": state["messages"] + [{"role": "user", "content": f"Observation: {observation}"}],
            "tool_calls": state["tool_calls"] + int(not observation.startswith("错误：")),
            "status": "step_limit" if state["requests"] >= max_steps else "running",
        }

    graph = StateGraph(WeatherState)
    graph.add_node("model", model)
    graph.add_node("tool", tool)
    graph.add_edge(START, "model")
    graph.add_conditional_edges("model", lambda state: "end" if state["status"] == "finished" else "tool",
                                {"end": END, "tool": "tool"})
    graph.add_conditional_edges("tool", lambda state: "again" if state["status"] == "running" else "end",
                                {"again": "model", "end": END})
    return graph.compile()


def initial_weather_state(question):
    return {"messages": [{"role": "system", "content": SYSTEM_PROMPT},
                         {"role": "user", "content": question}],
            "requests": 0, "tool_calls": 0, "status": "running", "answer": None}
