# 运行记录：insurance-demo

- 开始时间（UTC）：2026-11-19T12:47:05.955715+00:00
- 服务：qwen；请求模型：['qwen4-max']
- API 尝试：3；成功返回：3；退出码：0
- 服务商报告 token：9421；未返回用量的调用：0
- 源码基准提交：`1a982cf1c344a2de9b31ed9fba6225b399ad5c82`；执行时源码有未提交改动：`True`
- 完整请求、响应与源码文件指纹见同名 JSON；资料性质以各例的目录标记为准。
- Markdown 展示仅去除行尾空格和文件末尾空行；JSON 保留原始文本。

## 复现命令

```bash
python -m examples.insurance_compare --live --output outputs/insurance-demo-result.json
```

## 程序输出

```text
# 医疗险保障比较

问题：比较这两份医疗险资料。我关心普通门诊和续保安排，年度预算2000元；哪些差异有依据，哪些还需要确认？

状态：completed_with_gaps

## 保障范围

| 方案 | 资料内容 | 条件 | 依据 |
| --- | --- | --- | --- |
| 教学医疗计划A：住院基础 | 提供一般住院医疗、约定特殊门诊，以及与该次住院同因的住院前7日和出院后30日门急诊费用保障；上述责任共用200万元年度限额。普通门诊及体检不属于本计划保障。 | 特殊门诊仅指门诊肾透析、恶性肿瘤门诊治疗和器官移植后抗排异治疗。；费用须符合医院、等待期、责任除外等约定。 | [DEMO-HOSP-V1-COVERAGE] |
| 教学医疗计划B：门诊与住院 | 提供一般住院医疗及普通门急诊医疗。住院医疗年度限额为100万元，普通门急诊年度限额为1万元，两项限额分别计算。 | 普通门急诊不限于住院前后的就诊，但仍须满足医院和责任条件。；预防性体检、保健和美容不属于普通门诊医疗责任。 | [DEMO-OUT-V1-COVERAGE] |

## 续保安排

| 方案 | 资料内容 | 条件 | 依据 |
| --- | --- | --- | --- |
| 教学医疗计划A：住院基础 | 保险期间为1年，不保证续保。期满须重新申请，经审核同意后形成下一年度合同；产品停售时可能无法继续投保。 | 连续投保不等于终身保证续保。；下一年度保费需另行确认。 | [DEMO-HOSP-V1-RENEWAL] |
| 教学医疗计划B：门诊与住院 | 保险期间为1年，不保证续保。下一年度须重新申请并经审核，不能保证原有保障、费率或承保结果不变。 | 已有门诊或住院记录不能直接替代下一年度审核结论。 | [DEMO-OUT-V1-RENEWAL] |

## 免赔额

| 方案 | 资料内容 | 条件 | 依据 |
| --- | --- | --- | --- |
| 教学医疗计划A：住院基础 | 一般医疗责任共享每保险年度1万元免赔额，未使用部分不结转至下一年度。已由基本医保统筹或其他渠道补偿的费用不计入本计划免赔额。 | 只对本计划责任范围内、尚未得到补偿的费用累计免赔额。；住院、特殊门诊及住院前后门急诊不分别重复扣年度免赔额。 | [DEMO-HOSP-V1-DEDUCTIBLE] |
| 教学医疗计划B：门诊与住院 | 住院医疗按每保险年度5000元免赔额计算；普通门急诊按每次就诊100元免赔额计算，两类免赔额不合并或互相抵扣。 | 每次门急诊的未获补偿费用须先扣除该次免赔额。；不能把单次100元与年度5000元直接比较为同一种门槛。 | [DEMO-OUT-V1-DEDUCTIBLE] |

## 赔付比例

| 方案 | 资料内容 | 条件 | 依据 |
| --- | --- | --- | --- |
| 教学医疗计划A：住院基础 | 符合责任范围的费用先扣除其他补偿及剩余免赔额，再按100%赔付；以有基本医保身份投保但未按基本医保结算的，比例为60%。 | 比例适用于经过上述扣减后的费用，不是全部医疗发票金额。；赔付还受年度限额及其他条款限制。 | [DEMO-HOSP-V1-REIMBURSEMENT] |
| 教学医疗计划B：门诊与住院 | 扣除其他补偿和对应免赔额后，住院医疗按80%赔付，普通门急诊按70%赔付。 | 有基本医保的就诊应先办理医保结算。；两项比例分别适用，各自还受年度限额限制。 | [DEMO-OUT-V1-REIMBURSEMENT] |

## 医院范围

| 方案 | 资料内容 | 条件 | 依据 |
| --- | --- | --- | --- |
| 教学医疗计划A：住院基础 | 仅限中国内地二级及以上公立医院普通部。特需部、国际部、VIP病房和私立医院不在约定医院范围内。 | 急诊也不自动扩大约定医院范围。 | [DEMO-HOSP-V1-HOSPITAL] |
| 教学医疗计划B：门诊与住院 | 仅限中国内地二级及以上公立医院普通部，门急诊与住院采用相同医院范围。私立医院、特需部及国际部不在范围内。 | 提供普通门诊保障不等于所有诊所均可报销。 | [DEMO-OUT-V1-HOSPITAL] |

## 等待期

| 方案 | 资料内容 | 条件 | 依据 |
| --- | --- | --- | --- |
| 教学医疗计划A：住院基础 | 首次投保或中断后重新投保，疾病责任等待期为30日；因意外伤害就医及不间断续保不设等待期。 | 等待期从本次合同生效日起计算。；等待期内发生疾病所致费用按本条责任限制处理，不能仅根据报销申请日判断。 | [DEMO-HOSP-V1-WAITING-PERIOD] |
| 教学医疗计划B：门诊与住院 | 首次或中断后投保，住院疾病责任等待期为60日，普通门急诊疾病责任等待期为30日；意外伤害及不间断续保不设等待期。 | 等待期按责任分别判断，不能统一写成30日。 | [DEMO-OUT-V1-WAITING-PERIOD] |

## 责任除外

| 方案 | 资料内容 | 条件 | 依据 |
| --- | --- | --- | --- |
| 教学医疗计划A：住院基础 | 不承担未明确约定承保的既往症、非合理且必要的治疗、美容及体检费用，以及不符合医院范围的费用。 | 是否属于既往症需依据病历、发生时间和条款定义核实。；一项费用属于保障名称仍须同时满足本条及其他责任条件。 | [DEMO-HOSP-V1-EXCLUSIONS] |
| 教学医疗计划B：门诊与住院 | 不承担未明确承保的既往症、体检、牙齿矫正、美容、保健用品及不符合医疗必要性的费用。 | 普通门诊保障也受责任除外限制。；药店自行购药不在本计划普通门急诊责任内。 | [DEMO-OUT-V1-EXCLUSIONS] |

## 保费

| 方案 | 资料内容 | 条件 | 依据 |
| --- | --- | --- | --- |
| 教学医疗计划A：住院基础 | 本教学计划没有保费报价，不能据此判断是否符合用户预算或计算购买金额。 | 取得适用于年龄、医保身份及投保条件的报价后，才可比较保费。 | [DEMO-HOSP-V1-PREMIUM] |
| 教学医疗计划B：门诊与住院 | 本教学计划没有保费报价；门诊责任的存在不能用于推断保费金额或比其他计划贵多少。 | 预算匹配需补充适用于用户条件的报价。 | [DEMO-OUT-V1-PREMIUM] |

## 健康告知与核保

| 方案 | 资料内容 | 条件 | 依据 |
| --- | --- | --- | --- |
| 教学医疗计划A：住院基础 | 首次投保年龄为18至60周岁，须完成健康告知；涉及既往疾病、体检异常或持续治疗的申请需进一步核保。 | 年龄符合范围不代表必然承保。；不能仅凭疾病名称代替健康问卷和核保结论。 | [DEMO-HOSP-V1-UNDERWRITING] |
| 教学医疗计划B：门诊与住院 | 首次投保年龄为出生满30日至55周岁，须完成健康告知；未成年人由具备相应资格的投保人申请。 | 家庭成员应分别核对年龄与健康告知。；问卷或核保信息不足时不作确定承保判断。 | [DEMO-OUT-V1-UNDERWRITING] |

## 资料缺口与下一步

- 教学医疗计划A：住院基础 · 保费：本教学计划没有保费报价，不能据此判断是否符合用户预算或计算购买金额。
- 教学医疗计划B：门诊与住院 · 保费：本教学计划没有保费报价；门诊责任的存在不能用于推断保费金额或比其他计划贵多少。
- 年度预算已记录；本项目未取得针对该需求的有效报价，因此不判定任何产品是否符合预算。
- 向保险方核对完整条款、保障计划表、健康告知及当前投保规则。
- 取得适用于年龄、医保状态和所选计划的报价后，再核对年度预算。
- 健康告知与承保结果由保险方确认；本报告比较资料，不作承保判断。

## 资料来源

- [DEMO-HOSP-V1-COVERAGE] 教学医疗计划A：住院基础 / demo-v1 / 第1条 保障范围（自拟案例资料）
- [DEMO-HOSP-V1-DEDUCTIBLE] 教学医疗计划A：住院基础 / demo-v1 / 第2条 免赔额（自拟案例资料）
- [DEMO-HOSP-V1-REIMBURSEMENT] 教学医疗计划A：住院基础 / demo-v1 / 第3条 赔付比例（自拟案例资料）
- [DEMO-HOSP-V1-HOSPITAL] 教学医疗计划A：住院基础 / demo-v1 / 第4条 医院范围（自拟案例资料）
- [DEMO-HOSP-V1-WAITING-PERIOD] 教学医疗计划A：住院基础 / demo-v1 / 第5条 等待期（自拟案例资料）
- [DEMO-HOSP-V1-RENEWAL] 教学医疗计划A：住院基础 / demo-v1 / 第6条 续保安排（自拟案例资料）
- [DEMO-HOSP-V1-EXCLUSIONS] 教学医疗计划A：住院基础 / demo-v1 / 第7条 责任除外（自拟案例资料）
- [DEMO-HOSP-V1-PREMIUM] 教学医疗计划A：住院基础 / demo-v1 / 第8条 保费（自拟案例资料）
- [DEMO-HOSP-V1-UNDERWRITING] 教学医疗计划A：住院基础 / demo-v1 / 第9条 健康告知与核保（自拟案例资料）
- [DEMO-OUT-V1-COVERAGE] 教学医疗计划B：门诊与住院 / demo-v1 / 第1条 保障范围（自拟案例资料）
- [DEMO-OUT-V1-DEDUCTIBLE] 教学医疗计划B：门诊与住院 / demo-v1 / 第2条 免赔额（自拟案例资料）
- [DEMO-OUT-V1-REIMBURSEMENT] 教学医疗计划B：门诊与住院 / demo-v1 / 第3条 赔付比例（自拟案例资料）
- [DEMO-OUT-V1-HOSPITAL] 教学医疗计划B：门诊与住院 / demo-v1 / 第4条 医院范围（自拟案例资料）
- [DEMO-OUT-V1-WAITING-PERIOD] 教学医疗计划B：门诊与住院 / demo-v1 / 第5条 等待期（自拟案例资料）
- [DEMO-OUT-V1-RENEWAL] 教学医疗计划B：门诊与住院 / demo-v1 / 第6条 续保安排（自拟案例资料）
- [DEMO-OUT-V1-EXCLUSIONS] 教学医疗计划B：门诊与住院 / demo-v1 / 第7条 责任除外（自拟案例资料）
- [DEMO-OUT-V1-PREMIUM] 教学医疗计划B：门诊与住院 / demo-v1 / 第8条 保费（自拟案例资料）
- [DEMO-OUT-V1-UNDERWRITING] 教学医疗计划B：门诊与住院 / demo-v1 / 第9条 健康告知与核保（自拟案例资料）

模型请求：3；工具操作：3。
```

