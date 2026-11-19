# 产品资料的整理与核对

[保险项目](README.md) · [业务契约](requirements.md) · [来源参考](references.md)

比较结果能否使用，首先取决于目录中的事实是否准确。首版采用人工核对的条款事实，将产品、资料快照、比较维度、条件和出处一起保存。模型负责选择读取操作，不能修改目录中的保障事实。

## 两种资料性质

| 目录 | 内容 | 使用方式 |
| --- | --- | --- |
| [insurance_demo.json](../../src/agent_learning/data/insurance_demo.json) | 三个自拟方案，各九维条款 | 学习普通门诊、免赔、医院、续保等条件怎样影响比较 |
| [insurance_official.json](../../src/agent_learning/data/insurance_official.json) | 平安、太保、众安官方公开资料的少量概括 | 检查原文定位与未知项，不推断完整产品特性或在售状态 |

`synthetic` 表示自拟案例，`official_excerpt` 表示官方资料节选。即使同名产品，在不同年度、计划、附加责任下也可能不同，应分成不同目录版本，不能拼接成一个不存在的组合。

## 一个比较单元必须保留什么

| 字段 | 要求 |
| --- | --- |
| `product_id`、`version` | 唯一确定比较对象；资料快照不能伪装成合同生效版本 |
| `evidence_id`、`dimension` | 每条事实有唯一编号，归属于一个比较维度 |
| `text`、`conditions` | 同时记录主要内容、责任范围、例外和前提；不能只截取金额或百分比 |
| `status` | `known` 有记录依据；`unknown` 当前资料缺少信息；`conflict` 存在已标记的资料冲突 |
| `locator` | 标注条款章节或网页位置；未核实的页码不填写 |
| `source` | 来源标题、官方链接、核对日期、生效日期及资料性质；未知生效日期为 `null` |

`known` 只说明目录有依据，不表示承保、赔付或预算匹配成立。`unknown` 不能转成“不保”。`conflict` 由资料维护者标记，当前程序不自动发现所有语义矛盾。

每个产品都列出九个维度。缺少健康告知问卷、计划表或报价时，给相应维度写明缺失，并保留 `unknown`。宣传页的起价不能作为特定投保人的报价；保证续保也不能被缩写成保费固定。

## 纳入新资料的过程

1. 确认官方来源、文件标题、适用计划和版本；分别记录核对日期与资料明确给出的生效日期。
2. 按九个维度整理事实，连同例外、交叉引用和缺失附件一起标注。长合同中的事实需要回到原文核对。
3. 由另一轮审阅逐条检查数字、否定词、普通门诊与特殊门诊、责任共享范围和续保条件。
4. 使用 `Catalog(path)` 校验新 JSON，再在固定需求上检查比较表、缺口和引用。格式校验通过后仍需语义核对。
5. 公开资料只保存许可允许的内容、少量概括和来源，不提交用户的健康信息、保单、报价单或会话。

库接口允许维护者加载自建 JSON：

```python
from agent_learning.insurance.catalog import Catalog
from agent_learning.insurance.workflow import run_comparison

catalog = Catalog("outputs/reviewed-products.json")
# request 需明确选择这个目录中实际存在的产品与版本。
report = run_comparison(request, catalog=catalog)
```

本地网页目前只开放随项目提供的两个目录，没有文件上传或自动抽取功能。新资料进入网页前，需要先完成上述整理和核对，不能把模型抽取结果直接当成已核验的合同事实。
