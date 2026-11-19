# 来源与许可范围

本仓库包含原创实现与单独标注的教学材料，两者的许可范围不同。

| 内容 | 来源 | 许可与说明 |
| --- | --- | --- |
| 原创 Python 实现、测试与工程说明 | 本项目 | 根目录 MIT License，保留原仓库版权声明 |
| `docs/assets/` 下的中文 SVG 图 | 根据本项目执行过程与学习路线原创绘制 | MIT；没有复制或描摹第三方图片 |
| `src/agent_learning/data/notes.json` | 根据 Datawhale Hello-Agents 第一章与第四章整理的教学摘要 | CC BY-NC-SA 4.0；非教材原文，保留作者、章节与链接 |
| `src/agent_learning/data/corpus.json` 与 `eval_cases.json` | 按课程内容原创转述的资料摘要及开发评估题 | CC BY-NC-SA 4.0；不是教材全文或官方测试集，资料保留来源，评估题仅衡量当前语料与规则 |
| `docs/learning/` 下的手册正文 | 以 Hello-Agents 为主要参考，按自己的计划结合本项目代码与实验重新编排 | CC BY-NC-SA 4.0；各章标注教材出处、教学简化和项目扩展，非教材原文 |
| `docs/runs/` 下的教学实验记录与分析 | 实际模型请求、响应、引用的本地教学摘要及本项目判读 | CC BY-NC-SA 4.0；包含教材衍生摘要，不代表教材作者对模型输出作出背书 |
| `insurance_demo.json` | 本项目自拟的九维教学条款 | MIT；非销售产品，也不是完整保险合同 |
| `insurance_official.json` | 官方公开资料的少量自行概括、定位及链接 | 原来源的权利保留；不将保险机构条款重新授权为 MIT，不表示在售或得到保险机构背书 |
| `docs/insurance/` 的课程讲解与分析 | 结合 Hello-Agents 和本项目保险案例编排 | CC BY-NC-SA 4.0；第三方资料仍按原来源权利使用 |

## Hello-Agents

作者与来源：Datawhale 社区，[Hello-Agents 仓库](https://github.com/datawhalechina/hello-agents)。

教材原许可：[LICENSE.txt](https://github.com/datawhalechina/hello-agents/blob/main/LICENSE.txt)，副本见 [LICENSES/CC-BY-NC-SA-4.0.txt](LICENSES/CC-BY-NC-SA-4.0.txt)。摘要的改动包括压缩转述、增加检索标签及资料编号；N03 的未完成状态判定已明确标注为本项目教学扩展。

摘要、手册正文及其修改仍按 CC BY-NC-SA 4.0 使用，不能因根目录存在 MIT License 而将这部分材料重新标为 MIT。正文中的实验说明来自本项目实践，不意味着这些实验由教材作者提供或验证。图示根据本项目消息结构、工具实现和已有轨迹重新设计，未使用教材图片作为底图或描摹模板。

LangGraph 与 MCP 示例调用各自官方 Python 包，并按使用版本提供链接和说明；不将第三方包源码并入本仓库。依赖的许可证以对应包为准。本手册没有声称由 Datawhale、LangChain 或 MCP 项目背书。

## 仓库呈现参考

参考 [smolagents](https://github.com/huggingface/smolagents) 的源码、示例与测试分层，及 [LangGraph](https://github.com/langchain-ai/langgraph) 的功能说明与文档导航。不复制这两个项目的代码、图像或标识，不表示与其存在隶属或背书关系。

课程阅读组织还参考 Microsoft AI Agents for Beginners 与 Hugging Face Agents Course。具体页面、观察到的教学方法及本仓库的对应改进见 [参考资料与阅读设计](docs/references.md)。本轮图示为根据自己的实际消息与结果重新绘制的SVG。

## 图示的视觉参考

图示布局参考 [D2 的时序图文档](https://d2lang.com/tour/sequence-diagrams/) 中的参与者、生命线与消息组织，以及 [LangGraph 的工作流文档](https://docs.langchain.com/oss/python/langgraph/workflows-agents) 中用节点和连线解释关系的方式。采用本项目独立设计的白底、细线、少量配色样式，结构、中文标注和案例均按本项目代码重新绘制，未复制参考图片或标识。

图示的统一配色、字体层级和维护约定见 [图示规范](docs/assets/README.md)。