## 逐次模型响应

### 请求 1

结束原因：`tool_calls`；响应模型：`qwen4-max`。

```json
[
  {
    "id": "call_13f7da779d114370a27f1924",
    "function": {
      "arguments": "{\"product_id\": \"demo_hospital\", \"version\": \"demo-v1\", \"dimensions\": \n[\"coverage\", \"deductible\", \"reimbursement\", \"hospital\", \"waiting_period\", \"renewal\", \"exclusions\", \"premium\", \"underwriting\"]\n\n}",
      "name": "read_product_clauses"
    },
    "type": "function",
    "index": 0
  }
]
```

### 请求 2

结束原因：`tool_calls`；响应模型：`qwen4-max`。

```json
[
  {
    "id": "call_9eb6885d5dcc4a81aefbdda4",
    "function": {
      "arguments": "{\"product_id\": \"demo_outpatient\", \"version\": \"demo-v1\", \"dimensions\": \n[\"coverage\", \"deductible\", \"reimbursement\", \"hospital\", \"waiting_period\", \"renewal\", \"exclusions\", \"premium\", \"underwriting\"]\n\n}",
      "name": "read_product_clauses"
    },
    "type": "function",
    "index": 0
  }
]
```

### 请求 3

结束原因：`tool_calls`；响应模型：`qwen4-max`。

