"""比较任务的数据契约与确定性校验；模型不能改写比较单元的条款事实。"""

from copy import deepcopy
import math

from .catalog import Catalog, DIMENSIONS


def prepare_request(request, catalog):
    if not isinstance(request, dict):
        raise ValueError("需求必须是 JSON 对象。")
    if set(request) - {"question", "profile", "selections"}:
        raise ValueError("需求包含不支持的字段。")
    question = request.get("question", "比较选定医疗险的保障与限制。")
    if not isinstance(question, str) or not question.strip() or len(question) > 1500:
        raise ValueError("问题需为 1–1500 字符的文本。")
    profile = request.get("profile", {})
    if not isinstance(profile, dict) or set(profile) - {"focus", "annual_budget", "age", "social_insurance"}:
        raise ValueError("需求档案字段不合法。")
    focus = profile.get("focus", [])
    if not isinstance(focus, list) or any(not isinstance(x, str) or x not in DIMENSIONS for x in focus):
        raise ValueError("关注点必须是支持的比较维度列表。")
    age, budget = profile.get("age"), profile.get("annual_budget")
    if age is not None and (type(age) is not int or not 0 <= age <= 100):
        raise ValueError("年龄需为 0–100 的整数，或留空。")
    if budget is not None and (type(budget) not in (int, float) or not math.isfinite(budget) or not 0 <= budget <= 1000000):
        raise ValueError("年度预算需为 0–1000000 的有限数值，或留空。")
    social = profile.get("social_insurance", "unknown")
    if social not in ("yes", "no", "unknown"):
        raise ValueError("医保状态需为 yes、no 或 unknown。")
    selections = request.get("selections", [])
    if not isinstance(selections, list) or len(selections) > 3:
        raise ValueError("一次最多比较三个产品版本。")
    normalized, seen = [], set()
    for item in selections:
        if not isinstance(item, dict) or set(item) != {"product_id", "version"}:
            raise ValueError("每个比较对象必须指定产品编号与资料版本。")
        if any(not isinstance(item[k], str) for k in item):
            raise ValueError("产品编号与资料版本必须是字符串。")
        key = item["product_id"], item["version"]
        if key in seen:
            raise ValueError("不能重复选择同一产品版本。")
        catalog.get_product(*key)
        seen.add(key)
        normalized.append(deepcopy(item))
    questions = []
    if not focus:
        questions.append("你最希望比较哪些方面？例如保障范围、免赔额或续保安排。")
    if len(normalized) < 2:
        questions.append("请选择两到三个需要比较的产品，并确认各自的资料版本。")
    clean = {"question": question.strip(), "profile": {"focus": list(dict.fromkeys(focus)),
             "annual_budget": budget, "age": age, "social_insurance": social}, "selections": normalized}
    dimensions = list(dict.fromkeys(focus + list(DIMENSIONS)))
    plan = ["确认需求与比较对象的资料版本。",
            "优先查证关注维度：" + "、".join(DIMENSIONS[x] for x in focus) + "。" if focus else "等待补充关注维度。",
            "补齐保障、费用条件、续保、免责与投保前提，保留所有信息缺口。",
            "逐项校验产品、版本和已读取证据，再生成比较表与待确认事项。"]
    return {"status": "needs_input" if questions else "ready", "request": clean,
            "questions": questions, "plan": plan, "dimensions": dimensions,
            "catalog_fingerprint": catalog.fingerprint}


