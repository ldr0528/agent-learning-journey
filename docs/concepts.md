# 概念对照与阅读索引

[手册目录](../README.md) · [课程地图](course-map.md) · [真实实验](runs/README.md)

读到新术语时，先问它属于“模型输出”“程序保存的数据”还是“外部执行”。这三个位置分清楚，就能沿代码找到它在哪一轮发挥作用。

## 常用术语在本项目中的位置

| 概念 | 在本项目中指什么 | 容易混淆的地方 | 回到正文 |
| --- | --- | --- | --- |
| Message / 消息 | 一条带role与内容的模型输入或输出 | 终端打印的文字不一定在messages里 | [01](learning/model-calls.md) |
| Action / 行动请求 | 早期案例中，模型按提示生成的文本指令 | 写出函数名不会自动运行函数 | [02](learning/tool-feedback.md) |
| Observation / 观察结果 | 程序把实际工具结果组织成反馈 | 模型看不到未被加入下一次请求的结果 | [02](learning/tool-feedback.md) |
| Agent Loop | 请求模型、处理行动、回传结果、检查停止条件 | 一轮模型请求不等于一次工具执行 | [03](learning/agent-loop.md) |
| State / 状态 | 程序保存的问题、计划、历史、计数等数据 | 存在变量中不代表已经发给模型 | [05](learning/state-and-context.md) |
| Context / 上下文 | 本轮实际发给模型的信息 | 原始历史、摘要和剩余预算需由程序选择并组织 | [05](learning/state-and-context.md) |
| Plan-and-Solve | 一次规划后，按步骤组织执行请求 | 计划合格不代表每一步计算正确 | [06](learning/planning.md) |
| Reflection | 对草稿评审，必要时修订并复审 | 模型自评accept不等于外部验证通过 | [07](learning/reflection.md) |
| RAG | 先检索资料，再把选中证据交给生成过程 | 关键词相关不等于资料能回答问题 | [08](learning/rag.md) |
| Evaluation / 评估 | 对固定题按明确规则测量结果 | 检索召回、引用合法和答案正确是不同指标 | [09](learning/evaluation.md) |
| Checkpoint / 检查点 | 图执行期间保存的一份状态快照 | 本课程的进程内保存不能跨进程重启恢复 | [10](learning/langgraph.md) |
| MCP | 客户端发现和调用工具的通信协议 | MCP本身不负责让模型理解或选择工具 | [11](learning/mcp.md) |

## 文本 Action 与原生工具调用有何关系

前几章让模型返回 `Action: get_weather(...)`，Python 解析字符串、执行函数，并把 Observation 加到下一轮消息。第11章改用 API 的 `tool_calls` 字段，程序根据结构化的工具名和JSON参数调用 MCP，再用 `role=tool` 回传结果。

两种方式共同需要“实际执行”和“结果回传”。区别在于模型接口如何表达请求，以及工具是在当前进程执行还是通过MCP会话执行。`tool_call_id` 用于匹配一项模型工具请求与它的结果，不是MCP协议请求编号。完整过程见 [真实 MCP 时序图](learning/mcp.md)。

## 遇到疑惑时怎样定位

- **回答像是猜的**：先看真实记录中的 `request.messages`，确认工具结果或证据实际进入了模型。
- **程序显示完成但答案不对**：查看完成状态的定义，再按题目约束检查内容；模型自评与程序格式检查都不能替代这一步。
- **资料查到了却答不出来**：核对检索结果是否进入了证据预算，再看材料是否支持问题需要的具体事实。
- **图能运行是否说明Agent更强了**：先比较相同问题、输入和预算下的结果。框架首先改变的是状态与控制流的表达。

这些解释对应本项目的教学实现。主要概念来源与拓展位置见 [Hello-Agents 教材映射](roadmap.md) 和 [参考资料](references.md)。