```json
[
  {
    "id": "call_012a526610af4cb1b1718066",
    "function": {
      "arguments": "{\"evidence_ids\": \n[\"DEMO-HOSP-V1-COVERAGE\", \"DEMO-HOSP-V1-DEDUCTIBLE\", \"DEMO-HOSP-V1-REIMBURSEMENT\", \"DEMO-HOSP-V1-HOSPITAL\", \"DEMO-HOSP-V1-WAITING-PERIOD\", \"DEMO-HOSP-V1-RENEWAL\", \"DEMO-HOSP-V1-EXCLUSIONS\", \"DEMO-HOSP-V1-PREMIUM\", \"DEMO-HOSP-V1-UNDERWRITING\", \"DEMO-OUT-V1-COVERAGE\", \"DEMO-OUT-V1-DEDUCTIBLE\", \"DEMO-OUT-V1-REIMBURSEMENT\", \"DEMO-OUT-V1-HOSPITAL\", \"DEMO-OUT-V1-WAITING-PERIOD\", \"DEMO-OUT-V1-RENEWAL\", \"DEMO-OUT-V1-EXCLUSIONS\", \"DEMO-OUT-V1-PREMIUM\", \"DEMO-OUT-V1-UNDERWRITING\"]\n\n}",
      "name": "finish_comparison"
    },
    "type": "function",
    "index": 0
  }
]
```
