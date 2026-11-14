<div align="center">

# Agent 学习手册
### Agent Learning Journey

**从模型调用到智能体系统：原理、代码、运行结果与图解。**

[开始阅读](docs/learning/model-calls.md) · [章节目录](#章节目录) · [编排与学习计划](docs/roadmap.md) · [配套代码说明](docs/getting-started.md)

</div>

这是一套按我们自己的学习计划持续整理的 **Agent 学习资料库**，以 [Datawhale Hello-Agents](https://github.com/datawhalechina/hello-agents) 为主要参考。围绕已经写过的代码与已经发生的实验，把知识讲清楚，再逐步扩展到上下文、规划、检索和框架。

正文直接给出原理图、关键代码、已有运行结果及逐步解释。**不需要先配置环境或运行项目，就可以顺着章节学习。** 完整源码和运行命令作为配套，供希望进一步动手的读者使用。

![本手册的基础知识与后续学习路线](docs/assets/learning-path-zh.svg)

## 章节目录

以下是本手册自己的编排；章号不对应 Hello-Agents 的章号。参考教材的位置在每章中单独标注。

### 第一部分 · 模型、工具与智能体循环

这部分已有正文，按顺序阅读即可串起一条完整的信息流。

| 章节 | 正文讲解的内容 | 直接展示的案例 |
| --- | --- | --- |
| [第 1 章 · 模型调用与消息](docs/learning/model-calls.md) | 消息角色、请求与回复、提示对输出的影响 | Python 字典解释代码与已有英文回答 |
| [第 2 章 · 工具调用与结果回传](docs/learning/tool-feedback.md) | Action、函数执行、Observation、第二次请求 | 天气工具代码、消息变化图与广州无数据回答 |
| [第 3 章 · Agent Loop 与停止条件](docs/learning/agent-loop.md) | 多轮决策、Finish、请求预算和程序状态 | 北京与上海的三轮轨迹，以及两轮上限结果 |
| [第 4 章 · 检索、引用与资料不足](docs/learning/retrieval-and-citations.md) | 本地检索、资料回传、引用校验及证据边界 | 最大步数问题的两轮回答与 checkpoint 资料不足案例 |

### 第二部分 · 上下文、规划与反思

第 5 章已整理状态、上下文与预算对照的基础内容，其余内容随学习补充。

| 章节 | 核心问题 | 主要参考 |
| --- | --- | --- |
| [第 5 章 · 状态与上下文](docs/learning/state-and-context.md)（基础已整理） | 程序保存的信息怎样进入模型输入？预算提示与执行上限有什么区别？ | Hello-Agents 第九章选读 |
| 第 6 章 · Plan-and-Solve | 先生成计划，再执行，与逐轮决策有何差异？ | Hello-Agents 第四章 §4.3 |
| 第 7 章 · Reflection | 如何根据评审修订结果，又怎样限制修订次数？ | Hello-Agents 第四章 §4.4 |

### 第三部分 · 检索与评估

| 计划章节 | 核心问题 | 主要参考 |
| --- | --- | --- |
| 第 8 章 · RAG 与检索改进 | 资料增多后，怎样找到真正有用的内容？ | Hello-Agents 第八章 |
| 第 9 章 · Agent 评估 | 怎样分别判断检索、回答和执行流程的质量？ | Hello-Agents 第十二章 |

### 第四部分 · 框架与协议

| 计划章节 | 核心问题 | 主要参考 |
| --- | --- | --- |
| 第 10 章 · LangGraph 与调用链 | 如何用节点、边和状态表达已有流程？ | Hello-Agents 第六章 §6.5、第七章选读 |
| 第 11 章 · MCP 入门 | 工具接入协议在系统中解决了哪一层的问题？ | Hello-Agents 第十章选读 |

当前基础实践覆盖模型接入与教学简化版 ReAct。规划、反思与 LangGraph 尚待学习；本手册第 4 章的本地检索案例也不代表已经完成系统 RAG 学习。完整范围与教材映射见 [学习计划](docs/roadmap.md)。

## 正文怎样组织

每章从具体问题出发，依次呈现 **原理解释 → 中文图解 → 关键代码 → 运行结果 → 逐步分析 → 结论与边界**。问题后直接给出解释，不把核心知识留给读者运行后自行猜测。

代码片段注明来自哪段实现，以及是否为了讲解省略了外围代码。真实运行节选、确定性工具输出和机制示意分别标注；不会把新写的示意内容当作实际模型结果。文中天气始终是模拟数据。

## 贯穿案例与配套资料

模拟天气用来解释工具与循环，Research Agent 用来串联资料检索、结果回传和引用。随着学习推进，同一个案例会逐步补充状态管理、规划、评估与框架实现。

- [贯穿案例：Research Agent 的能力演进](docs/practice/research-agent.md)
- [附录：实现架构与组件职责](docs/architecture.md)
- [附录：固定问题与评估标准](docs/evaluation.md)
- [配套代码：环境与运行说明](docs/getting-started.md) · [独立示例](examples/README.md)
- [参与编写](CONTRIBUTING.md)

## 参考与许可

主要参考 [Hello-Agents](https://github.com/datawhalechina/hello-agents)。本手册按自己的学习顺序和案例重新组织，相关章节保留教材出处，并标明教学简化与项目扩展。

学习正文与教材衍生摘要采用 **CC BY-NC-SA 4.0**；原创代码、工程说明和原创中文图采用 [MIT License](LICENSE)。图示根据我们的代码与案例重新设计，不复制教材图片。详细范围见 [NOTICE.md](NOTICE.md)。
