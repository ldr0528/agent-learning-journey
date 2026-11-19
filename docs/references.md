# 教材与开源项目参考

[课程目录](../README.md#章节目录) · [教材映射](roadmap.md) · [保险资料来源](insurance/references.md)

本仓库以 Hello-Agents 为主要教材。课程型仓库用于确定阅读结构，保险应用用于理解业务组织；两者分别服务于教材与综合实践。

## 三个主要参考及落点

| 参考项目 | 上游的组织方式 | 本项目对应位置 |
| --- | --- | --- |
| [Datawhale Hello-Agents](https://github.com/datawhalechina/hello-agents) | README 按部分与章节导航，正文与配套代码对应，综合案例位于基础和进阶知识之后 | 首页是唯一总目录；01–11 讲机制，12 章讲医疗险综合实战；正文放在 `docs/`，入口和实现分别放在 `examples/`、`src/` |
| [Microsoft AI Agents for Beginners](https://github.com/microsoft/ai-agents-for-beginners) | 每课说明学习目标并关联代码，安装准备集中在独立课程配置页 | 章首提供目标、示例与实现入口；环境配置只维护一份；正文保留代码和输出解释 |
| [AWS Frictionless Insurance Advisor](https://github.com/aws-samples/sample-frictionless-insurance-advisor) | 保险应用有明确的用户场景、比较对象、工具和资料展示 | 第 12 章围绕需求、产品版本、证据和比较报告展开；业务契约、资料规范与实验记录分别维护 |

这三者的技术栈和用户群并不相同。我们的课程选用单体 Agent、LangGraph 与本地 MCP；保险案例面向投保用户，采用本地工作区。上游的多 Agent、云端客户系统和顾问销售流程不属于本项目当前实现。

## 知识来源怎样落到章节

[Hello-Agents 第四章](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter4/第四章%20智能体经典范式构建.md) 是模型调用、ReAct、Plan-and-Solve 和 Reflection 的主要来源。各章保留教材链接，并用本项目的输入、代码和结果重新解释。

| 教材机制 | 本项目的练习 | 实现取舍 |
| --- | --- | --- |
| ReAct 的决策与观察 | 天气查询和课程资料问答 | 基础章节使用文本 Action，保险案例使用原生工具调用 |
| Plan-and-Solve | 计划解析与逐步执行 | JSON 计划、前序结果、总请求预算 |
| Reflection | 解释草稿的评审与修订 | 有限修订和结构化反馈；评审通过仍需核对依据 |

上下文、检索、评估、LangGraph 与 MCP 的准确教材位置见 [对应表](roadmap.md)。保险中的固定计划和程序校验，与模型生成计划、模型评审分别说明，不把尚未整合的机制写成已有能力。

## 文档各自负责什么

| 位置 | 维护内容 |
| --- | --- |
| 根 README | 项目介绍、唯一课程总目录、开始阅读与安装入口 |
| `docs/learning/` 与保险 `course-guide.md` | 学习问题、原理与图、代码、输出解释和练习 |
| `docs/course-map.md` | 学习目标、先修要求和阶段验收 |
| `docs/roadmap.md` | Hello-Agents 映射、范围取舍与后续建设 |
| `docs/insurance/requirements.md` | 综合项目的业务规格与完成条件 |
| `examples/README.md` | 复现命令、参数与是否请求模型 |
| `docs/runs/` 与保险 `runs/` | 原始记录、运行参数、版本与用量 |

天气和课程资料问答是章节练习，医疗险是综合项目。新增材料应归入相应章节或项目文档，并同步目录与前后章导航。

## 图示、结果与许可

图示按本项目机制重新绘制，遵循 [白底、细线与少量配色的规范](assets/README.md)。每幅图对应明确的流程或数据关系；架构图与实际实现保持一致。

正文直接展示理解机制所需的代码和结果。模型名称、日期、请求参数与用量集中在实验记录；节选与整理注明范围，原始结果不改写。

其他补充实现参考及产品资料来源集中在 [保险参考文档](insurance/references.md) 与相应章节。第三方文字、代码和图片仍遵循原许可证；本页采用 [CC BY-NC-SA 4.0](../LICENSES/CC-BY-NC-SA-4.0.txt)。
