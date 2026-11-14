<div align="center">

# Agent Learning Journey

**跟着 Hello-Agents 学原理，用小实验理解 Agent，再把能力逐步放进同一个项目。**

[知识导航](#知识导航) · [实践项目](docs/practice/research-agent.md) · [学习路线](docs/roadmap.md) · [复现指南](docs/getting-started.md)

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Status](https://img.shields.io/badge/状态-持续学习中-0F766E)
[![Tests](https://github.com/ldr0528/agent-learning-journey/actions/workflows/tests.yml/badge.svg)](https://github.com/ldr0528/agent-learning-journey/actions/workflows/tests.yml)

</div>

这是一个以 [Datawhale Hello-Agents](https://github.com/datawhalechina/hello-agents) 为主线的 **Agent 学习与实践仓库**。记录每个知识点解决什么问题、代码怎样实现、实验说明了什么，以及哪些问题还没有解决。

内容按知识主题组织。每篇笔记连接教材、解释、实验与代码；Research Agent 是承载这些知识的持续实践项目。目前已跑通模型调用、工具回传、有限循环和本地资料问答，后续继续学习状态与上下文、规划、反思及 LangGraph。

![学习脉络：从模型调用到带依据的回答，再进入状态、规划与框架](docs/assets/learning-path-zh.svg)

## 知识导航

按下表顺序阅读，也可以从自己有疑问的概念进入。**“已有实践”表示有代码与运行证据，是否理解还需要能解释实验结果。**

| 知识主题 | 要弄明白的问题 | 对应教材 | 当前进展 |
| --- | --- | --- | --- |
| [模型调用与消息](docs/learning/model-calls.md) | 模型收到了什么？提示词为什么会影响回答？ | 第四章 §4.1 | 已有基础实践 |
| [工具调用与结果回传](docs/learning/tool-feedback.md) | Action、工具函数、Observation 分别由谁产生？ | 第一章 §1.2、第四章 §4.2 | 已有基础实践 |
| [Agent Loop 与停止条件](docs/learning/agent-loop.md) | 为什么查两座城市可能需要三次模型请求？何时结束？ | 第四章 §4.2 | 已有简化实现与边界实验 |
| [检索、引用与资料不足](docs/learning/retrieval-and-citations.md) | 搜到资料、附上编号，就代表回答有依据吗？ | 第四章工具循环的项目扩展 | 已有最小实验；系统 RAG 待学 |

教材概念、教学简化和项目扩展在笔记中分别说明。当前使用文字 Action 协议与三条本地摘要，尚未使用原生 Function Calling 或向量检索。

## 从实验中得到的理解

| 实验现象 | 可以得到的结论 |
| --- | --- |
| 模型输出 `Action: get_weather(...)` | 它提出了行动请求；实际调用函数需要程序执行。 |
| 工具结果既打印到终端，又被追加到 `messages` | 让下一次模型请求看到结果的是消息回传。 |
| 北京、上海各查一次，再输出比较结论 | 一条已运行的轨迹是 **3 次模型请求、2 次工具执行**；Finish 也来自一次模型请求。 |
| 把同一任务的上限改为 2，查完两地仍报告未完成 | 拿到数据与形成被程序接受的最终答复是两个步骤；上限控制预算。 |
| 当前摘要无法回答 checkpoint 的作用 | 应说明资料不足；这不能证明 Hello-Agents 教材没有相关内容。 |
| 回答带有本次返回的资料编号 | 编号可追溯只是第一步，还要核对资料是否支持结论。 |

这些结论来自本项目的具体实现和实验。模型输出可能变化，少量样例与离线测试都不代表通用可靠率。

## 用同一个项目串起知识

**Research Agent：依据本地 Hello-Agents 教学摘要回答问题，并列出引用来源。**

它把已学机制连成一条可观察的流程：模型选择检索词 → Python 检索 → 资料回传 → 模型作答 → 程序检查引用与停止条件。资料不足时可以说明不足，预算耗尽时报告未完成。

| 想看什么 | 阅读入口 |
| --- | --- |
| 每增加一种能力，解决了什么问题 | [Research Agent 的能力演进](docs/practice/research-agent.md) |
| 模型、工具和程序怎样配合 | [架构与中文流程图](docs/architecture.md) |
| 怎样判断“跑出来了”是否符合预期 | [固定问题与评估标准](docs/evaluation.md) |
| 自己运行、修改并观察 | [复现指南](docs/getting-started.md) · [分层实验](examples/README.md) |

## 当前学到哪里

已完成基础实践的是模型接入与教学简化版 ReAct 循环。**Hello-Agents 第四章还没有整体学完**：§4.3 Plan-and-Solve 与 §4.4 Reflection 尚待学习和实现。

下一步先从当前 `messages` 和程序计数出发，补状态与上下文的基础概念，再回到规划与反思。之后学习检索与评估，进入第六章 §6.5 LangGraph。第五章低代码平台本轮跳过；完整教材映射、范围与验收问题见 [学习路线](docs/roadmap.md)。

## 怎样使用这个仓库

- **只读原理**：从知识导航进入，每篇按“问题 → 机制 → 实验 → 结论与边界”阅读。
- **跟着动手**：完成 [环境配置](docs/getting-started.md)，先预测实验结果，再运行、解释，最后只改变一个条件作对照。
- **读实现**：从 [独立示例](examples/README.md) 进入 [循环源码](src/agent_learning/loop.py) 和 [离线测试](tests/test_agent_loop.py)。测试通过不代替对概念的理解。

欢迎补充能解释清楚一个知识点的小实验，参见 [贡献说明](CONTRIBUTING.md)。

## 材料与许可

主要学习材料为 [Hello-Agents](https://github.com/datawhalechina/hello-agents)。教材衍生的学习笔记与本地教学摘要保留出处，采用 **CC BY-NC-SA 4.0**；笔记是教学转述与项目实验整理，非教材原文。

原创代码、工程说明与原创中文图采用 [MIT License](LICENSE)。详细来源和许可范围见 [NOTICE.md](NOTICE.md)。
