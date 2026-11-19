# 课程例题与综合实战入口

[章节目录](../README.md#章节目录) · [环境配置](../docs/getting-started.md) · [运行记录](../docs/runs/README.md)

第 01–11 章的脚本对应独立例题；第 12 章使用医疗险资料比较项目。命令均从仓库根目录执行，先完成安装并激活虚拟环境。表中标注“调用 API”的模式需要模型配置，会产生服务商用量。

## 模型、工具与循环 · 01–04

| 章节与入口 | 模型 API | 可用参数 |
| --- | --- | --- |
| [01 模型调用](../docs/learning/model-calls.md)：`python -m examples.model_call` | 默认调用；加 `--check` 仅检查配置 | `--provider qwen` / `--provider openai` |
| [02 工具执行](../docs/learning/tool-feedback.md)：`python -m examples.tool_execution` | 不调用 | 本地模拟天气 |
| [02 结果回传](../docs/learning/tool-feedback.md)：`python -m examples.tool_roundtrip --city 上海` | 调用 | `--city`、`--provider` |
| [03 有限循环](../docs/learning/agent-loop.md)：`python -m examples.weather_loop --max-steps 3` | 调用 | `--question`、`--max-steps`、`--provider` |
| [04 本地检索](../docs/learning/retrieval-and-citations.md)：`python -m agent_learning.tools.notes --query "最大步数"` | 不调用 | `--query` |
| [04 检索与引用](../docs/learning/retrieval-and-citations.md)：`python -m agent_learning --question "Agent Loop 为什么要有最大步数？"` | 默认调用；加 `--check` 仅检查配置 | `--question`、`--max-steps`、`--provider` |

`agent-research` 与 `python -m agent_learning` 等价，是第 04 章的资料问答例题。`--check` 不验证服务权限或额度。

## 上下文与任务组织 · 05–07

| 章节与入口 | 模型 API | 可用参数 |
| --- | --- | --- |
| [05 上下文预览](../docs/learning/state-and-context.md)：`python -m examples.context_preview` | 不调用 | 展示构造后的消息 |
| [06 生成计划](../docs/learning/planning.md)：`python -m examples.plan_first --demo` | `--demo` 不调用；去掉后调用 | `--question`、`--provider` |
| [06 计划执行](../docs/learning/planning.md)：`python -m examples.plan_solve --demo` | `--demo` 不调用；去掉后调用 | `--question`、`--max-calls`、`--max-plan-steps`、`--provider` |
| [07 评审修订](../docs/learning/reflection.md)：`python -m examples.reflection --demo` | `--demo` 不调用；去掉后调用 | `--task`、`--max-calls`、`--max-revisions`、`--provider` |

### 状态与上下文：预算提示对照

以下命令均调用 API：

```bash
python -m examples.weather_loop --max-steps 2
python -m examples.weather_loop --max-steps 2 --budget-context
python -m examples.weather_loop --max-steps 3 --budget-context
```

### 状态与上下文：摘要接回循环

以下命令均调用 API；只切换历史模式：

```bash
python -m examples.weather_loop --max-steps 3 --budget-context --context-mode full
python -m examples.weather_loop --max-steps 3 --budget-context --context-mode summary
```

## 检索与质量 · 08–09

| 章节与入口 | 模型 API | 可用参数 |
| --- | --- | --- |
| [08 RAG](../docs/learning/rag.md)：`python -m examples.rag_research` | 默认不调用，输出证据摘录；`--live` 调用 | `--question`、`--top-k`、`--context-chars`、`--provider`、`--output`（Markdown） |
| [09 评估](../docs/learning/evaluation.md)：`python -m examples.evaluate` | 不调用 | `--k`、`--predictions`（外部回答 JSON）、`--output`（JSON） |

## 框架与协议 · 10–11

先安装可选依赖：`python -m pip install -e ".[all]"`；也可分别安装 `.[graph]` 或 `.[mcp]`。

| 章节与入口 | 模型 API | 可用参数 |
| --- | --- | --- |
| [10 LangGraph](../docs/learning/langgraph.md)：`python -m examples.langgraph_workflow` | 默认不调用；`--live` 调用 | `--question`、`--provider`；`--loop` 切换天气循环，配合 `--max-steps`；`--checkpoint` 仅用于三步问答图，与 `--loop` 互斥 |
| [11 MCP](../docs/learning/mcp.md)：`python -m examples.mcp_demo` | 默认不调用；`--live` 调用 | 默认模式用 `--city`、`--query`；模型模式用 `--question`、`--max-calls`、`--provider` |

默认模式执行 LangGraph 或本地 MCP 会话，天气数据仍为模拟数据。保存完整模型请求与响应可用 `python scripts/record_live.py mcp --output-dir outputs/my-live-run`；该记录命令调用 API。

## 综合实战 · 12 医疗险资料比较

[第 12 章](../docs/insurance/course-guide.md) 解释业务输入、取证与比较报告；[项目说明](../docs/insurance/README.md) 介绍本地使用流程。下列入口使用同一份需求和证据规则。

| 用途 | 命令 | 模型 API 与输出 |
| --- | --- | --- |
| Python 对照 | `python -m examples.insurance_compare` | 默认不调用；`--live` 调用；`--output` 导出 JSON，不创建会话 |
| LangGraph 对照 | `python -m examples.insurance_compare --engine langgraph` | 默认不调用；`--live` 调用；需 `.[graph]` |
| MCP 对照 | `python -m examples.insurance_compare --engine mcp` | 默认不调用；`--live` 调用；需 `.[mcp]` |
| 本地网页 | `python -m agent_learning.insurance.web` | 默认不调用；页面中明确启用模型辅助才调用；保存会话，可下载 JSON |
| 创建会话 | `python -m agent_learning.insurance compare --request examples/insurance_request.json --output outputs/insurance-report.md` | 默认不调用；`--live` 调用；保存会话，导出 Markdown |
| 查看报告 | `python -m agent_learning.insurance show SESSION_ID` | 不调用；读取已保存结果 |
| 补充后重跑 | `python -m agent_learning.insurance resume SESSION_ID --request examples/insurance_request.json` | 默认不调用；`--live` 调用；更新原会话 |

将 `SESSION_ID` 替换为创建时返回的编号。示例默认读取自拟教学目录；官方节选使用 `--catalog official --request examples/insurance_official_request.json`。`--catalog` 用于 `examples.insurance_compare` 或 CLI 的 `compare`；`resume` 沿用原会话目录。

三种对照入口以及 `compare` / `resume` 均可用 `--max-calls` 限制模型请求。网页用 `--port` 指定端口；网页和会话 CLI 用 `--sessions` 指定保存目录。医疗险入口使用环境配置中选择的模型服务，没有独立 `--provider` 参数。

## 检查入口

```bash
python -m unittest discover -s tests -v
python scripts/check_docs.py
python scripts/check_examples.py
# 安装可选依赖后执行
python scripts/check_examples.py --integrations
```

这些检查不调用付费模型。缺少可选依赖时，相应单元测试跳过；`--integrations` 要求依赖已安装并运行集成例子。预算耗尽实验的退出码可能为 1，应结合该例的输出状态判断。
