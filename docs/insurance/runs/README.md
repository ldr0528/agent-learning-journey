# 医疗险比较实验记录

[保险项目](../README.md) · [案例解析](../course-guide.md)

本页保存公开案例的请求、工具响应和报告。问题和需求档案来自仓库中的示例文件，不包含个人投保记录。

| 案例 | 输入 | 结束状态 | 模型请求 / 工具操作 | 输出与记录 |
| --- | --- | --- | --- | --- |
| 普通门诊与续保 | [自拟案例需求](../../../examples/insurance_request.json) | `completed_with_gaps` | 3 / 3 | [报告 JSON](report-demo.json) · [调用记录](insurance-demo.md) · [原始记录 JSON](insurance-demo.json) |
| 等待期与续保 | [官方节选需求](../../../examples/insurance_official_request.json) | `completed_with_gaps` | 5 / 5 | [报告 JSON](report-official.json) · [调用记录](insurance-official.md) · [紧凑记录 JSON](insurance-official.json) |

工具操作包括最终的 `finish_comparison` 校验，不仅是读取资料。两个报告均为九个维度、十八条证据；单元内容由程序从目录事实生成。官方案例多出的两次查询仍在既有节选中检索，没有补齐目录之外的信息。

两组共 8 次模型请求，服务商报告 39,338 token。模型、时间、参数及源码指纹保存在记录中。官方案例省略重复的条款请求正文，保留消息哈希、证据编号及原始工具决策；资料与结果分别见目录和报告。后续展示层改动不回写历史输出。

这些案例说明取证、覆盖检查与缺口输出可以连通，不构成产品推荐效果或回答准确率的统计。控制流程与数据隔离的回归检查见 [业务测试](../../../tests/test_insurance_workflow.py)、[目录测试](../../../tests/test_insurance_catalog.py) 和 [网页测试](../../../tests/test_insurance_web.py)。

2026-11-19 的本地工程验收通过项目完整测试 117 项、离线示例入口 16 个，以及课程链接和代码片段检查。浏览器核对覆盖比较生成、会话恢复、证据跳转与宽窄窗口布局；这些检查验证软件流程，不代替对保险资料完整性与适用性的审核。