class EvidenceWorkspace:
    """本次任务可访问的产品、证据与完成条件；查询结果不能扩大访问范围。"""

    def __init__(self, request, catalog=None):
        self.catalog = catalog or Catalog()
        self.state = prepare_request(request, self.catalog)
        self.allowed = {(x["product_id"], x["version"]) for x in self.state["request"]["selections"]}
        self.evidence = {}
        self.trace = []

    def _scope(self, product_id, version):
        if (product_id, version) not in self.allowed:
            raise ValueError("只能读取本次已选产品和资料版本。")

    def remember(self, facts):
        verified = {}
        for item in facts:
            self._scope(item["product_id"], item["version"])
            canonical = self.catalog.read(item["product_id"], item["version"], item["evidence_id"])
            if item != canonical:
                raise ValueError("工具证据与所选资料版本不一致，不能纳入比较。")
            verified[item["evidence_id"]] = canonical
        # 整批成功才加入本次证据，不能让报错响应留下模型未收到的部分结果。
        self.evidence.update(verified)
        return deepcopy(facts)

    def search(self, product_id, version, query, limit=3):
        self._scope(product_id, version)
        return self.remember(self.catalog.search(product_id, version, query, limit=limit))

    def read_dimensions(self, product_id, version, dimensions):
        self._scope(product_id, version)
        if not isinstance(dimensions, list) or not dimensions or len(dimensions) > len(DIMENSIONS):
            raise ValueError("需要指定 1–9 个比较维度。")
        if any(not isinstance(x, str) or x not in DIMENSIONS for x in dimensions):
            raise ValueError("包含未知比较维度。")
        return self.remember([fact for dimension in dict.fromkeys(dimensions)
                              for fact in self.catalog.facts(product_id, version, dimension)])

    def finish(self, evidence_ids):
        if self.state["status"] != "ready":
            raise ValueError("需求尚未补齐，请先回答补充问题。")
        if not isinstance(evidence_ids, list) or any(not isinstance(x, str) for x in evidence_ids):
            raise ValueError("证据编号必须是字符串列表。")
        if len(set(evidence_ids)) != len(evidence_ids):
            raise ValueError("证据编号不能重复。")
        if set(evidence_ids) - self.evidence.keys():
            raise ValueError("不能引用本次工具没有返回的证据。")
        # 所有比较维度的事实及其限制都要进入结果，防止挑选有利证据。
        required = {fact["evidence_id"] for item in self.state["request"]["selections"]
                    for dimension in self.state["dimensions"]
                    for fact in self.catalog.facts(item["product_id"], item["version"], dimension)}
        missing = required - set(evidence_ids)
        if missing:
            raise ValueError("比较依据尚未齐全，请读取缺失维度并保留全部适用条件。缺少：" + ", ".join(sorted(missing)))
        return self.report(accepted=evidence_ids)

    def report(self, *, accepted=None, status=None, model_calls=0, tool_calls=0, error=None):
        chosen = set(accepted) if accepted is not None else set(self.evidence)
        sources = [deepcopy(f) for key, f in self.evidence.items() if key in chosen]
        rows, gaps = [], []
        for dimension in self.state["dimensions"]:
            cells = []
            for item in self.state["request"]["selections"]:
                product = self.catalog.get_product(item["product_id"], item["version"])
                facts = [f for f in sources if (f["product_id"], f["version"], f["dimension"]) ==
                         (item["product_id"], item["version"], dimension)]
                cell_status = "unknown"
                if facts:
                    cell_status = "conflict" if any(f["status"] == "conflict" for f in facts) else (
                        "unknown" if any(f["status"] == "unknown" for f in facts) else "known")
                text = "；".join(f["text"] for f in facts) if facts else "尚未取得该项证据。"
                conditions = list(dict.fromkeys(c for f in facts for c in f["conditions"]))
                cells.append({**item, "product_name": product["name"], "status": cell_status,
                              "text": text, "conditions": conditions,
                              "evidence_ids": [f["evidence_id"] for f in facts]})
                if cell_status != "known":
                    gaps.append(f'{product["name"]} · {DIMENSIONS[dimension]}：' + text)
            rows.append({"dimension": dimension, "label": DIMENSIONS[dimension], "cells": cells})
        profile = self.state["request"]["profile"]
        if profile["annual_budget"] is not None:
            gaps.append("年度预算已记录；本项目未取得针对该需求的有效报价，因此不判定任何产品是否符合预算。")
        next_steps = ["向保险方核对完整条款、保障计划表、健康告知及当前投保规则。",
                      "取得适用于年龄、医保状态和所选计划的报价后，再核对年度预算。",
                      "健康告知与承保结果由保险方确认；本报告比较资料，不作承保判断。"]
        if profile["age"] is not None:
            next_steps.append(f'已记录年龄 {profile["age"]} 岁；需逐产品核对投保年龄范围，当前资料比较不等于通过投保资格检查。')
        if profile["social_insurance"] != "unknown":
            identity = "有" if profile["social_insurance"] == "yes" else "无"
            next_steps.append(f'已记录{identity}基本医保；请核对所选计划的投保身份与实际结算条件，两者可能影响赔付比例。')
        if any(c["status"] == "conflict" for row in rows for c in row["cells"]):
            next_steps.insert(0, "先核对冲突资料的版本与适用条件，再使用对应结论。")
        final_status = status or ("needs_input" if self.state["questions"] else
                                  "completed_with_gaps" if gaps else "completed")
        return {"status": final_status, "request": deepcopy(self.state["request"]),
                "questions": self.state["questions"][:], "plan": self.state["plan"][:],
                "rows": rows, "sources": sources, "gaps": list(dict.fromkeys(gaps)),
                "next_steps": next_steps, "trace": deepcopy(self.trace),
                "model_calls": model_calls, "tool_calls": tool_calls,
                "catalog_fingerprint": self.catalog.fingerprint, "error": error}


