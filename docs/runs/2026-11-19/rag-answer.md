# 真实运行：rag-answer

- 开始时间（UTC）：2026-11-19T10:47:49.091918+00:00
- 服务：qwen；请求模型：['qwen-plus']
- API 尝试：1；成功返回：1；退出码：0
- 服务商报告 token：995；未返回用量的调用：0
- 源码基准提交：`c369aae66043d059d7b53fb902e58c8ec7c6bfc9`；执行时源码有未提交改动：`True`
- 完整请求、响应与源码文件指纹见同名 JSON；工具数据为本地教学资料或模拟天气。
- Markdown 展示仅去除行尾空格和文件末尾空行；JSON 保留原始文本。

## 复现命令

```bash
python -m examples.rag_research --live --provider qwen --question "RAG 为什么要保留来源与引用？"
```

## 程序输出

```text
# 课程研究报告

问题：RAG 为什么要保留来源与引用？

模式：真实模型模式；状态：answered；模型请求：1 次。

## 检索轨迹

| 资料块 | 标题 | BM25 分数 | 纳入证据 |
| --- | --- | ---: | --- |
| D08-C01 | RAG 的来源与引用 | 9.823 | 是 |
| D05-C01 | RAG 的检索增强生成流程 | 6.664 | 是 |
| D04-C01 | 摘要保留较早证据 | 6.133 | 是 |

## 内容

- RAG 保留来源与引用是为了确保生成的回答仅基于实际纳入上下文的证据，并支持读者核查依据是否真实支持结论。 [D08-C01]
- 保留来源是 RAG 数据准备阶段的关键步骤，与文档收集、切分和索引构建共同构成检索增强的基础流程。 [D05-C01]
- 摘要或上下文整理过程中仍需保留来源信息，以防止关键事实（如城市、温度）及其出处在信息压缩时丢失。 [D04-C01]

## 来源

- [D08-C01] Hello-Agents 第八章 §8.3；教学摘要与本项目说明，非教材原文。 [教材链接](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter8/第八章%20记忆与检索.md)
- [D05-C01] Hello-Agents 第八章 §8.3；教学摘要与本项目说明，非教材原文。 [教材链接](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter8/第八章%20记忆与检索.md)
- [D04-C01] Hello-Agents 第九章 §9.1–9.2；教学摘要与本项目说明，非教材原文。 [教材链接](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter9/第九章%20上下文工程.md)

引用编号合法不代表论据足以支持结论；需要人工核对语义。
知识库 SHA-256：`7cace095e0e475b61713cb67134bc9155d15740573db895825c9a342297e1516`
```

## 逐次模型响应

### 请求 1

结束原因：`stop`；响应模型：`qwen-plus`。

````text
{"status":"answered","claims":[{"text":"RAG 保留来源与引用是为了确保生成的回答仅基于实际纳入上下文的证据，并支持读者核查依据是否真实支持结论。","citations":["D08-C01"]},{"text":"保留来源是 RAG 数据准备阶段的关键步骤，与文档收集、切分和索引构建共同构成检索增强的基础流程。","citations":["D05-C01"]},{"text":"摘要或上下文整理过程中仍需保留来源信息，以防止关键事实（如城市、温度）及其出处在信息压缩时丢失。","citations":["D04-C01"]}],"missing":""}
````
