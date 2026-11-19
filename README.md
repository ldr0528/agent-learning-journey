<div align="center">

# Agent 学习手册

### Agent Learning Journey

**从一次模型请求出发，理解 Agent 的工作过程，逐步构建有来源的资料问答。**

[开始阅读](docs/learning/model-calls.md) · [课程地图](docs/course-map.md) · [项目任务书](docs/practice/research-agent.md) · [迁移练习](docs/practice/transfer-exercises.md) · [环境配置](docs/getting-started.md)

</div>

Agent 学习手册是一套以 [Datawhale Hello-Agents](https://github.com/datawhalechina/hello-agents) 为主要教材的中文学习资料。围绕“模型看到了什么、程序执行了什么、结论依据是什么”这三个问题，连接原理、关键代码、图解、输出和练习。

模拟天气用于看清工具与循环，本地资料问答用于练习检索、引用和评估；规划、反思、LangGraph 与 MCP 各有独立示例。当前研究助手包含基础循环与 RAG 两条实现，多轮研究与报告修订是后续建设重点。

## 适合谁，学完能做什么

适合能阅读 Python 函数、列表、字典、循环和基础异常处理，想从调用模型走向理解 Agent 的学习者。无需预先掌握 Agent 框架；阅读正文无需配置 API，动手配置见 [环境说明](docs/getting-started.md)。

- **读懂机制：** 沿一次请求找到消息、工具结果与停止条件，解释为什么“终端打印了”不等于“模型收到了”。
- **修改实现：** 调整预算、上下文和检索条件，检查改变了哪些输入，以及失败发生在哪一层。
- **完成实践：** 按项目任务书提交带来源的回答与失败分析，用证据判断结论是否成立。

![四个学习阶段及对应成果](docs/assets/learning-path-zh.svg)

## 先看一个学习问题

“检索到了资料，模型就能回答吗？”在资料问答实验中，两个问题表现不同：

| 问题 | 检索与回答的关系 | 要学会的判断 |
| --- | --- | --- |
| RAG 为什么要保留来源与引用？ | 返回来源与引用的资料，生成带资料编号的结论 | 逐条检查引用是否支持结论，而不只看有没有编号 |
| RAG 服务每月收费多少钱？ | 返回 RAG 原理资料，仍说明缺少收费标准 | 主题相关不代表证据足以回答 |

这两条结果来自 [项目案例](docs/practice/research-agent.md)。正文给出证据、回答节选和分析，再通过 [迁移练习](docs/practice/transfer-exercises.md) 把同样的判断应用到新的报告。阅读顺序是：**问题 → 机制 → 代码与输出 → 解释 → 修改条件或完成练习**。

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
| 框架与协议 | [10 LangGraph 与调用链](docs/learning/langgraph.md) | 节点怎样更新状态、决定下一步？ |
| | [11 MCP 入门](docs/learning/mcp.md) | 客户端怎样发现并调用另一个进程的工具？ |

## 如何使用这套材料

第一次阅读按 01–11 顺序。已有工具调用经验，可以先完成 [阶段 A 自查](docs/course-map.md#阶段验收)，再进入上下文与任务组织。完整实现与独立入口用于对照正文和复现实验。

| 你想做什么 | 入口 |
| --- | --- |
| 按课程循序学习 | [课程地图与练习](docs/course-map.md) |
| 明确项目要解决什么、交付什么 | [项目任务书与验收](docs/practice/research-agent.md) |
| 检查能否把概念用于新问题 | [研究计划与报告修订练习](docs/practice/transfer-exercises.md) |
| 先运行无需密钥的例子 | [配套示例索引](examples/README.md) |
| 配置模型服务 | [配置说明](docs/getting-started.md) |
| 读已有代码如何协作 | [分层架构](docs/architecture.md) · [调用链阅读](docs/practice/source-reading.md) |
| 查看实验条件与检查结果 | [实验说明](docs/evidence.md) |
| 对照每次模型收到的内容 | [请求与响应记录](docs/runs/README.md) |
| 查术语与容易混淆的概念 | [概念对照](docs/concepts.md) · [参考资料与阅读设计](docs/references.md) |

LangGraph 与 MCP 作为可选安装项，基础章节无需这些库。每个运行入口注明是否请求模型，固定输入练习可在没有 API Key 时使用。

## 当前范围与下一步

目前包含 11 章正文、基础循环、规划与反思练习、两条本地资料问答路径，以及 LangGraph 和 MCP 示例。核心机制可以逐项学习；综合研究任务仍需继续扩展。

| 已有基础 | 接下来要补强 |
| --- | --- |
| 小型例题解释规划、执行和评审 | 需要前序证据的研究任务，以及初稿到修订稿的对照 |
| 14 篇短教学摘要与词法检索 | 较长章节材料、多来源比较与信息缺口处理 |
| 检索开发题与引用结构检查 | 独立问题、逐条证据判定和失败类型分析 |
| 独立的图工作流与协议工具示例 | 将已验证的研究流程接入框架和协议 |

具体交付物与完成条件见 [建设路线](docs/roadmap.md#后续建设与完成条件)。课程聚焦单体 Agent，框架选 LangGraph，协议选本地 MCP；低代码平台、多 Agent、训练和长期记忆不在当前范围。

## 项目组织

```text
docs/learning/          11 章教材：解释、代码、图、结果与练习
docs/practice/          项目任务、迁移练习与源码调用链
docs/assets/            原创中文 SVG
src/agent_learning/     模型接入、循环、任务、检索与集成
examples/               每章可独立运行的入口
tests/                  不调用付费模型的逻辑与集成检查
scripts/                文档、示例与图示维护工具
```

## 参考、许可与贡献

主要教材为 [Hello-Agents](https://github.com/datawhalechina/hello-agents)。正文按本项目案例重新组织，明确注明转述、教学简化和工程扩展；不复制第三方图像或标识。

正文和教材衍生资料采用 **CC BY-NC-SA 4.0**；原创实现、测试与原创图示采用 [MIT License](LICENSE)。混合许可的准确范围见 [NOTICE](NOTICE.md)。欢迎按 [贡献说明](CONTRIBUTING.md) 补充经过核对的讲解、案例与结果。
