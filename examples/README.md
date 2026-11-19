# 配套示例索引

[手册目录](../README.md#章节目录) · [环境配置](../docs/getting-started.md) · [课程验收](../docs/course-map.md)

正文已直接展示代码、结果与分析；这里集中列出可运行入口。所有命令从仓库根目录执行，先激活虚拟环境。默认是否请求模型因教学目的而异，下表明确标注。

新增章节已有 [真实千问实验集](../docs/runs/README.md)，可先看每次输入、响应和结果分析，再复现对应命令。

## 无需模型 API 的核心示例

| 对应章节 | 命令 | 实际执行什么 |
| --- | --- | --- |
| [02 工具回传](../docs/learning/tool-feedback.md) | `python -m examples.tool_execution` | Python 模拟天气工具 |
| [04 检索引用](../docs/learning/retrieval-and-citations.md) | `python -m agent_learning.tools.notes --query "最大步数"` | 基础三条摘要的标签匹配 |
| [05 上下文](../docs/learning/state-and-context.md) | `python -m examples.context_preview` | 三种上下文构造与实际本地工具 |
| [06 规划器](../docs/learning/planning.md) | `python -m examples.plan_first --demo` | 解析固定示意计划 |
| [06 计划执行](../docs/learning/planning.md) | `python -m examples.plan_solve --demo` | 固定模型回复驱动完整计划执行 |
| [07 评审修订](../docs/learning/reflection.md) | `python -m examples.reflection --demo` | 固定草稿、反馈与修订驱动有限流程 |
| [08 RAG](../docs/learning/rag.md) | `python -m examples.rag_research` | 真实本地检索与证据摘录报告 |
| [09 评估](../docs/learning/evaluation.md) | `python -m examples.evaluate` | 固定开发题上的实际检索指标 |

固定回复演示会显示适配器调用次数，但真实 API 次数为 0。RAG 默认的 `evidence_only` 是证据摘录，不是模型生成的研究结论。

## 真实模型入口

这些命令需要本地配置，会产生服务商 API 用量。可以继续使用千问，配置见 [环境说明](../docs/getting-started.md)。

| 主题 | 命令 | 观察重点 |
| --- | --- | --- |
| 单次模型调用 | `python -m examples.model_call` | 输入消息与回答文本 |
| 工具回传 | `python -m examples.tool_roundtrip --city 上海` | 工具结果进入第二次请求 |
| 有限循环 | `python -m examples.weather_loop --max-steps 3` | 请求、工具与 Finish 分别计数 |
| 基础研究助手 | `python -m agent_learning --question "Agent Loop 为什么要有最大步数？"` | 检索、引用与来源范围 |
| 只生成计划 | `python -m examples.plan_first` | 一次调用返回整个计划 |
| 计划后执行 | `python -m examples.plan_solve` | 前序结果成为后续输入 |
| 评审并修订 | `python -m examples.reflection` | 评审结构、修订预算、停止状态 |
| RAG 报告 | `python -m examples.rag_research --live` | 证据支持、逐条引用、资料不足 |
| LangGraph + 模型 | `python -m examples.langgraph_workflow --live --checkpoint` | 节点如何组织两次实际请求 |
| MCP + 模型 | `python -m examples.mcp_demo --live` | 工具发现、原生tool_calls与结果回传 |

`python -m examples.model_call --check` 或 `python -m agent_learning --check` 只检查配置字段，不验证权限或额度，也不请求模型。`agent-research` 与基础研究助手入口等价。

## 状态与上下文：预算提示对照

固定问题与模型，仅切换预算提示：

```bash
python -m examples.weather_loop --max-steps 2
python -m examples.weather_loop --max-steps 2 --budget-context
python -m examples.weather_loop --max-steps 3 --budget-context
```

学习者提供的前两次运行均在查询两地后达到上限；第三次增加请求次数后输出 Finish。因为执行预算改变，不能把成功归因于提示。完整分析见 [第 05 章](../docs/learning/state-and-context.md)。

## 状态与上下文：摘要接回循环

保持问题、模型、预算开关和上限一致，只切换历史模式：

```bash
python -m examples.weather_loop --max-steps 3 --budget-context --context-mode full
python -m examples.weather_loop --max-steps 3 --budget-context --context-mode summary
```

已有真实对照均为 3 次模型请求、2 次工具执行。摘要在第三次请求前由程序生成，保留较早结果和来源；不增加摘要模型调用。消息数减少不代表 token 一定减少，也不是成功率改善的证据。

## 先规划，再执行：规划器

先用 `plan_first` 看计划，再用 `plan_solve` 跟踪整个执行过程。教材示例数据相同，输出不必有完全相同的措辞或条目数。格式检查不等于语义正确；执行完成也需要核对中间结果。

预算边界可用以下离线命令检查，它们预期退出码为 1：

```bash
python -m examples.plan_solve --demo --max-calls 2
python -m examples.reflection --demo --max-calls 3
python -m examples.reflection --demo --max-revisions 0
```

逐步解释见 [第 06 章](../docs/learning/planning.md) 与 [第 07 章](../docs/learning/reflection.md)。

## 研究与评估报告

```bash
python -m examples.rag_research --question "RAG 为什么要保留来源？" --output outputs/research-report.md
python -m examples.evaluate --k 3 --output outputs/retrieval-evaluation.json
```

报告保存问题、模式、检索轨迹、证据或回答及来源。评估保留语料指纹、逐题结果和失败案例；实际开发集并非独立测试集。对外部回答做引用检查使用 `--predictions`，输入结构见 [评估章](../docs/learning/evaluation.md)。

## 真实框架与协议集成

先安装 `python -m pip install -e ".[all]"`。以下默认模式不调用模型，但确实执行第三方框架或本地 MCP 会话：

```bash
python -m examples.langgraph_workflow
python -m examples.langgraph_workflow --checkpoint
python -m examples.langgraph_workflow --loop
python -m examples.mcp_demo
```

图示例为理解、检索、回答三步；`--loop` 演示天气条件循环，`--checkpoint` 演示进程内状态快照。LangGraph和MCP示例添加 `--live` 才使用真实模型。MCP默认只验证协议；`--live` 会让模型依据发现的工具定义选择调用，程序执行并回传。天气仍来自本地模拟数据。

若需要保存完整请求与响应，可显式运行 `python scripts/record_live.py mcp --output-dir outputs/my-live-run`。该记录命令使用真实API，目标已存在时拒绝覆盖；公开结果前需检查输入是否适合公开。

## 统一检查

```bash
python -m unittest discover -s tests -v
python scripts/check_docs.py
python scripts/check_examples.py
# 已安装可选依赖后
python scripts/check_examples.py --integrations
```

检查仅使用公开教学数据与离线模式，不读取真实密钥。缺少可选依赖时，相关单元测试会显示跳过；集成检查要求依赖已安装，并实际运行例子。
