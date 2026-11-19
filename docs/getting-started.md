# 配套代码：环境与运行说明

[返回章节目录](../README.md#章节目录) · [配套示例](../examples/README.md)

学习正文已经直接展示关键代码和已有结果。本页供希望亲自运行、修改实现的读者使用，集中放置环境、配置和命令；不需要完成本页才能开始阅读。配套代码要求 Python 3.10 或更高版本，以下命令从仓库根目录执行。

## 准备环境

```bash
git clone https://github.com/ldr0528/agent-learning-journey.git
cd agent-learning-journey
python -m venv .venv
```

根据系统选择一组命令。已有 `.env` 时保留现有文件，跳过复制步骤。

```powershell
# Windows PowerShell
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

```bash
# macOS / Linux
source .venv/bin/activate
python -m pip install -e .
if [ ! -f .env ]; then cp .env.example .env; fi
```

Windows 如果不方便激活环境，可以直接使用 `.\.venv\Scripts\python.exe` 替代后续命令中的 `python`。

## 可选框架与协议

01–09 章使用基础安装即可。第 10、11 章使用真实第三方库，可分别安装或一次装齐：

```bash
python -m pip install -e ".[graph]"
python -m pip install -e ".[mcp]"
# 或一次安装两项
python -m pip install -e ".[all]"
```

课程固定使用 LangGraph 1.2.23 与 MCP Python SDK 1.30.0；MCP 选用 1.x 接口，不声称它是最新主版本。集成示例建议使用 Python 3.12，核心示例兼容 Python 3.10+。基础环境没有可选库时，集成测试会明确跳过；安装后再运行对应例子和测试，才能验证实际协议与框架行为。

## 配置模型

打开本地 `.env`，填写千问配置：

```dotenv
LLM_PROVIDER="qwen"
DASHSCOPE_API_KEY="YOUR-API-KEY"
QWEN_MODEL_ID="qwen-plus"
QWEN_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
```

该地址用于百炼北京地域的普通 API Key。其他地域或产品应使用对应的官方地址。配置从当前运行目录的 `.env` 读取，系统环境变量优先。真实密钥只保留在本地，提交时使用 [配置模板](../.env.example)。

```bash
# 只检查必填配置，不验证服务权限或额度，不请求模型
python -m agent_learning --check
```

本项目已有千问 `qwen-plus` 的真实运行证据。OpenAI 配置入口保留，但尚未取得成功运行证据；如需使用，填写模板中的 `LLM_API_KEY`、`LLM_MODEL_ID`、`LLM_BASE_URL`，运行时加 `--provider openai`。模型与参数是否可用取决于所选服务。

## 先运行一个不调用模型的实验

```bash
python -m examples.tool_execution
python -m agent_learning.tools.notes --query "最大步数"
```

前者执行手动指定的天气 Action，后者只检索本地摘要。两者都不需要密钥、不请求模型。可以先观察 Python 工具能独立做什么，再加入模型决策。

后半程课程也提供无需 API Key 的完整演示：

```bash
python -m examples.plan_solve --demo
python -m examples.reflection --demo
python -m examples.rag_research --output outputs/research-report.md
python -m examples.evaluate --output outputs/retrieval-evaluation.json
```

前两项使用固定模型回复验证控制流程；研究报告默认摘录真实本地检索结果，评估运行真实检索。模式均在输出中标明。安装可选依赖后，还可运行真实框架与本地协议：

```bash
python -m examples.langgraph_workflow
python -m examples.mcp_demo
```

这些默认模式不请求付费模型，MCP 仅启动本地服务端子进程并在会话结束时关闭。

## 运行模型与完整循环

以下实验会产生模型 API 用量。每次先预测模型请求次数和工具执行次数，再对照输出。

```bash
python -m examples.model_call
python -m examples.tool_roundtrip --city 上海
python -m examples.weather_loop
python -m agent_learning --question "Agent Loop 为什么要有最大步数？"
```

安装后的 `agent-research` 与 `python -m agent_learning` 是等价入口。更多观察点见 [分层实验](../examples/README.md)。

规划与反思去掉 `--demo` 后使用真实模型；RAG 和 LangGraph 显式添加 `--live` 后才使用真实模型。完整模式对照见 [示例索引](../examples/README.md)，不要把演示中的固定回复当成服务商实测。

## 观察边界

```bash
# 两次模型请求可能只够查完两个城市，尚未得到最终答复
python -m examples.weather_loop --max-steps 2

# 工具中没有广州的模拟数据
python -m examples.tool_roundtrip --city 广州

# 本地三条摘要不够回答这个问题
python -m agent_learning --question "LangGraph 的 checkpoint 有什么作用？"

# 已拿到资料，但预算可能不够形成最终答复
python -m agent_learning --question "Agent Loop 为什么要有最大步数？" --max-steps 1
```

天气始终是模拟数据。达到请求上限且没有有效 Finish 时，程序报告未完成，退出码为 `1`；这是上限实验中的预期行为。有效的“资料不足”答复可以正常结束，但没有解决原始知识问题。

## 运行离线检查

```bash
python -m unittest discover -s tests -v
python scripts/check_docs.py
python scripts/check_examples.py
```

测试使用固定的模拟模型回复，不读取真实密钥、不请求 API。它检查程序是否正确回传结果、执行预算、校验引用和隔离任务。真实模型表现另按 [评估标准](evaluation.md) 人工核对。

模型请求失败时，检查当前服务的配置、模型权限和额度。报告问题只提供命令、版本、服务与模型名以及脱敏错误，无需提供密钥或 `.env` 文件。
