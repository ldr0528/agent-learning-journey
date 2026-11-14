# 工具调用：从 Action 到 Observation

[返回知识导航](../../README.md#知识导航) · 上一篇：[模型调用](model-calls.md) · 下一篇：[Agent Loop](agent-loop.md)

教材入口：[Hello-Agents 第一章 §1.2](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter1/第一章%20初识智能体.md)、[第四章 §4.2 ReAct](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter4/第四章%20智能体经典范式构建.md)。本项目使用模拟天气与文字协议简化观察过程。

## 谁产生了什么

当终端出现 `Action: get_weather(city="上海")` 时，要区分三个角色：

| 内容或动作 | 产生者 | 在本实验中的意义 |
| --- | --- | --- |
| `Action: get_weather(...)` | 模型 | 按提示中的工具说明提出操作请求 |
| 解析 Action，调用 `get_weather` | Python 程序 | 真正执行函数，获得模拟天气 |
| `Observation: 晴天，22℃` | 程序根据工具返回值组织 | 给下一次模型请求提供观察结果 |
| 根据天气作答 | 模型 | 读取回传结果后生成回答 |

模型输出的函数名与参数是文字。Python 必须识别允许的工具和参数，再调用已有函数；本项目不会执行任意模型代码。

## 关键不是打印，而是回传

下面是 [tool_roundtrip.py](../../examples/tool_roundtrip.py) 中连接两次模型请求的关键步骤：

```python
messages.append({"role": "assistant", "content": action})
messages.append({"role": "user", "content": f"Observation: {result}"})
answer = ask_model(client, model, messages, options)
```

第一条保存模型刚才提出的请求，第二条保存程序获得的结果。下一次调用提交扩充后的消息列表，模型才拿到这些信息。`print(result)` 只改变终端显示，不会改变发送给模型的消息。

这里的 Observation 使用程序构造的 `user` 消息承载，是教学文字协议的实现选择；它不是用户手动输入，也不是 API 原生的 `tool` 消息。

## 分别观察工具执行和结果回传

| 实验 | 命令 | 应观察什么 |
| --- | --- | --- |
| 独立执行工具 | `python -m examples.tool_execution` | 手动给定 Action 也能执行函数；此时没有模型参与决策。 |
| 完整结果回传 | `python -m examples.tool_roundtrip --city 上海` | 第一次请求选择工具，程序执行，第二次请求根据结果回答。 |
| 数据缺失 | `python -m examples.tool_roundtrip --city 广州` | 工具返回无数据，模型应说明无法依据现有数据回答。 |

已有广州实验给出了无天气数据的答复。这个例子说明回传的缺失信息也能影响回答；不能把结果替换成模型自行编造的实时天气。

## 结论与边界

Action 表达意图，工具函数执行操作，Observation 承载反馈。提示词解释可用工具和输出约定，程序负责实际执行与结果传递。

当前格式依靠提示词与解析规则，模型仍可能多写说明或给出错误格式。后续可以比较结构化工具调用；本阶段先把这条信息传递链理解清楚。

自检：如果只打印 Observation、没有把它放进下一次请求，第二次模型调用能否可靠地根据这次工具执行作答？请从 `messages` 的内容解释。

---

本页为教材辅助学习笔记，结合本项目代码与实验整理，非教材原文；采用 [CC BY-NC-SA 4.0](../../LICENSES/CC-BY-NC-SA-4.0.txt)。
