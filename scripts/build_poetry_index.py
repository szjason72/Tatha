#!/usr/bin/env python3
"""
从本地 poetry-knowledge-base 项目构建 poetry 命名空间的 FAISS 索引，供 RAG 查询（如「推荐一句思乡的诗」）。

数据源（按优先级）：
1. 环境变量 TATHA_POETRY_INDEX_SOURCE：指向 poems_index.json 或 poems_annotated.json 的路径
2. 默认：../poetry-knowledge-base/poems/poems_annotated.json（若存在），否则 poems_index.json

用法:
  uv run python scripts/build_poetry_index.py [--max-docs N]
  --max-docs  最多加载 N 条诗词（默认全部）；可用于快速建小索引测试。
"""
import argparse
import json
import os
from pathlib import Path

# Tatha 项目根
TATHA_ROOT = Path(__file__).resolve().parent.parent
# 默认：与 Tatha 同级的 poetry-knowledge-base
DEFAULT_POEMS_ANNOTATED = TATHA_ROOT.parent / "poetry-knowledge-base" / "poems" / "poems_annotated.json"
DEFAULT_POEMS_INDEX = TATHA_ROOT.parent / "poetry-knowledge-base" / "poems" / "poems_index.json"


def load_poems_json(path: Path) -> list[dict]:
    """加载诗词 JSON 数组。每条约含 poet_name, title, content；annotated 版另有 dynasty, annotation_summary。"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def poem_to_text(item: dict) -> str:
    """将一条诗词转为 RAG 可检索的纯文本。"""
    title = (item.get("title") or "").strip() or "(无题)"
    author = (item.get("poet_name") or "").strip()
    dynasty = (item.get("dynasty") or "").strip()
    content = (item.get("content") or "").strip()
    summary = (item.get("annotation_summary") or "").strip()
    parts = [f"《{title}》"]
    if author:
        parts.append(author)
    if dynasty:
        parts.append(f"（{dynasty}）")
    line1 = " ".join(parts)
    lines = [line1, content]
    if summary:
        lines.append(summary)
    return "\n".join(lines).strip()


def main():
    parser = argparse.ArgumentParser(description="从 poetry-knowledge-base 构建 Tatha poetry 索引")
    parser.add_argument("--max-docs", type=int, default=0, help="最多加载条数，0=全部")
    parser.add_argument("--source", type=str, default="", help="诗词 JSON 路径（覆盖 TATHA_POETRY_INDEX_SOURCE）")
    args = parser.parse_args()

    source_path = args.source or os.getenv("TATHA_POETRY_INDEX_SOURCE")
    if source_path:
        path = Path(source_path)
    else:
        path = DEFAULT_POEMS_ANNOTATED if DEFAULT_POEMS_ANNOTATED.exists() else DEFAULT_POEMS_INDEX

    if not path.exists():
        print(f"未找到诗词数据: {path}")
        print("请确保 poetry-knowledge-base 与 Tatha 同级，或设置 TATHA_POETRY_INDEX_SOURCE 指向 poems_index.json / poems_annotated.json")
        return 1

    print(f"加载: {path}")
    items = load_poems_json(path)
    if args.max_docs > 0:
        items = items[: args.max_docs]
        print(f"限制为前 {args.max_docs} 条")
    print(f"共 {len(items)} 条诗词")

    from llama_index.core import Document
    from tatha.retrieval import build_index_from_documents

    docs = [Document(text=poem_to_text(item)) for item in items if poem_to_text(item)]
    build_index_from_documents(docs, namespace="poetry")
    print("索引已构建到 .data/indices/poetry")
    return 0


if __name__ == "__main__":
    exit(main())