def run_comparison(request, *, catalog=None, mode="offline", max_calls=6, max_tools=12, request_model=None):
    workspace = EvidenceWorkspace(request, catalog)
    if mode not in ("offline", "live"):
        raise ValueError("运行模式需为 offline 或 live。")
    if workspace.state["status"] == "needs_input":
        return {**workspace.report(), "mode": mode}
    if mode == "live":
        if request_model is None:
            raise ValueError("模型模式需要显式提供请求接口。")
        from .agent import run_agent
        return {**run_agent(workspace, request_model, max_calls=max_calls, max_tools=max_tools), "mode": mode}
    count = 0
    for item in workspace.state["request"]["selections"]:
        facts = workspace.read_dimensions(item["product_id"], item["version"], workspace.state["dimensions"])
        count += 1
        workspace.trace.append({"step": count, "name": "read_product_clauses", "arguments": item,
                                "evidence_ids": [f["evidence_id"] for f in facts], "is_error": False})
    result = workspace.finish(list(workspace.evidence))
    result.update(mode="offline", tool_calls=count)
    return result


def render_markdown(report):
    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ")
    lines = ["# 医疗险保障比较", "", "问题：" + cell(report["request"]["question"]),
             "", "状态：" + report["status"], ""]
    profile = report["request"]["profile"]
    lines.extend(["## 需求摘要", "", "关注点：" + "、".join(DIMENSIONS[x] for x in profile["focus"]),
                  "", "年度预算：" + (str(profile["annual_budget"]) + " 元" if profile["annual_budget"] is not None else "未提供"), ""])
    if report["questions"]:
        lines.extend(["## 需要补充", ""] + ["- " + q for q in report["questions"]] + [""])
    for row in report["rows"]:
        lines.extend(["## " + row["label"], "", "| 方案 | 资料内容 | 条件 | 依据 |", "| --- | --- | --- | --- |"])
        for item in row["cells"]:
            refs = " ".join(f'[{x}]' for x in item["evidence_ids"])
            lines.append("| " + " | ".join(cell(x) for x in (item["product_name"], item["text"],
                         "；".join(item["conditions"]), refs)) + " |")
        lines.append("")
    lines.extend(["## 资料缺口与下一步", ""] + ["- " + x for x in report["gaps"] + report["next_steps"]])
    lines.extend(["", "## 资料来源", ""])
    for item in report["sources"]:
        source = item["source"]
        label = f'[{item["evidence_id"]}] {item["product_name"]} / {item["version"]} / {item["locator"]}'
        url = source.get("url")
        lines.append("- " + label + (f' [来源]({url})' if url else "（自拟案例资料）")
                     + f'；核对日期：{source["checked_at"]}；生效日期：{source.get("effective_date") or "未核实"}。'
                     + source["locator"])
    return "\n".join(lines) + "\n"
