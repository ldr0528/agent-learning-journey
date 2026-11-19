# 第 10 章 · LangGraph 与调用链

[章节目录](../../README.md#章节目录) · [上一章：评估](evaluation.md) · [下一章：MCP](mcp.md)

本章以 [Hello-Agents 第六章 §6.5.1–6.5.3](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter6/第六章%20框架开发实践.md) 为主线：先做“理解、搜索、回答”三步图，再把已有天气循环映射为节点与条件边。三步图将教材中的外部搜索改成本地教学摘要；循环迁移和进程内快照是本项目扩展。第七章只沿实际调用链选读，见 [源码阅读练习](../practice/source-reading.md)。

## 10.1 图组织的是执行过程

之前的 `for` 循环已经完成了模型请求、工具执行和停止判断。引入 LangGraph 后，这些责任仍然存在，只是被显式表达为状态、节点和边。LangGraph 不替我们判断资料是否支持结论，也不自动把状态中的所有字段发送给模型。

| 图中的概念 | 本项目具体含义 | 容易混淆的地方 |
| --- | --- | --- |
| State | 问题、检索词、资料、答案、执行轨迹 | 程序状态不等于模型输入 |
| Node | 做一次明确工作的 Python 函数 | 节点可以完全不调用模型 |
| Edge | 下一步执行哪个节点 | 普通边固定跳转，条件边读取状态后选择 |
| compile | 将定义检查、组装成可运行图 | 不会在编译时完成问答 |
| invoke | 给图输入并运行 | 才会实际执行节点 |

![框架的执行组织与 MCP 的工具通信](../assets/framework-protocol-zh.svg)

本图是按项目实现原创绘制的。上半部分对应本章的状态与节点；协议部分将在下一章展开。

## 10.2 三步问答：每一步返回更新字段

[完整实现](../../src/agent_learning/integrations/langgraph_workflow.py) 定义了以下状态：

```python
class QuestionState(TypedDict, total=False):
    question: str
    query: str
    notes: list
    answer: str
    trace: list[str]
```

`TypedDict` 描述字典的字段形状，帮助阅读和类型检查；它不是问题内容正确性的校验器。`total=False` 允许字段随节点执行逐步补齐。

三个节点的分工如下：

| 节点 | 读取 | 写入 | 离线默认模式 |
| --- | --- | --- | --- |
| understand | question | query、trace | 清理问题两端空白，直接作为检索词 |
| search | query | notes、trace | 调用现有 `search_notes` 读取本地摘要 |
| answer | question、notes | answer、trace | 摘录命中内容并附上资料编号 |

例如搜索节点只返回自己的更新，不改写其他字段：

```python
def search(state):
    notes = search_notes(state["query"])
    return {"notes": notes, "trace": [*state["trace"], "search"]}
```

这里每次显式构造完整的 `trace` 新列表。本例没有设置列表追加 reducer，因此节点返回某字段时，使用的是替换语义。如果只返回 `["search"]`，先前的 `understand` 记录就会丢失。不同项目也可用 reducer 表达合并规则，但不能混用两种思路而导致重复追加。

图的连接来自实际代码：

```python
graph = StateGraph(QuestionState)
graph.add_node("understand", understand)
graph.add_node("search", search)
graph.add_node("answer", answer)
graph.add_edge(START, "understand")
graph.add_edge("understand", "search")
graph.add_edge("search", "answer")
graph.add_edge("answer", END)
app = graph.compile()
```

节点名是图中的标识，函数才执行工作。`START` 与 `END` 是流程入口和终点，不是模型角色。接口语义补充参考 [LangGraph Graph API 官方文档](https://docs.langchain.com/oss/python/langgraph/graph-api)。

## 10.3 已实际运行的三步图

在 Python 3.12、LangGraph 1.2.23 的隔离环境中，助教运行了真实 `StateGraph`。以下是离线输出，不是 Qwen 的回答：

```text
离线模式：真实 LangGraph 调度、本地工具；回答由确定性摘录或预设回复产生，不调用模型。
节点：understand -> search -> answer
检索词：Action 和 Observation 分别由谁产生？
资料：N02
回答：Action 表达模型希望执行的操作。程序解析请求并调用对应工具，把实际结果组织为 Observation，供下一次模型决策使用。打印工具结果不等于把结果发送给模型。 [N02]
```

从这段输出能确认三件事：图按指定顺序执行；检索真正读取本地 N02；资料内容经过状态传给回答节点。它不能证明真实模型改写查询或组织答案的质量。

增加 `--live` 后，understand 和有资料的 answer 节点通过现有 `ask_model` 调用已配置的模型。搜索仍由 Python 执行。无资料时直接说明资料不足；有资料时，程序要求回答引用本次返回的编号，未知编号或缺少引用会停止。编号合法仍不等于论据足以支持结论。

## 10.4 将有限循环迁移成条件图

同一模块提供第二个图，由 `model` 和 `tool` 两个节点组成：

```text
START → model ── 有效 Finish ──→ END
           │
           └─ 其他输出 → tool ── 尚有预算 ──→ model
                            └─ 预算耗尽 ──→ END
```

`model` 保存回复并增加 `requests`；`tool` 解析工具请求、保存 Observation，并增加成功执行的工具次数。节点更新列表时都创建新列表，便于检查上一轮状态。

| 原循环中的职责 | 图中的位置 |
| --- | --- |
| `ask_model` 或固定回复 | model 节点里的 `decide(messages)` |
| 识别有效 Finish | model 节点更新 status 和 answer |
| 工具执行、错误返回 | tool 节点调用既有 `execute_action` |
| 判断还有没有请求预算 | tool 后面的条件边读取 status |
| 保存问题与工具结果 | WeatherState.messages |

`max_steps` 仍然限制模型决策节点的次数。LangGraph 的 `recursion_limit` 是图执行层面的保护，不能直接当作模型请求预算：一次模型决策后可能还要执行工具节点。

使用预设的“北京查询、上海查询、Finish”回复序列运行真实图，实际输出为：

```text
状态：finished；模型决策节点 3 次；工具执行 2 次。
回答：上海更暖和（22℃ vs 北京12℃），数据为模拟天气。
```

这里实际模型 API 请求为 0，三次决策节点使用固定回复。将上限改为 2，结果为 `step_limit`，两次工具执行后没有有效答案；第三次模型节点不应发生。这与第 3 章的停止约定一致。

此迁移只包含核心天气循环，没有声称将研究助手的引用纠错、预算提示和摘要功能全部迁入图。能用状态和边表达某个流程，并不意味着应该马上迁移所有组件。

## 10.5 checkpoint：保存图状态的快照

普通 Python 字典保存在当前调用中。给图配置 checkpointer 后，框架可以按执行进度记录状态。我们用 `InMemorySaver` 做最小实验：

```python
checkpointer = InMemorySaver()
app = build_question_graph(checkpointer=checkpointer)
config = {"configurable": {"thread_id": "learning-demo"}}
app.invoke({"question": "Action Observation", "trace": []}, config)
snapshot = app.get_state(config)
```

助教实测输出：

```text
进程内快照：trace=['understand', 'search', 'answer']；待执行节点=()
```

`thread_id` 标识一条图执行线程；测试也验证了两个线程的问题、答案没有混在一起。`next=()` 表示此快照没有待执行节点。保存快照不代表模型回答已经正确。

这里的存储是内存，进程结束后不会保留。本例验证快照读取和线程隔离，没有实现数据库持久化、人工中断恢复或跨进程续跑。更完整的持久化能力应按 [官方 Persistence 文档](https://docs.langchain.com/oss/python/langgraph/persistence) 继续实验。

## 10.6 运行、比较与自测

安装可选组件后，下面命令默认均不调用模型：

```bash
python -m pip install -e ".[graph]"
python -m examples.langgraph_workflow
python -m examples.langgraph_workflow --checkpoint
python -m examples.langgraph_workflow --loop
python -m examples.langgraph_workflow --loop --max-steps 2
```

最后一条预期退出码为 1，含义是预算耗尽、任务未完成。真实模型模式显式使用 `--live`，会产生 API 用量，例如 `python -m examples.langgraph_workflow --live`。

| 自测任务 | 参考答案或验收点 |
| --- | --- |
| 把问题改成资料库没有的词 | notes 为空，answer 说明资料不足；不能自动补写未知事实 |
| 为什么 trace 需要保留之前的元素？ | 本例字段按返回值替换，没有设置追加 reducer |
| 上限为 2，为何不能靠图自动多生成一次总结？ | 请求预算是业务约束，不能通过框架暗中越过 |
| 两个线程使用同一个 thread_id 会怎样？ | 可能混用同一线程记录，应按任务明确分配标识 |
| 是否只要写成图就更适合小脚本？ | 还要权衡分支复杂度、状态可观察性和新增依赖；简单流程原生函数可能更易读 |

离线测试覆盖三节点顺序、无资料分支、快照隔离、天气工具结果回传、预算停止和未知引用拒绝。见 [集成测试](../../tests/test_langgraph_integration.py)。本章材料与代码已准备，不代表学习者已完成所有练习。

---

以 Hello-Agents 第六章为主线、按本项目代码重新编排，框架 API 以官方文档和已安装版本为准。正文采用 [CC BY-NC-SA 4.0](../../LICENSES/CC-BY-NC-SA-4.0.txt)。
