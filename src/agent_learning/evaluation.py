"""分别评估真实检索排名与回答引用结构，不自动判定语义真实性。"""

import json
from pathlib import Path
import re

from .tools.retrieval import load_index


CASES_PATH = Path(__file__).resolve().parent / "data" / "eval_cases.json"


def load_cases(path=CASES_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))["cases"]


def evaluate_retrieval(index, cases, k=3):
    if k < 1:
        raise ValueError("k 必须至少为 1。")
    rows, recalls, reciprocal_ranks, empty_negative = [], [], [], []
    valid_docs = {chunk["doc_id"] for chunk in index.chunks}
    for case in cases:
        expected = set(case["relevant_doc_ids"])
        if expected - valid_docs:
            raise ValueError(f'评估题 {case["id"]} 标注了不存在的文档。')
        results = index.search(case["question"], limit=k)
        found = {item["doc_id"] for item in results}
        row = {"id": case["id"], "question": case["question"], "relevant_doc_ids": sorted(expected),
               "returned_ids": [item["id"] for item in results]}
        if expected:
            recall = len(expected & found) / len(expected)
            reciprocal_rank = next((1 / rank for rank, item in enumerate(results, 1)
                                    if item["doc_id"] in expected), 0.0)
            recalls.append(recall)
            reciprocal_ranks.append(reciprocal_rank)
            row.update(recall_at_k=recall, reciprocal_rank=reciprocal_rank)
        else:
            empty_negative.append(not results)
            row["empty_result"] = not results
        rows.append(row)
    return {
        "kind": "offline_retrieval_development_set", "k": k,
        "corpus_sha256": index.corpus_sha256,
        "index": {"chunks": len(index.chunks), "max_chars": index.max_chars,
                  "overlap": index.overlap, "k1": index.k1, "b": index.b},
        "answerable_cases": len(recalls), "no_answer_cases": len(empty_negative),
        "mean_recall_at_k": sum(recalls) / len(recalls) if recalls else None,
        "mrr_at_k": sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else None,
        "empty_result_rate_on_no_answer": sum(empty_negative) / len(empty_negative) if empty_negative else None,
        "semantic_answer_accuracy": None,
        "note": "当前分数仅对应这个与语料一起设计的小型开发集；没有调用模型，不代表答案正确率。",
        "cases": rows,
    }


def evaluate_citations(predictions, index, case_ids):
    """predictions 为真实回答或明确标记来源的外部记录，函数不伪造回答。"""
    known = {item["id"] for item in index.chunks}
    seen, rows = set(), []
    total_claims = covered_claims = total_citations = valid_citations = 0
    for prediction in predictions:
        case_id = prediction.get("case_id")
        if not isinstance(case_id, str) or case_id not in case_ids or case_id in seen:
            raise ValueError("预测记录的 case_id 必须有效且唯一。")
        seen.add(case_id)
        evidence_ids, claims = prediction.get("evidence_ids"), prediction.get("claims")
        if not isinstance(evidence_ids, list) or any(not isinstance(item, str) for item in evidence_ids):
            raise ValueError("evidence_ids 必须是实际发送给模型的资料编号列表。")
        if set(evidence_ids) - known:
            raise ValueError("evidence_ids 包含知识库不存在的资料。")
        if not isinstance(claims, list):
            raise ValueError("claims 必须是列表。")
        case_total = case_valid = case_covered = 0
        for claim in claims:
            if not isinstance(claim, dict) or not isinstance(claim.get("text"), str) or not claim["text"].strip():
                raise ValueError("每条结论必须包含非空 text。")
            citations = claim.get("citations")
            if not isinstance(citations, list) or any(not isinstance(item, str) for item in citations):
                raise ValueError("citations 必须是字符串列表。")
            cited = set(citations)
            mentioned = set(re.findall(r"\[([A-Za-z][A-Za-z0-9_-]*)\]", claim["text"]))
            reported = cited | mentioned
            case_total += len(reported)
            case_valid += len(reported & set(evidence_ids))
            case_covered += bool(cited) and cited <= set(evidence_ids) and mentioned <= cited
        total_claims += len(claims)
        covered_claims += case_covered
        total_citations += case_total
        valid_citations += case_valid
        rows.append({"case_id": case_id, "claims": len(claims), "fully_cited_claims": case_covered,
                     "citation_references": case_total, "valid_references": case_valid})
    return {
        "kind": "provided_answer_citation_structure", "provided_cases": len(rows),
        "total_claims": total_claims, "citation_references": total_citations,
        "citation_validity": valid_citations / total_citations if total_citations else None,
        "claim_citation_coverage": covered_claims / total_claims if total_claims else None,
        "semantic_support": "not_evaluated",
        "note": "编号合法和每条结论带引用都不证明资料支持结论；证据日志真实性及语义需人工核对。",
        "cases": rows,
    }


def run_evaluation(k=3, predictions=None):
    index, cases = load_index(), load_cases()
    result = {"retrieval": evaluate_retrieval(index, cases, k)}
    if predictions is not None:
        result["citations"] = evaluate_citations(predictions, index, {case["id"] for case in cases})
    return result
