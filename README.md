<div align="center">

# Agent Learning Journey

**从一次模型调用，到一个能检索、引用和停止的研究助手。**

[快速开始](#快速开始) · [运行示例](#运行示例) · [架构说明](docs/architecture.md) · [教材与路线](docs/roadmap.md) · [评估](docs/evaluation.md)

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Status](https://img.shields.io/badge/状态-实验原型-0F766E)
[![Tests](https://github.com/ldr0528/agent-learning-journey/actions/workflows/tests.yml/badge.svg)](https://github.com/ldr0528/agent-learning-journey/actions/workflows/tests.yml)

</div>

以 [Datawhale Hello-Agents](https://github.com/datawhalechina/hello-agents) 为主要学习材料的 Python 实践项目。先看清模型、工具和程序各自做什么，再逐步加入状态管理、规划与框架。

当前主项目是一个命令行研究助手：它从三条带出处的本地教学摘要中检索资料，把结果传回模型，生成带编号的简答。代码保留完整执行轨迹，方便阅读和调试；这是可运行的教学原型，尚不具备通用网页研究能力。

![研究助手的工具循环与来源校验](docs/assets/agent-loop-zh.svg)

*本项目根据实际代码原创绘制的中文流程图。模型提出行动，程序执行工具并管理停止条件。*

## 已实现

- **模型接入**：统一读取环境配置，区分千问与 OpenAI 的密钥及请求选项。
- **有限工具循环**：Action → 执行 → Observation → 再决策；支持 Finish、请求上限和错误反馈。
- **本地资料检索**：按关键词标签匹配摘要，保留资料编号、性质、教材小节与链接。
- **来源检查**：拒绝未检索到的引用编号，提示修正最终答案内的引用；来源链接由程序输出。
- **可检查的行为**：拒绝重复执行相同检索；无资料时允许说明不足；预算用尽时明确报告未完成。
- **分层示例与离线测试**：从单次调用到完整循环，核心逻辑可以在没有 API Key 时测试。

千问 `qwen-plus` 已真实验证。OpenAI 兼容配置保留，但尚未取得成功运行证据；模型可用性与参数支持以所用服务为准。

## 快速开始

要求 Python 3.10 或更高版本。以下命令从仓库根目录执行。

```bash
git clone https://github.com/ldr0528/agent-learning-journey.git
cd agent-learning-journey
python -m venv .venv
```

激活环境并安装：

```powershell
# Windows PowerShell
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
Copy-Item .env.example .env
```

```bash
# macOS / Linux
source .venv/bin/activate
python -m pip install -e .
cp .env.example .env
```

已有 `.env` 时不要覆盖。打开本地 `.env`，填写千问配置：

```dotenv
LLM_PROVIDER="qwen"
DASHSCOPE_API_KEY="YOUR-API-KEY"
QWEN_MODEL_ID="qwen-plus"
QWEN_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
```

这个地址用于百炼北京地域的普通 API Key。其他地域或产品需要使用相应的官方地址。配置从当前运行目录的 `.env` 读取，系统环境变量优先；请勿提交真实密钥。

```bash
# 只检查配置，不请求模型
python -m agent_learning --check

# 运行研究助手，会产生模型 API 用量
python -m agent_learning --question "Agent Loop 为什么要有最大步数？"
```

也可以使用安装后的等价入口：

```bash
agent-research --question "Action 和 Observation 分别由谁产生？"
```

如需 OpenAI，填写模板中的 `LLM_API_KEY`、`LLM_MODEL_ID`、`LLM_BASE_URL`，运行时加 `--provider openai`。不要混用两家服务的密钥。

## 运行示例

正常流程的节选如下，省略了 Observation 中的完整摘要。实际模型措辞与轮数可能变化。

```text
[第 1 轮] Action: search_notes(query="Agent Loop 最大步数")
Observation: [N01] Agent Loop 的基本过程
             [N03] Finish 与最大步数

[第 2 轮] Action: Finish[最大步数限制执行预算，防止持续运行和资源耗尽。[N03]]
模型请求 2 次；工具执行 1 次。

引用来源（本地教学摘要，非教材原文）：
[N03] Hello-Agents 第四章 §4.2.3；未完成状态说明为本项目的教学扩展
```

各个示例分别展示一种机制，说明见 [examples/README.md](examples/README.md)。

| 命令 | 观察什么 | 调用模型 |
| --- | --- | --- |
| `python -m examples.model_call` | system / user 与单次回复 | 是 |
| `python -m examples.tool_execution` | 解析手动指定的 Action，执行模拟天气函数 | 否 |
| `python -m examples.tool_roundtrip --city 上海` | 工具结果进入下一次模型请求 | 是，最多两次 |
| `python -m examples.weather_loop` | 查询两个城市后比较，观察多轮决策 | 是 |
| `python -m agent_learning.tools.notes --query "最大步数"` | 只看本地检索结果与出处 | 否 |

给研究助手加 `--max-steps 1`，可观察“拿到资料但来不及形成有效最终答案”的情况。程序返回退出码 `1` 是该实验预期的未完成状态。天气示例始终使用模拟数据。

## 项目结构

```text
src/agent_learning/
├── config.py              # 服务配置与客户端创建
├── llm.py                 # 单次模型请求
├── loop.py                # 通用循环、预算与停止条件
├── cli.py                 # 研究助手命令行入口
├── agents/
│   ├── research.py        # 检索问答与引用检查
│   └── weather.py         # 模拟天气任务
├── tools/
│   ├── notes.py           # 本地标签检索
│   └── weather.py         # 模拟天气函数
└── data/notes.json        # 带出处的教学摘要
examples/                  # 可独立运行的能力示例
tests/                     # 离线控制逻辑测试
docs/                      # 架构、教材映射、评估、中文图
```

## 测试与评估

```bash
python -m unittest discover -s tests -v
```

离线测试不请求模型、不需要密钥，覆盖上下文回传、步数限制、格式纠错、引用范围、重复查询和配置隔离。GitHub Actions 在 Linux、Windows 上执行检查。

另有 [六个固定任务与验收标准](docs/evaluation.md)，分别检查答案依据、引用、流程和调用次数。真实模型结果与离线测试是两类证据；少量成功样例不构成普遍可靠率结论。

## 当前边界

- 使用提示词和正则解析的文字协议，尚未使用 API 原生 Function Calling。
- 资料只有三条教学摘要；关键词命中不代表语义相关，没有命中也不代表教材没有写。
- 引用检查验证编号是否来自本次检索，不能自动证明每个结论得到支持。
- `finished` 表示流程接受了最终答复，可能是“资料不足”；`step_limit` 表示没有取得有效最终答复。
- 尚未实现网页搜索、向量检索、持久化记忆、LangGraph、Plan-and-Solve 或 Reflection。

## 后续方向

按能力推进：模型与工具基础 → 状态与上下文 → 规划与反思 → 检索与评估 → LangGraph → MCP。教材映射与范围取舍见 [路线说明](docs/roadmap.md)。完成基础循环不等于已经学完 Hello-Agents 第四章。

欢迎提出可复现的问题或小范围改进，参见 [贡献说明](CONTRIBUTING.md)。

## 参考与许可

- 核心学习材料：[Hello-Agents](https://github.com/datawhalechina/hello-agents)。教学摘要逐条保留出处，采用其 **CC BY-NC-SA 4.0** 许可。
- 仓库组织参考：[smolagents](https://github.com/huggingface/smolagents) 的源码、示例与测试分层，以及 [LangGraph](https://github.com/langchain-ai/langgraph) 的功能、快速开始和文档导航方式。本项目没有复制其图片或实现。
- 本项目原创代码与中文流程图沿用仓库的 [MIT License](LICENSE)。教材衍生资料单独标注，不因放入本仓库而改为 MIT；详见 [NOTICE.md](NOTICE.md)。
