# 分层实验：从概念到观察

先阅读对应知识笔记，预测结果，再运行并解释差异。环境配置见 [复现指南](../docs/getting-started.md)；以下命令均从仓库根目录执行。

| 知识主题 | 实验入口 | 运行后应能解释 |
| --- | --- | --- |
| [模型调用与消息](../docs/learning/model-calls.md) | `python -m examples.model_call` | system 与 user 分别提供了什么信息 |
| [Action 与工具执行](../docs/learning/tool-feedback.md) | `python -m examples.tool_execution` | 没有模型参与时，Python 为什么也能执行工具 |
| [结果回传](../docs/learning/tool-feedback.md) | `python -m examples.tool_roundtrip --city 上海` | 哪一步让第二次请求获得了工具结果 |
| [Agent Loop](../docs/learning/agent-loop.md) | `python -m examples.weather_loop` | 模型请求与工具执行为什么分别计数 |
| [本地检索](../docs/learning/retrieval-and-citations.md) | `python -m agent_learning.tools.notes --query "最大步数"` | 摘要、标签、编号和原文链接各有什么用途 |
| [带引用的回答](../docs/practice/research-agent.md) | `python -m agent_learning --question "Agent Loop 为什么要有最大步数？"` | 回答是否引用了真正支持结论的资料 |

`python -m examples.model_call --check` 只检查配置。工具执行与本地检索不读取密钥、不联网；其余实验会产生模型 API 用量。

## 只改变一个条件

| 对照方式 | 观察重点 |
| --- | --- |
| 单次调用只改 system 中的回答语言 | 输入说明怎样影响回复形式 |
| 回传实验将 `--city 上海` 改成 `--city 广州` | 缺少数据时是否如实说明 |
| 天气循环加 `--max-steps 2` | 查到数据与输出有效 Finish 是否是同一件事 |
| 研究助手的问题改为 checkpoint 的作用 | 当前摘要不足时是否编造回答 |

天气只有北京与上海的模拟数据；不将结果解释为实时天气。上限实验中的 `step_limit` 与退出码 1 可以是符合预期的结果。更完整的验收见 [评估文档](../docs/evaluation.md)。

示例依次复用 `agent_learning` 中的配置、请求、工具与循环。学习时先定位一段关键代码，再做小幅修改，最后用观察结果解释机制。
