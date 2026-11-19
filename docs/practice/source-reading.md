# 沿一次请求追踪控制与数据

[章节目录](../../README.md#章节目录) · [LangGraph](../learning/langgraph.md) · [实现架构](../architecture.md)

本练习结合 [Hello-Agents 第七章](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter7/第七章%20构建你的Agent框架.md) 的分层思路，沿一次请求追踪“谁调用谁、数据在哪里改变、错误从哪里返回”。先读懂已有函数怎样协作，再考虑怎样划分自己的模块。

## 先选一条可观察的路径

以第 4 章的问题“Agent Loop 为什么要有最大步数？”为例：模型请求本地检索，程序返回 N01、N03，下一次模型请求用 N03 回答。沿这条路径阅读，可以将每个函数与一项具体工作对应起来。

| 顺序 | 本项目入口 | 要观察的数据 |
| --- | --- | --- |
| 1 | [cli.main](../../src/agent_learning/cli.py) | question、max_steps、provider |
| 2 | [run_research](../../src/agent_learning/agents/research.py) | 当前任务的 queried、retrieved、searches |
| 3 | [run_agent](../../src/agent_learning/loop.py) | messages、request_messages、step |
| 4 | [ask_model](../../src/agent_learning/llm.py) | 实际发给 SDK 的消息列表与返回文字 |
| 5 | run_research 内部 execute_search | Action 解析得到的 query |
| 6 | [search_notes / format_results](../../src/agent_learning/tools/notes.py) | 文件记录、命中标签、资料编号与来源 |
| 7 | run_agent 下一轮 | 新增 assistant Action 和 user Observation |
| 8 | validate_answer 与来源输出 | 引用是否来自本任务，来源链接来自哪里 |

## 把控制流和数据流分别说清楚

控制流回答“下一步执行哪个函数”。数据流回答“下一个函数拿到哪些值”。二者都看懂，才能定位“工具执行了，但模型没收到结果”这类问题。

```text
问题 → CLI → run_research → run_agent → ask_model
                                      ↓ Action
                          execute_search → search_notes
                                      ↓ 格式化结果
                              messages 追加 Observation
                                      ↓
                                下一次 ask_model
```

`execute_search` 是传给循环的函数。循环不需要了解文件内容和引用规则；研究助手通过这个函数和 `validate_answer` 提供任务逻辑。这个分工对应教材中模型层、Agent 层、工具层的职责划分：一层处理请求，一层组织任务，一层提供数据。

## 三个具体阅读任务

**任务一：找出模型真正收到的变量。** 在 `run_agent` 中定位 `ask_model` 的参数。当前传入 `request_messages`，它可能是完整历史，也可能先经过整理并附加预算。只读 `messages` 的构造而忽略调用参数，会漏掉最终输入。

**任务二：解释工具为什么不在第一次模型调用内部执行。** `ask_model` 返回的是文字；循环返回到 Python 后才调用工具执行函数。天气函数或者摘要检索的结果再进入消息列表，等待下一次请求。这里没有 API 原生 tool 消息，也没有让模型直接执行 Python。

**任务三：找出两种不同的停止。** 有效 Finish 通过校验后返回 `finished`；请求耗尽则返回 `step_limit` 和空答案。查到资料、打印正确文字或者执行完最后一个工具，都不能替代最终停止条件。

## 看完原生实现，再定位适配层

| 实现 | 应读的调用链 | 保持不变的业务事实 |
| --- | --- | --- |
| 原生天气循环 | weather.run_weather → loop.run_agent → execute_action | 两地工具结果必须回传；预算统计模型请求 |
| LangGraph 天气图 | build_weather_graph → model/tool 节点 → execute_action | 状态和条件边表达同样的停止条件 |
| MCP 协议基线 | run_mcp_demo → ClientSession → 子进程服务 → get_weather/search_notes | 工具结果仍是模拟天气或本地摘要 |
| MCP 模型桥接 | run_mcp_agent → run_model_tool_loop → 模型 tool_calls → ClientSession.call_tool | 模型只提出请求，宿主执行并回传 role=tool |

框架或协议只改变了部分组织方式。阅读时先找业务函数被保留下来的位置，再看新增状态、路由、传输和异常处理。

## 对照阅读：同样的工具结果经过哪两条边界

打开 [MCP 模型桥接代码](../../src/agent_learning/integrations/mcp_agent.py)，沿 `run_mcp_agent` 进入 `run_model_tool_loop`。这次不要按文件从头读到尾，而是追踪一个北京天气结果：

```text
MCP list_tools → 工具定义 → 模型请求的 tools 参数
                                 ↓ tool_calls（名字、参数、调用编号）
                宿主检查名字、解析 JSON
                                 ↓
               MCP call_tool → 服务端 → get_weather
                                 ↓ 实际工具结果
                messages 追加 assistant 与 tool
                                 ↓
                    下一次模型 API 请求 → 最终文本
```

第一条边界是宿主与模型 API；第二条是 MCP 客户端与服务端。模型返回 `tool_calls[].id`，宿主将同一个值写进 tool 消息的 `tool_call_id`，由此关联请求与反馈；MCP 的请求编号则由 SDK 管理。原生 tool calling 并不意味着模型绕过了宿主直接执行函数。

打开 [运行记录](../runs/2026-11-19/mcp.md) 和 [请求 JSON](../runs/2026-11-19/mcp.json)，找到 `calls[2].request.messages`：最后一条 tool 消息保存上海 22℃，较早的 tool 消息保存北京 12℃。对照第三次响应，检查比较结论是否使用了这些值，以及是否保留“模拟数据”的限定。这份答案比较正确，但漏掉了数据性质说明。

阅读时给以下五处各写一句注释：

| 位置 | 应说明的原因 |
| --- | --- |
| `discovered.tools` → `model_tool_schema(tools)` | 工具说明来自本次发现，参数定义不另写一份 |
| `request_model(messages, tools)` | 这是 API 边界；日志与 token 用量应从这里的实际请求获取 |
| `name not in known` | 模型可能请求不存在的工具，未知名字不能直接派发 |
| `role="tool"` 与 `tool_call_id` | 结果需要进入下一轮输入，并关联原来的请求 |
| `range(1, max_calls + 1)` | 限制模型调用次数，最后查到工具也不能暗中增加一次总结 |

`asyncio.to_thread` 在这里承接同步模型 HTTP 调用，让事件循环能继续处理 MCP 子进程的数据流。它没有让模型和工具凭空同时完成；程序仍等待模型回复后才知道调用参数。

再回到 [LangGraph 图实现](../../src/agent_learning/integrations/langgraph_workflow.py)，找到 `answer` 构造消息的位置。图状态中的 notes 与 MCP 客户端内存中的结果一样，必须被明确放进请求，才成为模型可见的依据。checkpoint 保存状态不能替代这一步。

再看 [三步图记录](../runs/2026-11-19/langgraph-checkpoint.md)：understand 返回一句回答而不是关键词，标签检索仍命中 N02。沿代码可找到原因——query 没有格式质量检查；沿第二次请求则能看到 N02 已进入 answer 的输入。两项观察分别定位查询改写和证据回传，便于确定下一步该改哪里。

## 用测试验证阅读结论

不需要 API Key 的检查：

```bash
python -m unittest discover -s tests -p test_agent_loop.py -v
python -m unittest discover -s tests -p test_research_agent.py -v
```

测试通过固定回复截获每次请求，检查 Observation 是否进入下一轮、引用是否来自当前任务、重复查询是否再次执行工具。读一个测试时先找输入轨迹，再找断言，说明这个断言能检查哪一种错误。

安装对应可选依赖后，继续检查图的状态更新与 MCP 消息流：

```bash
python -m unittest discover -s tests -p test_langgraph_integration.py -v
python -m unittest discover -s tests -p test_mcp_integration.py -v
python -m unittest discover -s tests -p test_mcp_agent.py -v
```

## 练习与参考答案

1. **删掉打印 Observation 的语句，会让模型失去结果吗？** 不会，只要追加消息和下一次调用仍然存在。打印用于观察。
2. **保留打印，但删掉消息追加，会怎样？** 工具结果留在终端，后续模型请求缺少它；这才改变数据流。
3. **为什么来源链接由程序读取记录输出？** 当前代码不依赖模型自行写出 URL，能维持编号和本地来源记录的对应关系。但内容是否真正支持答案仍需检查。
4. **换成 LangGraph 后能删掉业务预算吗？** 不能；图运行限制和模型请求预算的单位不同。
5. **MCP 发现工具时是否已经调用模型？** 没有；客户端发现是协议操作。默认例子就此验证工具；`--live` 才在发现之后发起模型请求。
6. **工具参数格式正确，就能认定名字存在吗？** 不能；宿主先对照本次发现的名称列表，再解析参数并调用服务端。
7. **看到 trace 有三个节点，就能说 API 调用了三次吗？** 不能；节点也可能只做本地检索或资料不足处理，应定位实际模型请求。

验收时，任选一条路径，用自己的话标出“模型调用、程序控制、工具执行、结果回传、停止检查”五个位置，并给出实际文件或函数名。能够定位到源码，比背诵框架术语更能说明已经理解。

---

本练习以 Hello-Agents 第七章为阅读线索，路径、代码和问题均根据本项目重新设计。
