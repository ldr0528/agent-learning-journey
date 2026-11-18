# 手册配套示例

[手册正文](../README.md#章节目录) 已包含关键代码、已有结果与解释。这里列出可独立运行的配套示例，供希望进一步复现或修改的读者使用。环境配置见 [配套说明](../docs/getting-started.md)；以下命令均从仓库根目录执行。

| 知识主题 | 实验入口 | 运行后应能解释 |
| --- | --- | --- |
| [模型调用与消息](../docs/learning/model-calls.md) | `python -m examples.model_call` | system 与 user 分别提供了什么信息 |
| [Action 与工具执行](../docs/learning/tool-feedback.md) | `python -m examples.tool_execution` | 没有模型参与时，Python 为什么也能执行工具 |
| [结果回传](../docs/learning/tool-feedback.md) | `python -m examples.tool_roundtrip --city 上海` | 哪一步让第二次请求获得了工具结果 |
| [Agent Loop](../docs/learning/agent-loop.md) | `python -m examples.weather_loop` | 模型请求与工具执行为什么分别计数 |
| [历史筛选与摘要](../docs/learning/state-and-context.md#58-截断历史会丢掉什么摘要怎样补回来) | `python -m examples.context_preview` | 怎样保留较早的工具证据 |
| [本地检索](../docs/learning/retrieval-and-citations.md) | `python -m agent_learning.tools.notes --query "最大步数"` | 摘要、标签、编号和原文链接各有什么用途 |
| [带引用的回答](../docs/practice/research-agent.md) | `python -m agent_learning --question "Agent Loop 为什么要有最大步数？"` | 回答是否引用了真正支持结论的资料 |

`python -m examples.model_call --check` 只检查配置。工具执行、本地检索与上下文预览不读取密钥、不联网；其余实验会产生模型 API 用量。

## 只改变一个条件

| 对照方式 | 观察重点 |
| --- | --- |
| 单次调用只改 system 中的回答语言 | 输入说明怎样影响回复形式 |
| 回传实验将 `--city 上海` 改成 `--city 广州` | 缺少数据时是否如实说明 |
| 天气循环加 `--max-steps 2` | 查到数据与输出有效 Finish 是否是同一件事 |
| 研究助手的问题改为 checkpoint 的作用 | 当前摘要不足时是否编造回答 |

天气只有北京与上海的模拟数据；不将结果解释为实时天气。上限实验中的 `step_limit` 与退出码 1 可以是符合预期的结果。更完整的验收见 [评估文档](../docs/evaluation.md)。

示例依次复用 `agent_learning` 中的配置、请求、工具与循环。学习时先定位一段关键代码，再做小幅修改，最后用观察结果解释机制。

## 状态与上下文：预算提示对照

这个实验对应 Hello-Agents 第九章 §9.1、§9.2.1。保持问题、模型和请求上限一致，仅切换是否把本轮剩余预算加入模型消息：

```bash
python -m examples.weather_loop --max-steps 2
python -m examples.weather_loop --max-steps 2 --budget-context
```

开启后，每轮会显示实际附加到请求中的预算提示；提示只加入本轮的消息副本，不累积到历史。程序的请求上限仍为 2。此处统计的是模型请求次数，不是 token 预算。

两次已有真实运行都在两次查询后耗尽预算。保持提示开启，再只把上限改为 3：

```bash
python -m examples.weather_loop --max-steps 3 --budget-context
```

该次运行在第三轮输出有效 Finish。完整结果与原因解释见 [第 5 章](../docs/learning/state-and-context.md)；不能据此归因于提示效果，因为这次同时增加了可用请求次数。

离线检查使用固定模型回复，验证提示更新、历史保留和上限约束。真实模型结果另行核对数据是否齐全、是否有有效 Finish，以及结论是否有依据。

## 状态与上下文：摘要接回循环

先离线查看完整历史、最近两条历史、较早摘要加最近历史的区别：

```bash
python -m examples.context_preview
```

程序直接执行本地模拟天气工具，显示三种消息输入，不调用模型。结果和分析已经写入 [第 5 章](../docs/learning/state-and-context.md#58-截断历史会丢掉什么摘要怎样补回来)。

接入循环后，保持问题、模型、预算提示和上限一致，仅切换历史整理方式：

```bash
python -m examples.weather_loop --max-steps 3 --budget-context --context-mode full
python -m examples.weather_loop --max-steps 3 --budget-context --context-mode summary
```

默认使用 `full`。`summary` 在较早历史存在时，用带来源的工具结果摘要替代旧的 Action/Observation 对，保留最近一对原始消息；本轮预算最后追加。较早历史出现不能整理的格式时保留完整历史。原始任务历史不会被摘要覆盖。

上述两条命令会调用模型 API。摘要模式已有离线验证，真实模型结果尚待运行；不要把测试中预设的 Finish 当成模型实测。消息减少不等于 token 减少，也尚未证明摘要提高了正确率。
