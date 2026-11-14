# 复现指南

[返回知识导航](../README.md#知识导航) · [选择一个实验](../examples/README.md)

本页集中放置环境、配置和命令。知识解释从首页的主题笔记进入。要求 Python 3.10 或更高版本，以下命令从仓库根目录执行。

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

## 运行模型与完整循环

以下实验会产生模型 API 用量。每次先预测模型请求次数和工具执行次数，再对照输出。

```bash
python -m examples.model_call
python -m examples.tool_roundtrip --city 上海
python -m examples.weather_loop
python -m agent_learning --question "Agent Loop 为什么要有最大步数？"
```

安装后的 `agent-research` 与 `python -m agent_learning` 是等价入口。更多观察点见 [分层实验](../examples/README.md)。

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
```

测试使用固定的模拟模型回复，不读取真实密钥、不请求 API。它检查程序是否正确回传结果、执行预算、校验引用和隔离任务。真实模型表现另按 [评估标准](evaluation.md) 人工核对。

模型请求失败时，检查当前服务的配置、模型权限和额度。报告问题只提供命令、版本、服务与模型名以及脱敏错误，无需提供密钥或 `.env` 文件。
