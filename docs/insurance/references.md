# 医疗险比较的资料与设计参考

[返回第 12 章](course-guide.md) · [业务任务书](requirements.md) · [架构设计](architecture.md) · [通用教材参考](../references.md)

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

## Frictionless Insurance Advisor：需求、比较与来源之间的衔接

参考 [AWS Samples 的 Frictionless Insurance Advisor](https://github.com/aws-samples/sample-frictionless-insurance-advisor)。该示例围绕保险顾问组织客户资料、产品比较和资料浏览，并将演示资料与业务边界写明。

| 实际源码 | 可借鉴的组织方式 | 本项目的适配与限制 |
| --- | --- | --- |
| [agent/app.py](https://github.com/aws-samples/sample-frictionless-insurance-advisor/blob/main/agent/app.py) | 分步收集信息，识别缺失项，确认重要字段变化 | 整理需求提案后由用户确认；不收集顾问 CRM 中与当前比较无关的字段 |
| [ComparatorPage.tsx](https://github.com/aws-samples/sample-frictionless-insurance-advisor/blob/main/react-frontend/src/components/ComparatorPage.tsx) | 先选择对象，再展示并排比较；分别处理加载、错误与重试 | 使用本地目录的 2–3 个产品版本，比较格仍由程序从事实组装 |
| [sources.py](https://github.com/aws-samples/sample-frictionless-insurance-advisor/blob/main/agent/sources.py) | 从工具结果收集来源候选，再附到回答 | 使用精确证据编号校验；报告追问进一步限制为当前有效报告的来源快照 |
| [useAgentChat.ts](https://github.com/aws-samples/sample-frictionless-insurance-advisor/blob/main/react-frontend/src/hooks/useAgentChat.ts) | 按客户隔离会话，将结构化事件关联到对应消息 | 按本地会话与运行隔离；切换页面后，旧事件不能进入另一份报告 |

我们面向中国内地投保用户。上游的顾问销售流程、云端客户系统、自拟海外产品和估费规则没有移入本项目；它们不能充当中国内地医疗险事实或保费依据。前端整体分区可对照其 [界面说明](https://github.com/aws-samples/sample-frictionless-insurance-advisor/blob/main/react-frontend/README.md)。

## Moneta Agents：需求信息与产品检索职责分开

[Moneta](https://github.com/Azure-Samples/moneta-agents) 面向保险与银行顾问。其 [保险协调器](https://github.com/Azure-Samples/moneta-agents/blob/main/src/backend/foundry/orchestrators/open_ai_insurance_orchestrator.py) 区分客户资料和产品研究，客户资料缺少必要标识时要求补充；[保险条款工具](https://github.com/Azure-Samples/moneta-agents/blob/main/src/backend/foundry/agents/insurance/policies/policies_functions.py) 将搜索结果作为结构化工具输出返回。

本项目借鉴职责划分，在同一个 Python 工作流中分别处理需求、取证和结果，不为这些职责各增设一个 Agent。目录查询继续保留产品、版本、证据编号和定位；不移植 Azure AI Search、CosmosDB 或云端多 Agent 编排。Moneta 搜索结果会去掉部分内部编号，我们不沿用这一处理来删减自己的证据标识。

## Agent Chat UI：会话、工具进度与报告分别呈现

[Agent Chat UI](https://github.com/langchain-ai/agent-chat-ui) 已于 2026 年 11 月 3 日归档。本项目只借鉴可读的交互分工，不将该项目或 LangGraph 服务端作为本地网页的新增运行依赖。

| 实际源码 | 交互机制 | 本项目中的对应位置 |
| --- | --- | --- |
| [history/index.tsx](https://github.com/langchain-ai/agent-chat-ui/blob/main/src/components/thread/history/index.tsx) | 用可读的问题标题列出会话，并区分加载与选中状态 | 本地会话列表与已有报告回看 |
| [thread/index.tsx](https://github.com/langchain-ai/agent-chat-ui/blob/main/src/components/thread/index.tsx) | 会话切换、消息提交、错误反馈与独立内容区域 | 聊天与后台任务分离，页面刷新不重新提交任务 |
| [messages/tool-calls.tsx](https://github.com/langchain-ai/agent-chat-ui/blob/main/src/components/thread/messages/tool-calls.tsx) | 分开显示工具请求与返回内容 | 业务进度默认简短，参数与证据在详情中查看 |
| [artifact.tsx](https://github.com/langchain-ai/agent-chat-ui/blob/main/src/components/thread/artifact.tsx) | 在聊天之外呈现独立产物 | 版本化比较报告与证据抽屉 |

上游的可恢复流和 checkpoint 功能依赖其服务端协议。我们采用本地后台运行、事件轮询与报告快照，不能仅凭相似界面声称具有相同的执行恢复能力。

## 本地实现约定：不是照搬云端架构

需求确认、运行幂等、过期修订拒绝、合作取消和重启后标记 `interrupted` 是本项目针对本地应用实现的契约，完整决策与接口见 [架构设计](architecture.md)。会话保存和执行管理分别见 [store.py](../../src/agent_learning/insurance/store.py)、[runs.py](../../src/agent_learning/insurance/runs.py)；同步 CLI 也通过 `claim_session()` 在调用模型前认领会话。对应行为由 [运行与存储检查](../../tests/test_insurance_runs.py) 和 [对话边界检查](../../tests/test_insurance_conversation.py) 验证。

后台执行使用 Python 标准库，应用状态由 `sqlite3` 保存为单表 JSON 记录，旧 JSON 文件按需迁移并保留。取消行为对照 [CPython Future 源码](https://github.com/python/cpython/blob/3.13/Lib/concurrent/futures/_base.py) 与 [官方取消说明](https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.Future.cancel)：运行中的调用不能依靠取消 Future 强制撤回。事务控制对照 [Python sqlite3](https://docs.python.org/3/library/sqlite3.html#transaction-control) 与 [SQLite 事务文档](https://www.sqlite.org/lang_transaction.html)；数据库写入事务与程序的需求版本、运行归属检查共同防止覆盖，不需要部署云端数据库。

## 产品资料：区分教学目录与官方摘录

自拟的三款教学产品用于覆盖九个比较维度，资料版本为 `demo-v1`。它们的名称与保障条件不对应现实保险产品，保费维度明确记录为未知。

资料入口：[教学产品目录](../../src/agent_learning/data/insurance_demo.json)、[官方摘录目录](../../src/agent_learning/data/insurance_official.json)。官方目录的每个产品保留 `source.url`、原文位置和核对信息，比较报告从同一记录生成来源链接。

官方目录只保存少量人工核对的概括，不是合同原文。目录中的来源链接与原文位置用于回查依据，阅读时应同时检查产品标识、资料版本、维度和适用条件。

`snapshot-2026-11-19` 标记本地资料快照，不表示合同生效日、条款备案版本或销售状态。概括没有提供报价、健康告知细则或其他责任时，应保持未知，不能用另一产品的内容填补。

| 所问的问题 | 应查哪类依据 |
| --- | --- |
| Agent 怎样组织规划、工具与反馈？ | Hello-Agents 与本项目代码 |
| 比较页怎样让需求、差异和证据对应？ | 业务任务书、架构设计、开源应用的交互源码 |
| 某个保障条件在资料中怎样表述？ | 该产品、该版本的目录事实及原始来源 |
| 用户是否有适用报价或可以获承保？ | 保险方针对具体条件提供的信息，不能由教学目录推断 |

## 本项目的编写方式

课程用自己的数据结构与业务流程讲解，每次改动都应能回到具体的输入、证据和结果。引用片段保留出处，示意数据标明性质，图示根据本项目流程重新绘制。

上述开源仓库用于阅读与设计参考；本页没有复制其界面图片或整段实现。官方条款仍受原来源权利约束。本页文字采用 [CC BY-NC-SA 4.0](../../LICENSES/CC-BY-NC-SA-4.0.txt)。
