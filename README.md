<div align="center">

# Agent 学习手册

### Agent Learning Journey

**用一套可阅读、可运行、可核验的中文材料，学会构建单体智能体。**

[开始阅读](docs/learning/model-calls.md) · [课程地图](docs/course-map.md) · [真实实验](docs/runs/README.md) · [贯穿项目](docs/practice/research-agent.md) · [环境配置](docs/getting-started.md)

</div>

以 [Datawhale Hello-Agents](https://github.com/datawhalechina/hello-agents) 为主要教材，按我们自己的课程路径重新编排。全书围绕两个案例展开：模拟天气说明模型、工具与循环；Research Agent 串起资料检索、来源引用、评估与工具接入。

**正文直接给出解释、关键代码、原创中文图、输出和分析。** 可以先阅读，再选择动手；安装命令集中在配套文档。适合能阅读基础 Python、希望理解 Agent 如何工作的学习者。

![课程四部分与贯穿案例](docs/assets/learning-path-zh.svg)

## 章节目录

章号属于本手册，不对应 Hello-Agents 原章号。每章附教材定位、实验、边界和练习；完整目标与验收见 [课程地图](docs/course-map.md)。

| 部分 | 章节 | 学完要能解释的问题 |
| --- | --- | --- |
| 模型、工具与循环 | [01 模型调用与消息](docs/learning/model-calls.md) | 哪些信息实际进入了模型请求？ |
| | [02 工具调用与结果回传](docs/learning/tool-feedback.md) | Action、函数执行、Observation 分别由谁产生？ |
| | [03 Agent Loop 与停止条件](docs/learning/agent-loop.md) | 模型请求数为什么不等于工具执行数？ |
| | [04 检索、引用与资料不足](docs/learning/retrieval-and-citations.md) | 查到资料、引用合法、结论有依据有何区别？ |
| 上下文与任务组织 | [05 状态与上下文](docs/learning/state-and-context.md) | 怎样保留证据、更新预算、整理较早历史？ |
| | [06 Plan-and-Solve](docs/learning/planning.md) | 怎样将计划变成逐步执行，并回传结果？ |
| | [07 Reflection](docs/learning/reflection.md) | 怎样评审和修订，又如何限制迭代？ |
| 检索与质量 | [08 RAG 与检索改进](docs/learning/rag.md) | 怎样从文档构造可追溯的回答证据？ |
| | [09 Agent 评估](docs/learning/evaluation.md) | 怎样分别测量检索、引用与回答质量？ |
| 框架与协议 | [10 LangGraph 与调用链](docs/learning/langgraph.md) | 如何把节点、状态和分支映射到真实运行？ |
| | [11 MCP 入门](docs/learning/mcp.md) | 客户端怎样发现并调用另一个进程的工具？ |

## 如何使用这套材料

第一次阅读按 01–11 顺序。已熟悉模型调用的读者可以从第 03 章开始，用 [阶段验收](docs/course-map.md#阶段验收) 检查基础。每章的关键代码与输出已在正文呈现，完整实现位于 `src/agent_learning`，独立入口位于 `examples`。

| 你想做什么 | 入口 |
| --- | --- |
| 按课程循序学习 | [课程地图与练习](docs/course-map.md) |
| 看完整研究助手怎样组织 | [贯穿项目与验收](docs/practice/research-agent.md) |
| 先运行无需密钥的例子 | [配套示例索引](examples/README.md) |
| 使用千问或 OpenAI 运行真实模型 | [配置说明](docs/getting-started.md) |
| 读已有代码如何协作 | [分层架构](docs/architecture.md) · [调用链阅读](docs/practice/source-reading.md) |
| 区分真实结果和教学演示 | [结果证据与学习进度](docs/evidence.md) |
| 对照每次模型实际收到的内容 | [真实 API 实验集](docs/runs/README.md) |
| 查术语与容易混淆的概念 | [概念对照](docs/concepts.md) · [参考资料与阅读设计](docs/references.md) |

LangGraph 与 MCP 作为可选安装项，基础章节无需这些库。所有离线演示都会明确说明数据或模型回复是否预设；真实工具、框架和协议运行也会注明边界。

## 从真实输出读懂一个机制

在 MCP 章节，千问实际提出查询北京、上海的工具请求；Python通过MCP执行工具，把12℃与22℃回传；第三次模型请求得出上海更暖和。模型并没有直接连接工具服务端，中间的应用完成了发现、映射与结果回传。

![千问模型通过Python应用调用MCP工具的实际时序](docs/assets/mcp-model-roundtrip-zh.svg)

完整 [输入与输出](docs/runs/2026-11-19/mcp.md) 保留模型原话：结尾漏写了提示要求的“模拟数据”。正文会同时解释正确的比较和遗漏的约束。这样的分析也用于规划、Reflection、RAG和LangGraph，让读者看到程序实际完成了什么，以及还需要检查什么。

## 材料完成与个人学习进度

第 01–05 章保留学习者提供的千问结果；第 06–11 章以新采集的真实API输出为主例，附请求记录、用量与结果判读。固定回复保留用于无需密钥的分支练习和自动测试。教材准备与个人掌握程度分别记录，个人学习继续从规划与执行阶段推进。具体样本与边界见 [结果说明](docs/evidence.md)。

本轮范围聚焦单体 Agent：跳过低代码平台，第六章框架只选 LangGraph；MCP 只做本地工具通信。多 Agent、A2A、ANP、训练与长期记忆不进入本课程验收。教材映射和边界见 [学习计划](docs/roadmap.md)。

## 项目组织

```text
docs/learning/          11 章教材：解释、代码、图、结果与练习
docs/practice/          贯穿项目与源码调用链
docs/assets/            原创中文 SVG
src/agent_learning/     模型接入、循环、任务、检索与集成
examples/               每章可独立运行的入口
tests/                  不调用付费模型的逻辑与集成检查
scripts/                文档、示例与图示维护工具
```

## 参考、许可与贡献

主要教材为 [Hello-Agents](https://github.com/datawhalechina/hello-agents)。正文按本项目案例重新组织，明确注明转述、教学简化和工程扩展；不复制第三方图像或标识。

正文和教材衍生资料采用 **CC BY-NC-SA 4.0**；原创实现、测试与原创图示采用 [MIT License](LICENSE)。混合许可的准确范围见 [NOTICE](NOTICE.md)。欢迎按 [贡献说明](CONTRIBUTING.md) 补充经过核对的讲解、案例与结果。
