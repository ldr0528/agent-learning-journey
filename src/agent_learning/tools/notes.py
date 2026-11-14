"""读取本地 Hello-Agents 教学摘要，按关键词标签检索。

运行：python -m agent_learning.tools.notes --query "Agent Loop 为什么要有最大步数？"
这是配合第四章工具定义的简化练习，独立运行时不调用模型，不是向量检索。
"""

import argparse
import json
from pathlib import Path


NOTES_PATH = Path(__file__).resolve().parents[1] / "data" / "notes.json"


def search_notes(query, limit=2):
    # ① 每次都实际读取本地文件，查询结果来自文件内容。
    notes = json.loads(NOTES_PATH.read_text(encoding="utf-8"))["notes"]
    query = query.strip().casefold()
    if not query:
        return []
    if limit < 1:
        raise ValueError("limit 必须至少为 1。")

    # ② 查看问题中包含哪些关键词标签。casefold 让英文匹配不区分大小写。
    results = []
    for note in notes:
        matched = [word for word in note["keywords"] if word.casefold() in query]
        if matched:
            results.append({**note, "matched_keywords": matched, "score": len(matched)})

    # ③ 按匹配标签的数量排序，最多返回 limit 条；这不是语义相关度。
    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:limit]


def format_results(results):
    if not results:
        return "没有匹配到本地摘要。可能缺少相关资料，也可能是关键词表达不同；不能据此断言教材没有相关内容。"
    blocks = []
    for note in results:
        blocks.append(
            f'[{note["id"]}] {note["title"]}\n'
            f'匹配标签：{", ".join(note["matched_keywords"])}\n'
            f'摘要：{note["content"]}\n'
            f'性质：{note["content_type"]}\n'
            f'出处：{note["source_section"]}\n'
            f'原文链接：{note["source_url"]}'
        )
    return "\n\n".join(blocks)


def main():
    parser = argparse.ArgumentParser(description="检索本地教学摘要，不调用模型或联网")
    parser.add_argument("--query", required=True, help="要查询的问题或关键词")
    args = parser.parse_args()
    if not args.query.strip():
        parser.error("--query 不能为空。")
    try:
        results = search_notes(args.query)
    except (OSError, json.JSONDecodeError):
        print("无法读取摘要文件，请检查 agent_learning/data/notes.json 是否存在且 JSON 格式正确。")
        return 1
    print(f"问题：{args.query}\n本地检索命中 {len(results)} 条（最多返回 2 条）。\n")
    print(format_results(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
