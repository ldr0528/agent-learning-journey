# 医疗险比较的资料与设计参考

[业务任务书](requirements.md) · [课程指南](course-guide.md) · [通用教材参考](../references.md)

本项目的三类来源承担不同职责：Hello-Agents 提供学习机制，开源应用提供业务组织参考，产品资料支持具体保障事实。设计参考仓库不能充当医疗险条款依据。

## Hello-Agents：沿一个业务问题学习机制

课程主线仍然来自 [Datawhale Hello-Agents](https://github.com/datawhalechina/hello-agents)。保险案例把原有的小练习连接成需求澄清、资料取证和报告比较。

| 教材位置 | 本业务中的对应问题 |
| --- | --- |
| [第四章 §4.2–4.4](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter4/第四章%20智能体经典范式构建.md) | 怎样选择工具、组织依赖步骤、检查比较表述并限制修订？ |
| [第八章 §8.3](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter8/第八章%20记忆与检索.md) | 怎样从选定产品和版本中取得相关条款，并保留来源？ |
| [第九章](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter9/第九章%20上下文工程.md) | 用户补充需求后，哪些新事实、旧证据和未知项应进入下一次请求？ |
| [第六章 §6.5](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter6/第六章%20框架开发实践.md) | 怎样把同一业务表示为状态、节点和条件转移？ |
| [第十章 §10.2](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter10/第十章%20智能体通信协议.md) | 怎样把条款工具放到独立服务中，仍保持同样的入参与结果？ |
| [第十二章](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter12/第十二章%20智能体性能评估.md) | 怎样分别检查工具使用、资料引用、业务边界与失败处理？ |

医疗险的字段、产品目录、比较表和未知事项处理是本项目的业务编排，不是 Hello-Agents 的保险案例。

## Frictionless Insurance Advisor：比较对象与资料原文放在一起

参考 [AWS Samples 的 Frictionless Insurance Advisor](https://github.com/aws-samples/sample-frictionless-insurance-advisor)。该示例围绕保险顾问组织客户资料、产品比较和资料浏览，并将演示资料与业务边界写明。

本项目主要借鉴三点：

- **先确定比较对象。** 产品选择与用户关注点是明确输入，不能只靠一段自由回答隐含地决定范围。
- **比较结果能够回到资料。** 对照表与来源浏览服务于同一任务，用户可以查看结论依据。
- **分析与业务决定分开。** 整理保障信息不等于取得有效报价或承保结果。

这里将读者与用户定位为中国内地投保用户，采用本地会话、少量产品资料和单体工具循环。上游的顾问销售流程、云端客户系统和产品数据没有移入本项目，也不作为中国内地医疗险事实依据。

## Open Deep Research：先澄清，再形成可追踪的研究任务

参考 [Open Deep Research](https://github.com/langchain-ai/open_deep_research) 及其 [主流程代码](https://github.com/langchain-ai/open_deep_research/blob/main/src/open_deep_research/deep_researcher.py)。其中的 `clarify_with_user` 根据需求是否清楚决定询问或继续，`write_research_brief` 将已有消息整理成研究任务。

这给保险比较的启发是：关注点缺失时先问清楚；进入取证阶段后，保留已经确定的产品、版本、维度和未知项。新信息到来时更新任务范围，再检查哪些证据仍然适用。

本项目采用单体 Agent 和确定性的比较表组装。借鉴的是澄清、取证和汇总之间的衔接，不移植上游多研究者并发流程，也不把通用网络搜索结果直接当作某个保险合同的条款。

## Microsoft 示例：工具边界与结果校验

[Moneta Agents 的保险条款模块](https://github.com/Azure-Samples/moneta-agents/blob/main/src/backend/foundry/agents/insurance/policies/policies_functions.py) 将保险资料查询放到业务工具中。本项目据此区分工具取证与回答呈现，并保留自己的证据编号、产品和版本，便于每个比较单元核对归属。

[Insurance Claims Review](https://github.com/Azure-Samples/azure-functions-hosted-skills-samples/tree/main/claims-review-workflow) 将材料检查和结果保存拆开。其业务是理赔，本项目只借鉴“程序核验输入与结果”的职责划分：模型提出完成操作，程序重新检查覆盖范围，不能直接信任模型声称资料已齐全。

## 产品资料：区分教学目录与官方摘录

自拟的三款教学产品用于覆盖九个比较维度，资料版本为 `demo-v1`。它们的名称与保障条件不对应现实保险产品，保费维度明确记录为未知。

资料入口：[教学产品目录](../../src/agent_learning/data/insurance_demo.json)、[官方摘录目录](../../src/agent_learning/data/insurance_official.json)。官方目录的每个产品保留 `source.url`、原文位置和核对信息，比较报告从同一记录生成来源链接。

官方资料只选取少量公开条款片段。目录中的来源链接与原文位置用于核对片段，阅读时应同时检查产品标识、资料版本、维度和适用条件。

`snapshot-2026-11-19` 标记本地摘录快照，不表示合同生效日、条款备案版本或销售状态。片段没有提供报价、健康告知细则或其他责任时，应保持未知，不能用另一产品的内容填补。

| 所问的问题 | 应查哪类依据 |
| --- | --- |
| Agent 怎样组织规划、工具与反馈？ | Hello-Agents 与本项目代码 |
| 比较页怎样让需求、差异和原文对应？ | 业务任务书、开源应用的交互设计 |
| 某个保障条件在资料中怎样表述？ | 该产品、该版本的条款片段及原文来源 |
| 用户是否有适用报价或可以获承保？ | 保险方针对具体条件提供的信息，不能由教学目录推断 |

## 本项目的编写方式

课程用自己的数据结构与业务流程讲解，每次改动都应能回到具体的输入、证据和结果。引用片段保留出处，示意数据标明性质，图示根据本项目流程重新绘制。

上述开源仓库用于阅读与设计参考；本页没有复制其界面图片或整段实现。官方条款仍受原来源权利约束。本页文字采用 [CC BY-NC-SA 4.0](../../LICENSES/CC-BY-NC-SA-4.0.txt)。
