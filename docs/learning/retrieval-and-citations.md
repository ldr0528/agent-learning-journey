# 检索与引用：怎样让回答有据可查

[返回知识导航](../../README.md#知识导航) · 上一篇：[Agent Loop](agent-loop.md) · 实践：[Research Agent](../practice/research-agent.md)

教材连接：[Hello-Agents 第四章 §4.2 的工具循环](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter4/第四章%20智能体经典范式构建.md)。本页的本地摘要检索、编号校验和资料不足实验是项目扩展，不代表已经完成第八章 RAG 的系统学习。

## 从天气工具换成资料工具

循环机制保持不变，把 `get_weather` 换成 `search_notes`，模型就能请求本地资料。资料来自 [notes.json](../../src/agent_learning/data/notes.json) 中的三条教学摘要，包含编号、标签、内容、教材章节和原文链接。

检索使用关键词标签匹配，最多返回两条。没有向量数据库，也没有联网浏览教材；外部原文链接用于读者查证。

## 读懂一次两轮回答

问题：“Agent Loop 为什么要有最大步数？”已有运行的结构如下，摘要与答案为节选：

```text
第 1 轮：Action: search_notes(query="Agent Loop 最大步数")
         Observation: [N01] Agent Loop 的基本过程
                      [N03] Finish 与最大步数

第 2 轮：Action: Finish[最大步数限制执行预算……本练习达到上限且没有有效
         Finish 时报告未完成。[N03]]

模型请求 2 次；工具执行 1 次。
```

第一轮模型只决定查什么，Python 读取并格式化资料；第二轮模型根据已回传的资料回答。`[N03]` 指向本次检索返回的记录，最终展示的原文链接由程序从记录读取。

“无有效 Finish 就报告未完成”是本项目的状态约定，回答中应保留这个限定，不能将它写成教材原文或所有 Agent 的统一规则。

## 三种容易混淆的情况

| 现象 | 可以说明什么 | 还不能说明什么 |
| --- | --- | --- |
| 查询没有命中摘要 | 当前数据与匹配方式没有找到结果 | 教材没有相关知识 |
| 查询命中某条摘要 | 标签匹配到了记录 | 记录足以回答这个问题 |
| 答案引用本次返回的编号 | 引用编号可追溯 | 资料支持答案中的每个结论 |

例如，查询“LangGraph 的 checkpoint 有什么作用”时，当前资料不足。即使用“Agent Loop”命中了 N01，它也只介绍循环过程，不能据此说明 checkpoint 的状态恢复机制。

## 程序检查和人工判断各做什么

[research.py](../../src/agent_learning/agents/research.py) 要求先检索再结束，拒绝引用本次未返回的编号，并检查 Finish 中是否有引用或明确的“资料不足”说明。它还阻止再次执行相同查询，把具体错误反馈给下一轮模型。

这些规则检查流程与编号，尚未做语义事实核验。模型即使引用了真实编号，也可能误用资料；是否支持结论仍需按 [评估标准](../evaluation.md) 人工检查。

## 自己复现

```bash
python -m agent_learning.tools.notes --query "最大步数"
python -m agent_learning --question "Agent Loop 为什么要有最大步数？"
python -m agent_learning --question "LangGraph 的 checkpoint 有什么作用？"
```

先看工具实际返回了什么，再看模型答案引用了哪条资料。对没有依据的问题，诚实说明不足是符合边界要求的行为，不能记为已经解答问题。

自检：如果引用编号合法，但摘要没有支持答案，应该改进的是引用格式、检索资料还是回答内容？为什么不能只看程序是否正常退出？

---

本页为教材辅助学习笔记，结合本项目代码与实验整理，非教材原文；采用 [CC BY-NC-SA 4.0](../../LICENSES/CC-BY-NC-SA-4.0.txt)。
