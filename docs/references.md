# 教材与呈现方式参考

[返回项目首页](../README.md)

本资料库以 **Datawhale Hello-Agents 为知识主线**，按本项目的学习范围重新编排。其他开源课程与项目用于参考阅读导航、案例递进和验收表达；具体技术内容仍以各章的教材定位为起点。

## 主教材：概念、实现与结果连在一起

[Hello-Agents 仓库](https://github.com/datawhalechina/hello-agents) 按基础、智能体构建、高级扩展与应用组织内容，并在目录中交代每章主题。本项目沿用“先理解机制，再进入框架和项目”的学习顺序，具体取舍见 [课程对应关系](roadmap.md)。

重点参考 [第四章：智能体经典范式构建](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter4/第四章%20智能体经典范式构建.md)。它将流程讲解、图示、分模块代码和运行结果放在同一章内，便于读者把设计与实际行为对照。本项目对应的改编范围是：

| 教材部分 | 本项目使用方式 | 明确调整之处 |
| --- | --- | --- |
| §4.2 ReAct | 理解模型决策、程序执行与观察回传 | 用模拟天气与本地资料降低外部服务依赖 |
| §4.3 Plan-and-Solve | 先生成计划，再携带原题与历史逐步执行 | 采用 JSON 计划，增加总调用预算与状态区分 |
| §4.4 Reflection | 初稿、评审、修订和再次评审 | 将代码优化改为文字解释修订，采用结构化评审协议 |

例题保留教材来源，补充实现说明输入与输出；固定输入练习在入口注明运行方式。

## README、需求与课程设计参考

下表记录值得借鉴的组织方式，以及它们在本手册中的落点。课程型仓库与工具型仓库的读者目标不同，应按用途取舍。

| 来源 | 参考之处 | 本项目如何使用 |
| --- | --- | --- |
| [Hello-Agents 第十六章 §16.2、§16.4](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter16/第十六章%20毕业设计.md) | 选题从问题、功能与预期成果展开；README 包含示例、评估和未来计划 | [项目任务书](practice/research-agent.md) 集中说明读者问题、输入输出、场景与验收；课程范围仍为单体 Agent |
| [Microsoft AI Agents for Beginners](https://github.com/microsoft/ai-agents-for-beginners) · [Planning Design](https://github.com/microsoft/ai-agents-for-beginners/blob/main/07-planning-design/README.md) | 课程目录连接文字、代码和扩展阅读；章节先说明学习目标 | 首页保留逐章问题，环境配置独立；[课程地图](course-map.md) 对应先修、目标和产物 |
| [Hugging Face Agents Course](https://huggingface.co/learn/agents-course/unit0/introduction) · [循环讲解](https://huggingface.co/learn/agents-course/unit1/agent-steps-and-structure) | 先修提示、逐步例子与自查帮助读者进入课程 | 基础章节围绕消息流展开；练习先预测，再对照解析 |
| [smolagents](https://github.com/huggingface/smolagents) | README 用具体任务展示用途，并提供机制图与详细文档入口 | 首页直接呈现资料问答的结果差异；细节时序图放在对应章节 |
| [Deep Research From Scratch](https://github.com/langchain-ai/deep_research_from_scratch) | 先定义研究的范围、过程和报告，再按构件递进 | [建设路线](roadmap.md#后续建设与完成条件) 以同一个研究任务组织后续扩展；先写任务要求，再整合工具 |
| [Open Deep Research](https://github.com/langchain-ai/open_deep_research) | 配置、用途、评估方法与结果有明确入口 | [项目验收](practice/research-agent.md) 与 [评估说明](evaluation.md) 连接到逐题结果，避免只展示成功案例 |

这些参考启发了本项目的编排，不代表本项目具备上游工具的全部能力。框架、服务、认证或排行榜不因被参考而加入课程；项目当前实现与待建设内容分别列出。

## 图示与结果的使用规则

本项目图示根据自己的代码和课程问题绘制，采用白底、细线与少量配色。概览图交代学习阶段与产物；时序图放在对应机制旁，便于沿箭头对照代码。上述项目的图片与标识未移入本仓库。

每幅图应回答一个明确问题，例如“下一次请求从哪里得到历史”“修订完成为何仍要评审”。模型、程序和工具的职责应能从节点及连接读出，调用预算和停止出口应与代码一致。颜色只辅助分组，关键含义还要用文字和箭头表达。图源与维护方式见 [图示规范](assets/README.md)。

正文围绕实验结果解释机制，模型、日期和参数放入运行记录。固定输入练习用于复现特定分支；质量比较需要同题、同条件的多次实验。

阅读者应能在每章顺序找到：要解决的问题、核心机制、关键代码、实际结果、逐步解释、边界条件和带参考解析的练习。运行命令与完整源码用于复现这条学习过程。

---

各上游项目的文字、代码与图片仍受其自身许可证约束。本页记录来源与借鉴范围，不把其他项目内容重新声明为本项目原创。本文采用 [CC BY-NC-SA 4.0](../LICENSES/CC-BY-NC-SA-4.0.txt)。
