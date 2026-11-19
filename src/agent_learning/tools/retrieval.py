"""可检查的中文 BM25 基线：分块、索引、排序、来源保留。无网络依赖。"""

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re


CORPUS_PATH = Path(__file__).resolve().parents[1] / "data" / "corpus.json"


def tokenize(text):
    """英文按词，中文按相邻双字；这是字面检索，不是语义嵌入。"""
    tokens = []
    for part in re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]+", text.casefold()):
        if "\u4e00" <= part[0] <= "\u9fff":
            tokens.extend(part[i:i + 2] for i in range(len(part) - 1))
            if len(part) == 1:
                tokens.append(part)
        else:
            tokens.append(part)
    return tokens


def split_documents(documents, max_chars=180, overlap=30):
    """按字符窗口切分；保留原文偏移，不能把字符数称为 token 数。"""
    if max_chars < 1 or not 0 <= overlap < max_chars:
        raise ValueError("分块要求 max_chars > 0 且 0 <= overlap < max_chars。")
    chunks, seen = [], set()
    for document in documents:
        doc_id = document["id"]
        if doc_id in seen or not re.fullmatch(r"D[0-9]+", doc_id):
            raise ValueError("文档编号必须是唯一的 D数字。")
        seen.add(doc_id)
        text = document["text"]
        if not text.strip():
            raise ValueError(f"空文档：{doc_id}")
        start, number = 0, 1
        while start < len(text):
            end = min(start + max_chars, len(text))
            chunks.append({
                "id": f"{doc_id}-C{number:02d}", "doc_id": doc_id,
                "title": document["title"], "text": text[start:end],
                "start": start, "end": end,
                "source_section": document["source_section"],
                "source_url": document["source_url"],
                "content_type": document["content_type"],
            })
            if end == len(text):
                break
            start, number = end - overlap, number + 1
    return chunks


class BM25Index:
    def __init__(self, documents, *, max_chars=180, overlap=30, k1=1.5, b=0.75):
        if k1 <= 0 or not 0 <= b <= 1:
            raise ValueError("BM25 要求 k1 > 0 且 0 <= b <= 1。")
        self.chunks = split_documents(documents, max_chars, overlap)
        self.k1, self.b = k1, b
        self.max_chars, self.overlap = max_chars, overlap
        self.counts = [Counter(tokenize(chunk["title"] + " " + chunk["text"])) for chunk in self.chunks]
        self.lengths = [sum(count.values()) for count in self.counts]
        self.average_length = sum(self.lengths) / len(self.lengths) if self.lengths else 1
        self.document_frequency = Counter(term for count in self.counts for term in count)
        payload = json.dumps(documents, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.corpus_sha256 = hashlib.sha256(payload).hexdigest()

    def search(self, query, limit=3, min_score=0.0):
        if limit < 1 or min_score < 0 or not math.isfinite(min_score):
            raise ValueError("limit 至少为 1，min_score 是非负有限数。")
        terms = set(tokenize(query))
        results, total = [], len(self.chunks)
        for chunk, counts, length in zip(self.chunks, self.counts, self.lengths):
            score = 0.0
            matched = []
            for term in sorted(terms):
                frequency = counts[term]
                if not frequency:
                    continue
                matched.append(term)
                df = self.document_frequency[term]
                inverse_frequency = math.log(1 + (total - df + 0.5) / (df + 0.5))
                normalizer = frequency + self.k1 * (1 - self.b + self.b * length / self.average_length)
                score += inverse_frequency * frequency * (self.k1 + 1) / normalizer
            if score > min_score:
                results.append({**chunk, "score": score, "matched_terms": matched})
        return sorted(results, key=lambda item: (-item["score"], item["id"]))[:limit]


def load_index(path=CORPUS_PATH, **kwargs):
    corpus = json.loads(Path(path).read_text(encoding="utf-8"))
    return BM25Index(corpus["documents"], **kwargs)


def select_evidence(results, max_chars=1800):
    """选择完整证据块；预算包含元数据包装，避免再次截断证据块或来源。"""
    if max_chars < 1:
        raise ValueError("证据字符预算必须至少为 1。")
    selected, used = [], 0
    for item in results:
        block = json.dumps({key: item[key] for key in (
            "id", "title", "text", "source_section", "source_url", "content_type",
        )}, ensure_ascii=False)
        cost = len(block) + (1 if selected else 0)
        if used + cost <= max_chars:
            selected.append(item)
            used += cost
    return selected


def format_evidence(evidence):
    return "\n".join(json.dumps({key: item[key] for key in (
        "id", "title", "text", "source_section", "source_url", "content_type",
    )}, ensure_ascii=False) for item in evidence)
