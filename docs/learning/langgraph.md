# 第 10 章 · LangGraph：用状态与边组织执行

[章节目录](../../README.md#章节目录) · [上一章：评估](evaluation.md) · [下一章：MCP](mcp.md)

**本章目标：** 将问答与工具循环映射为状态、节点和边，并通过进程内快照观察图状态。

**配套示例：** [三步问答与天气循环](../../examples/langgraph_workflow.py) · **核心实现：** [图定义与状态更新](../../src/agent_learning/integrations/langgraph_workflow.py)

本章以 [Hello-Agents 第六章 §6.5.1–6.5.3](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter6/第六章%20框架开发实践.md) 为主线：先做“理解、搜索、回答”三步图，再把天气循环映射为节点与条件边。三步图使用本地教学摘要，便于跟踪查询、证据和答案；随后通过进程内快照观察图状态。第七章的分层思路可结合 [源码阅读练习](../practice/source-reading.md) 选读。

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

图的上半部分表示本章的状态与节点；下半部分的工具通信将在下一章展开。

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

把一次执行展开，会更容易看清“状态在变化”是什么意思。下面是默认问题的字段变化示意；省略了摘要正文，不是完整日志：

| 执行位置 | 新增或更新的字段 | 仍然保留的内容 |
| --- | --- | --- |
| 输入图时 | question、空 trace | 原问题 |
| understand 后 | query、`["understand"]` | question |
| search 后 | notes 包含 N02、增加 search 轨迹 | question、query |
| answer 后 | answer、增加 answer 轨迹 | 原问题、检索词、检索证据 |

`search` 不需要重复返回原问题。图会把它返回的字段更新合入已有状态；未返回的字段继续保留。因此节点既不需要复制整个字典，也不能假定返回值已经包含所有状态。

例如搜索节点只返回自己的更新，不改写其他字段：

```python
def search(state):
    notes = search_notes(state["query"])
    return {"notes": notes, "trace": [*state["trace"], "search"]}
```

这里每次显式构造完整的 `trace` 新列表。本例没有设置列表追加 reducer，因此节点返回某字段时，使用的是替换语义。如果只返回 `["search"]`，先前的 `understand` 记录就会丢失。不同项目也可用 reducer 表达合并规则，但不能混用两种思路而导致重复追加。

将三个节点依次连接：

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

## 10.3 从检索词到带引用的回答

下面节选检索词、资料与最终回答，观察状态如何沿三个节点传递。完整消息见 [运行记录](../runs/2026-11-19/langgraph-checkpoint.md)。

```text
节点：understand -> search -> answer
检索词：Action 由 Agent 产生，Observation 由 Environment 产生。
资料：N02
回答：根据资料 [N02]：

- **Action** 由**模型**产生，它表达模型希望执行的操作；
- **Observation** 由**程序（或工具调用系统）** 产生，即程序解析请求、调用对应工具后，将实际结果组织为 Observation，供下一次模型决策使用。

注意：打印工具结果 ≠ 将结果作为 Observation 发送给模型，Observation 需被显式构造并传回模型 [N02]。
进程内快照：trace=['understand', 'search', 'answer']；待执行节点=()
```

understand 的提示要求“只输出检索词”，模型却写了一句答案。程序没有检查查询质量，直接把整句作为 query。标签检索仍因 `Action`、`Observation` 命中 N02，于是流程继续。这里需要分别检查两个结果：查询是否适合检索，以及检索是否找到相关资料。命中了资料，并不说明查询改写已经合格。

answer 的第二次请求包含原问题和 N02 全文，最终把 Observation 解释为程序组织的工具结果。与第一次回复相比，这个回答多了调用工具、整理结果和回传模型的具体过程。阅读时应顺着传入的证据解释答案，而不是根据节点名推断它已经完成了“理解”。

模型参与时，understand 和有资料的 answer 通过 `ask_model` 生成内容；搜索由 Python 执行。无资料时，answer 直接说明资料不足。有命中也可能答不了问题：解释性回答必须引用本次编号；若只说明缺口，可用“资料不足：”开头且不附引用。任何未知编号都会使流程停止，缺口说明也不能绕过这一检查。编号校验只解决引用范围，结论是否受到资料支持仍需检查。

### 三个节点为什么通常只有两次模型请求

understand 用模型把问题整理为检索词；search 只是 Python 本地查找；answer 将原问题与查到的摘要交给模型。节点数、工具次数、模型请求数是三种计数，不能从图上数三个方框就说花了三次 API 调用。

命中资料后，回答节点构造的用户消息是：

```python
answer_input = {
    "role": "user",
    "content": f'问题：{state["question"]}\n资料：\n{format_results(state["notes"])}',
}
```

模型看到的是这条消息和该节点的系统要求。它不会自动读取 `trace`、上一次完整回复或 checkpoint；哪些状态进入请求，仍由 Python 构造。这里保留原问题，是为了防止回答阶段只围绕简短检索词作答而丢失用户要求。

三步图也是一个固定工作流：边规定 understand 后一定搜索，搜索后一定回答；模型可以改变检索词，却不能自己跳到另一个节点。下一节的条件循环才由模型输出与程序状态共同决定是否继续。两者都可以由 LangGraph 表达，不必把所有图都称作自主规划。

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

下面节选两次工具请求和最终回答，完整消息见 [运行记录](../runs/2026-11-19/langgraph-loop.md)。

```text
Action: get_weather(city="北京")
Action: get_weather(city="上海")
Action: Finish[上海更暖和（22℃ vs 北京12℃），以上为模拟天气数据。]
```

程序最终输出：

```text
状态：finished；模型决策节点 3 次；工具执行 2 次。
回答：上海更暖和（22℃ vs 北京12℃），以上为模拟天气数据。
```

两次查询分别得到北京和上海的模拟天气。第三次请求的 messages 含有这两条 Observation，模型据此比较温度并输出 Finish。因此，这段轨迹中模型请求 3 次，工具执行 2 次。

将上限改为 2 后，程序在两次工具执行后返回 `step_limit`，不再进入第三次模型节点。预算测试用固定回复检查这一停止条件。

这张图迁移天气循环的决策、工具回传与停止条件。基础研究助手的引用纠错，以及天气入口的预算提示和规则摘要，还需要各自确定状态字段与执行位置，再接入图中。

读条件边时可以做一个三步判断：先看 `model` 有没有识别到有效 Finish；没有则看 `tool` 是否把执行结果追加进 messages；最后看本轮 `requests` 是否已到上限。模型决定提出什么请求，程序决定是否执行、如何反馈以及何时停止。把循环改写成图，并没有转移这些责任。

## 10.5 checkpoint：保存图状态的快照

普通 Python 字典保存在当前调用中。给图配置 checkpointer 后，框架可以按执行进度记录状态。本节把 `InMemorySaver` 接在三步问答图；天气循环图尚未配置检查点，因此 `--loop` 与 `--checkpoint` 不能组合使用：

```python
checkpointer = InMemorySaver()
app = build_question_graph(checkpointer=checkpointer)
config = {"configurable": {"thread_id": "learning-demo"}}
app.invoke({"question": "Action Observation", "trace": []}, config)
snapshot = app.get_state(config)
```

三步图结束后，同一个进程读出的快照为：

```text
进程内快照：trace=['understand', 'search', 'answer']；待执行节点=()
```

`thread_id` 标识一条图执行线程；测试也验证了两个线程的问题、答案没有混在一起。`next=()` 表示此快照没有待执行节点。保存快照不代表模型回答已经正确。

可以将 checkpoint 想成“框架保存的一份执行记录”。它和模型消息历史解决的问题不同：前者供程序读取图状态，后者是发给模型的输入。即使快照里存着 notes，如果回答节点没有把 notes 放入请求，模型也不能据此作答。这正是第 5 章“本地有数据”和“本轮发送了数据”的区别。

`InMemorySaver` 将快照保存在内存，进程结束后即丢失。需要跨进程续跑时，应选择持久化存储，并检查恢复位置和已完成操作是否会重复执行，见 [官方 Persistence 文档](https://docs.langchain.com/oss/python/langgraph/persistence)。本例先练习快照读取与线程隔离。

## 10.6 运行、比较与自测

安装可选组件后，可以运行问答图、查看快照或观察循环的预算边界：

```bash
python -m pip install -e ".[graph]"
python -m examples.langgraph_workflow
python -m examples.langgraph_workflow --checkpoint
python -m examples.langgraph_workflow --loop
python -m examples.langgraph_workflow --loop --max-steps 2
```

默认模式不需要密钥：问答图摘录本地资料，天气图使用预设回复。添加 `--live` 后调用配置的模型并产生 API 用量，例如 `python -m examples.langgraph_workflow --live`。最后一条命令预期退出码为 1，表示预算耗尽、任务未完成。

| 自测任务 | 参考答案或验收点 |
| --- | --- |
| 把问题改成资料库没有的词 | notes 为空，answer 说明资料不足；不能自动补写未知事实 |
| 为什么 trace 需要保留之前的元素？ | 本例字段按返回值替换，没有设置追加 reducer |
| 上限为 2，为何不能靠图自动多生成一次总结？ | 请求预算是业务约束，不能通过框架暗中越过 |
| 两个线程使用同一个 thread_id 会怎样？ | 可能混用同一线程记录，应按任务明确分配标识 |
| 是否只要写成图就更适合小脚本？ | 还要权衡分支复杂度、状态可观察性和新增依赖；简单流程原生函数可能更易读 |

建议每次只改一个条件：先在 `answer` 调用前查看消息，确认有 N02 和原问题；再把查询改成没有命中的词，预测 answer 会不会请求模型。参考答案是不会：无资料分支直接写入“资料不足”。图仍经过 answer 节点，但这个节点不发起请求。对照节点轨迹和请求记录，可以看清两种计数的区别。

[集成测试](../../tests/test_langgraph_integration.py) 覆盖节点顺序、无资料分支、命中后仍缺资料、快照隔离、结果回传、预算停止和未知引用拒绝。读每个断言时，试着指出它对应哪一个状态字段或条件边。

---

以 Hello-Agents 第六章为主线、按本项目代码重新编排，框架 API 以官方文档和已安装版本为准。正文采用 [CC BY-NC-SA 4.0](../../LICENSES/CC-BY-NC-SA-4.0.txt)。
