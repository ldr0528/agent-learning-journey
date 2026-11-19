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

01–09 章和第 12 章的 Python、网页入口使用基础安装即可。第 10、11 章以及第 12 章的框架与协议对照需要可选依赖，可分别安装或一次装齐：

```bash
python -m pip install -e ".[graph]"
python -m pip install -e ".[mcp]"
# 或一次安装两项
python -m pip install -e ".[all]"
```

课程使用 LangGraph 1.2.23 与 MCP Python SDK 1.30.0。集成示例建议使用 Python 3.12，核心示例兼容 Python 3.10+。未安装可选库时，相关测试会跳过。

## 配置模型

打开本地 `.env`，填写千问配置：

```dotenv
LLM_PROVIDER="qwen"
DASHSCOPE_API_KEY="YOUR-API-KEY"
QWEN_MODEL_ID="qwen4-max"
QWEN_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
```

该地址用于百炼北京地域的普通 API Key。其他地域或产品应使用对应的官方地址。配置从当前运行目录的 `.env` 读取，系统环境变量优先。真实密钥只保留在本地，提交时使用 [配置模板](../.env.example)。

```bash
# 只检查必填配置，不验证服务权限或额度，不请求模型
python -m agent_learning --check
```

默认模型为 `qwen4-max`，已验证工具请求、MCP调用与结果回传。该模型于2026-11-16上线，支持北京地域；版本与能力见 [官方说明](https://help.aliyun.com/zh/model-studio/qwen4-max)。示例设置 `reasoning_effort="none"`、`max_tokens=512`，便于观察简短的消息与控制流程。更换模型时请核对其参数支持情况。

早期实验使用 `qwen-plus`，各条 [运行记录](runs/README.md) 保留当时的模型和参数。若使用 OpenAI，填写 `LLM_API_KEY`、`LLM_MODEL_ID`、`LLM_BASE_URL`，并将 `LLM_PROVIDER` 设置为 `openai`。支持 `--provider` 的章节脚本还可在单次运行时传入 `--provider openai`；医疗险网页和 CLI 统一读取 `LLM_PROVIDER`，不接受该命令行参数。

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

前两项使用固定回复检查控制流程；研究报告默认摘录检索结果，评估按固定题计算指标。安装可选依赖后，可运行框架与协议示例：

```bash
python -m examples.langgraph_workflow
python -m examples.mcp_demo
```

这些默认模式不请求付费模型，MCP 仅启动本地服务端子进程并在会话结束时关闭。

连接模型使用 `python -m examples.langgraph_workflow --live --checkpoint` 或 `python -m examples.mcp_demo --live`。MCP模型示例默认最多4次模型请求；它与纯协议验证共享服务端。

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

## 医疗险比较工作区

完成基础安装后，运行 `python -m agent_learning.insurance.web`，打开终端显示的本地地址。默认按固定流程整理资料；开启页面中的模型辅助选项后才使用上述模型配置。

业务输入、比较结果和练习见 [医疗险 Agent](insurance/README.md)。需要对照 LangGraph 或 MCP 时，再安装可选依赖并按 [示例索引](../examples/README.md) 操作。

## 运行离线检查

```bash
python -m unittest discover -s tests -v
python scripts/check_docs.py
python scripts/check_examples.py
```

测试使用固定的模拟模型回复，不读取真实密钥、不请求 API。它检查程序是否正确回传结果、执行预算、校验引用和隔离任务。真实模型表现另按 [评估标准](evaluation.md) 人工核对。

前端状态回归使用 Node.js 内置模块，不需要安装 npm 包。机器上有 Node.js 时，上述单元测试会一并检查提交重试、草稿隔离和报告切换；没有时仅跳过这组前端检查，应用本身仍只需 Python。也可单独运行 `node tests/ui/insurance-state-checks.cjs`。

模型请求失败时，检查当前服务的配置、模型权限和额度。报告问题只提供命令、版本、服务与模型名以及脱敏错误，无需提供密钥或 `.env` 文件。
