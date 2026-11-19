# 第 11 章 · MCP：让工具通过标准协议被调用

[章节目录](../../README.md#章节目录) · [上一章：LangGraph](langgraph.md) · [贯穿项目：Research Agent](../practice/research-agent.md)

本章以 [Hello-Agents 第十章 §10.2 MCP 协议实战](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter10/第十章%20智能体通信协议.md) 为参考，把已有天气工具和本地摘要检索暴露为 MCP 工具。为看清协议边界，我们直接使用官方 Python SDK，不再套一层 HelloAgents 客户端；这是实现方式的调整。本轮不扩展 A2A、ANP 或多 Agent。

## 11.1 为什么普通函数调用还不是 MCP

以前程序直接调用 `get_weather("北京")`，调用方知道函数位置和参数。MCP 场景中，工具服务可以是另一个进程：客户端先发现它提供哪些工具、各自需要什么参数，再通过协议发起调用。

本项目保留同一个天气函数，让它在服务端执行。变化发生在调用边界，而不是天气数据本身。

| 角色 | 本项目对应物 | 职责 |
| --- | --- | --- |
| Host / 宿主程序 | `examples.mcp_demo` | 启动演示、展示结果；本例没有接入模型 |
| Client | `ClientSession` | 初始化会话、发现工具、发送调用 |
| Server | 本地 Python 子进程 | 暴露工具定义，校验参数，调用本地函数 |
| 工具实现 | `get_weather`、`search_notes` | 返回模拟天气或教学摘要 |

![真实框架与协议适配的职责边界](../assets/framework-protocol-zh.svg)

模型本身不会因为装了 SDK 就自动连接工具。宿主需要把工具说明交给模型，接收模型的选择，再代它发出 MCP 请求。我们先单独验证协议和工具，让这段通信不依赖模型的随机输出。

## 11.2 一次会话的实际顺序

演示使用标准输入输出，也就是 stdio。客户端启动服务端子进程，通过两条流交换 MCP 消息。官方 SDK 负责 JSON-RPC 消息、请求编号、初始化通知以及返回值解码。

```text
启动服务端子进程
    ↓
initialize：协商版本与能力
    ↓
list_tools：取得名称、说明、参数 schema
    ↓
call_tool("weather", {"city": "北京"})
    ↓
服务端调用本地 get_weather → 返回结果
    ↓
call_tool("search_notes", {"query": "Action Observation"})
    ↓
结束会话并清理子进程
```

Python 方法名为 `list_tools` 和 `call_tool`，对应协议中的 `tools/list`、`tools/call` 方法。初始化的意义不只是打印“连接成功”，而是让两端确认可以怎样交换后续消息。生命周期与传输细节见 [MCP 初始化规范](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle) 和 [stdio 传输规范](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)。

## 11.3 服务端：保留原来的工具逻辑

[服务端完整代码](../../src/agent_learning/integrations/mcp_server.py) 创建 `FastMCP`，并注册两个工具。天气工具的实际定义如下：

```python
@server.tool()
def weather(city: str) -> dict:
    """查询本项目模拟天气；北京和上海有数据，其他城市返回暂无天气数据。"""
    if not city.strip():
        raise ValueError("city 不能为空。")
    return {"city": city.strip(), "weather": get_weather(city.strip()), "simulated": True}
```

工具名称、docstring 和类型标注用于构造发现结果。客户端能知道 `city` 是必填字符串；真正的业务检查仍由函数执行。返回值保留 `simulated: true`，避免把练习数据误解成真实天气。

服务端入口调用：

```python
create_server().run(transport="stdio")
```

stdio 模式下 stdout 是协议通道，不能在服务端随意向 stdout 打印调试文字。本项目通过 SDK 的日志通道或 stderr 报告错误。客户端自己的终端输出不占用服务端的协议流。

另一个工具 `search_notes` 读取既有本地摘要，返回资料编号、内容、出处和原文链接。它没有因为经过 MCP 就变成语义搜索，仍遵守原先的标签检索规则。

## 11.4 客户端：发现定义，再实际调用

[客户端完整代码](../../src/agent_learning/integrations/mcp_client.py) 使用当前 Python 解释器启动模块，这让客户端和服务端处于同一已安装环境。关键会话部分如下，参数构造和退出处理见源码：

```python
async def exchange():
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            initialized = await session.initialize()
            tools = await session.list_tools()
            weather = await session.call_tool("weather", {"city": city})
            notes = await session.call_tool("search_notes", {"query": query})
```

这里没有直接导入并调用服务端的 `weather` 函数。调用经过客户端流、子进程中的 MCP 服务端，再到本地工具。`list_tools` 本身不会查询天气，只有 `call_tool` 才触发相应业务函数。

返回值也分层：客户端先检查 `isError`，再读取结构化内容；若 SDK 返回文本块，则解析其中的 JSON。工具调用失败不能被当成正常证据。本例给整个会话设置了 20 秒超时，并通过异步上下文管理器关闭连接和子进程。

## 11.5 已实际运行的协议结果

助教在 Python 3.12、官方 `mcp==1.30.0` 环境中启动了真实子进程。以下是实际输出节选，模型 API 请求为 0：

```text
真实 MCP stdio 会话；工具在子进程执行，本次模型请求 0 次。
initialize：agent-learning-tools；协商协议版本：2025-11-25
list_tools：search_notes, weather
call_tool weather：北京，下雨，12℃，模拟数据。
call_tool search_notes：N02
```

后续输出列出 N02 的摘要内容及原文链接。测试同时检查了工具发现中的 `city` 参数 schema，并验证广州返回“暂无天气数据”、未知检索词返回空列表。缺少数据不会因为经过协议而变成有效答案。

本次协商得到的版本来自 SDK 的实际握手，不是我们手写一个版本字符串来模拟成功。未来升级 SDK 后，协商版本可能变化，应重新运行集成测试，而不是仅修改教材输出。

## 11.6 和 Agent Loop 接起来时，还缺哪一步

当前演示显式指定调用哪个工具。真正接回 Agent 时，宿主还需要完成以下衔接：

| 环节 | 需要传递的信息 |
| --- | --- |
| 发现 → 模型请求 | 工具名称、说明、参数定义 |
| 模型选择 → MCP 客户端 | 工具名和解析后的参数 |
| MCP 返回 → 下一轮模型请求 | 实际结果、错误、来源和资料不足状态 |
| 最终回答 | 依据本次结果生成答案并校验引用 |

这与第 2 章的结论相同：结果打印到终端，不会自动让模型收到。MCP 解决通信边界，宿主仍要构造模型输入、限制执行预算，并处理工具失败。

本课程交付的是已验证的 MCP 工具服务和客户端，不把它描述成一个已经自动发现并自主选择所有工具的完整宿主。远程 HTTP 部署、认证和写入类工具不在此练习中。

## 11.7 版本、运行与自测

本项目固定官方 SDK 的 **1.30.0 维护线**，使用 `FastMCP`、`ClientSession` 和 `stdio_client`，便于与教材及 Python 3.10+ 的课程环境对照。这不是宣称 1.x 是最新主线；官方 SDK 已有 2.x，接口变化见 [官方 v1.30.0 说明](https://github.com/modelcontextprotocol/python-sdk/blob/v1.30.0/README.md)。SDK 内的 FastMCP 与独立发行的 `fastmcp` 包也不能仅凭同名混用。

```bash
python -m pip install -e ".[mcp]"
python -m examples.mcp_demo
python -m examples.mcp_demo --city 广州 --query "没有匹配的词"
```

两条演示都在本地运行，不需要 `.env` 或 API Key。客户端自动启动和关闭服务端，不用再手工打开一个后台窗口。

| 自测任务 | 参考答案或验收点 |
| --- | --- |
| 调用 list_tools 后，天气已经查过了吗？ | 没有；只得到了工具定义 |
| 广州没有数据，应该怎么返回？ | 保留“暂无天气数据”和模拟性质；不能编一个温度 |
| 把工具结果传给模型的责任在哪？ | 宿主程序；协议返回不等于已经进入模型输入 |
| 为什么禁止服务端随意 print？ | stdout 承载协议消息，混入普通日志会破坏解析 |
| 给服务端增加一个只读工具，客户端自动会使用吗？ | 可通过发现看到新定义，但是否调用仍需宿主或模型决策 |

推荐动手扩展：增加一个返回本地摘要数量的只读工具，检查 `list_tools` 的 schema，再由客户端显式调用一次。验收时分别展示发现结果和执行结果，而不是只展示服务端注册成功。

对应测试见 [MCP 集成测试](../../tests/test_mcp_integration.py)。当前实测验证协议与工具，不构成模型工具选择能力的评估，也不代表学习者已经完成这一章。

---

参考 Hello-Agents 第十章，按本项目已有工具重新设计；SDK 接口以固定版本的官方实现为准。正文采用 [CC BY-NC-SA 4.0](../../LICENSES/CC-BY-NC-SA-4.0.txt)。
