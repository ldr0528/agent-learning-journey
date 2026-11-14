# Agent Loop：多轮决策与停止条件

[返回知识导航](../../README.md#知识导航) · 上一篇：[工具结果回传](tool-feedback.md) · 下一篇：[检索与引用](retrieval-and-citations.md)

教材入口：[Hello-Agents 第四章 §4.2，重点 §4.2.3](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter4/第四章%20智能体经典范式构建.md)。当前是 ReAct 的教学简化实现，省略 Thought 长文本；`step_limit` 状态与下面的对照实验属于本项目扩展。

## 为什么需要循环

单次工具回传预先安排“请求工具 → 回答”。任务变成“分别查询北京、上海，再比较哪里更暖和”后，模型可能需要多次取数据。循环在每轮发送已有消息，接收下一步行动，执行并回传结果，直到接受最终答复或用完预算。

![模型决策、程序执行、资料回传与停止分支](../assets/agent-loop-zh.svg)

## 一条已经运行过的轨迹

以下保留天气实验的关键输出，天气均为模拟数据：

```text
第 1 轮：Action: get_weather(city="北京")
         Observation: 下雨，12℃
第 2 轮：Action: get_weather(city="上海")
         Observation: 晴天，22℃
第 3 轮：Action: Finish[上海更暖和（22℃ vs 北京12℃），数据为模拟天气。]

模型请求 3 次；工具执行 2 次。
```

第三轮没有新工具操作，但比较结论仍需要一次模型请求产生。程序识别 Finish 后提取答案并结束。这解释了为什么“查两个城市”不等于“最多请求模型两次”。

每轮结束后，已有 Action 和 Observation 被保存在 `messages` 中；第三次请求因此可以同时包含两座城市的结果。下一步行动的顺序由模型输出决定，上面的次数是具体运行轨迹，不是所有模型运行都必然相同。

## 对照实验：把预算改成 2

```bash
python -m examples.weather_loop
python -m examples.weather_loop --max-steps 2
```

已有对照运行在两轮内查完两座城市，随后输出“达到 2 轮上限，任务未完成”，计数为模型 2 次、工具 2 次。程序没有再额外请求模型生成总结。

| 机制 | 谁决定 | 本项目中的作用 |
| --- | --- | --- |
| 下一步 Action | 模型根据当前输入生成 | 继续使用工具，或尝试 Finish |
| 接受 Finish | 程序解析并按任务规则校验 | 产生 `finished` 状态 |
| 请求上限 | 程序中的 `max_steps` | 阻止继续请求，必要时产生 `step_limit` |

`finished` 代表最终答复被流程接受，不能证明内容正确；`step_limit` 代表预算内没有取得有效最终答复。研究助手中的有效“资料不足”也能结束流程。

## 读代码时抓住三个位置

在 [loop.py](../../src/agent_learning/loop.py) 中找到 `for step ...`、`messages.append(...)` 和 Finish 分支，分别对应预算、历史信息和结束判断。再看 [天气任务](../../src/agent_learning/agents/weather.py) 如何提供提示词与工具，而复用同一个循环。

当前 `step`、`tool_calls` 和 `max_steps` 是程序变量，并未作为动态预算消息发送给模型。程序知道还剩几轮，模型不一定获得了这项信息——这是下一步学习状态与上下文的切入点。

自检：为什么完成两次工具执行后仍可能未完成？如果模型多花一轮修正输出格式，会消耗哪个预算？

---

本页为教材辅助学习笔记，结合本项目代码与实验整理，非教材原文；采用 [CC BY-NC-SA 4.0](../../LICENSES/CC-BY-NC-SA-4.0.txt)。
