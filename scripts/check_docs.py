"""Validate published documentation, examples and editable SVG without network calls."""

import ast
from collections import Counter
import copy
import html
import json
from pathlib import Path
import re
import subprocess
import textwrap
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CHAPTERS = (
    "model-calls", "tool-feedback", "agent-loop", "retrieval-and-citations",
    "state-and-context", "planning", "reflection", "rag", "evaluation", "langgraph", "mcp",
)
EXACT_FUNCTIONS = {
    "get_weather": "src/agent_learning/tools/weather.py",
    "execute_action": "src/agent_learning/tools/weather.py",
    "search_notes": "src/agent_learning/tools/notes.py",
    "citation_ids": "src/agent_learning/agents/research.py",
    "summarize_records": "src/agent_learning/context.py",
}


def heading_anchors(content):
    counts = Counter()
    anchors = set()
    for heading in re.findall(r"^#{1,6}\s+(.+)$", content, re.MULTILINE):
        heading = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", heading)
        heading = re.sub(r"<[^>]+>", "", heading)
        slug = re.sub(r"[^\w\- ]", "", html.unescape(heading).strip().lower()).replace(" ", "-")
        anchors.add(f"{slug}-{counts[slug]}" if counts[slug] else slug)
        counts[slug] += 1
    return anchors


def normalized(node):
    node = copy.deepcopy(node)
    if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
        if isinstance(node.body[0].value.value, str):
            node.body.pop(0)
    return ast.dump(node, include_attributes=False)


def main():
    tracked = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT,
    ).decode("utf-8").split("\0")
    files = {name for name in tracked if name and (ROOT / name).is_file()}
    errors, snippets = [], []
    for name in sorted(files):
        path = ROOT / name
        if path.suffix not in {".md", ".svg", ".json"}:
            continue
        content = path.read_text(encoding="utf-8-sig")
        if path.suffix == ".svg":
            root = ET.fromstring(content)
            if root.find("{http://www.w3.org/2000/svg}title") is None:
                errors.append(f"{name}: SVG 缺少 title")
        elif path.suffix == ".json":
            json.loads(content)
        else:
            if len(re.findall(r"^```[^`]*$", content, re.MULTILINE)) % 2:
                errors.append(f"{name}: 代码围栏未闭合")
            for target in re.findall(r"\]\(([^)\n]+)\)", content):
                target = target.strip("<>")
                link = urlsplit(target)
                if link.scheme or link.netloc:
                    continue
                dest = (path.parent / unquote(link.path)).resolve() if link.path else path
                if not dest.is_relative_to(ROOT) or not dest.exists():
                    errors.append(f"{name}: 无效本地链接 {target}")
                    continue
                if dest.is_file() and dest.relative_to(ROOT).as_posix() not in files:
                    errors.append(f"{name}: 链接目标未纳入仓库 {target}")
                if link.fragment and dest.suffix == ".md":
                    if unquote(link.fragment) not in heading_anchors(dest.read_text(encoding="utf-8-sig")):
                        errors.append(f"{name}: 无效标题锚点 {target}")
            for language, code in re.findall(r"^```([\w-]+)\n(.*?)^```[ \t]*$", content, re.MULTILINE | re.DOTALL):
                try:
                    if language == "python":
                        tree = ast.parse(code)
                        compile("async def _excerpt():\n" + textwrap.indent(code, "    "), name, "exec")
                        if name.startswith("docs/learning/"):
                            snippets.append(tree)
                    elif language == "json":
                        json.loads(code)
                except (SyntaxError, ValueError) as error:
                    errors.append(f"{name}: {language} 片段无效 ({error})")

    for chapter in CHAPTERS:
        path = ROOT / f"docs/learning/{chapter}.md"
        if not path.is_file():
            errors.append(f"缺少章节：{chapter}")
            continue
        content = path.read_text(encoding="utf-8")
        if "hello-agents" not in content.lower() or "github.com/datawhalechina" not in content.lower():
            errors.append(f"{chapter}: 缺少教材来源链接")
        if not re.search(r"练习|验收|自查", content):
            errors.append(f"{chapter}: 缺少学习练习或验收")
        if len(content) < 1500:
            errors.append(f"{chapter}: 章节过短，请核对是否仅有占位目录")

    for name, source in EXACT_FUNCTIONS.items():
        actual = [node for tree in snippets for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
        original = next(node for node in ast.parse((ROOT / source).read_text(encoding="utf-8")).body
                        if isinstance(node, ast.FunctionDef) and node.name == name)
        if not actual or any(normalized(node) != normalized(original) for node in actual):
            errors.append(f"正文函数与源码不一致：{name}")
    if errors:
        print("\n".join(errors))
        return 1
    print(f"文档检查通过：{len(CHAPTERS)} 章，{len(snippets)} 段 Python，链接、图示、JSON 与关键函数一致。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
