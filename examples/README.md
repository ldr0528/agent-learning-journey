# 能力示例

先按根目录 README 安装项目，在仓库根目录使用 `python -m examples.<名称>` 运行。

| 示例 | 目的 | 入口 |
| --- | --- | --- |
| 单次模型调用 | 看清 system、user 与一次响应 | `python -m examples.model_call` |
| 工具执行 | 手动给定 Action，Python 解析并执行模拟天气函数 | `python -m examples.tool_execution` |
| 工具结果回传 | 模型请求 → 执行 → Observation → 模型回答 | `python -m examples.tool_roundtrip --city 上海` |
| 有限循环 | 分别查询两个城市，再比较；最多 5 次模型请求 | `python -m examples.weather_loop` |

`model_call --check` 只检查配置。工具执行示例不读取密钥、不联网；其他示例会产生模型 API 用量。

天气只有北京与上海的模拟数据，查询广州应得到无数据答复。可用 `python -m examples.weather_loop --max-steps 2` 观察预算不足导致的未完成状态。

示例依次复用 `agent_learning` 中的配置、请求、工具与循环，不依赖私人学习目录。主项目使用 `python -m agent_learning`。
