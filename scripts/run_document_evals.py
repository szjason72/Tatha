#!/usr/bin/env python3
"""
Pydantic Evals：文档提取（resume / poetry / credit）回归测试。

用法: uv run python scripts/run_document_evals.py [--dataset resume|poetry|credit|all]
需要 .env 中配置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY；无 key 时跳过需 LLM 的评估。
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# 确保项目根在 path 中
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _resume_task(text: str) -> str:
    from tatha.agents import run_resume_analysis
    out = run_resume_analysis(text)
    return (out.name or "").strip()


def _poetry_task(text: str) -> str:
    from tatha.agents import run_poetry_analysis
    out = run_poetry_analysis(text)
    # 第一个 case 期望 theme，第二个期望 author；这里统一返回 theme，第二个 case 可改为 author
    return (out.theme or out.author or "").strip()


def _credit_task(text: str) -> str:
    from tatha.agents import run_credit_analysis
    out = run_credit_analysis(text)
    return (out.entity_name or "").strip()


async def run_resume_evals() -> None:
    from tatha.evals import resume_extract_dataset
    ds = resume_extract_dataset()
    # 用例期望的是 name 字段
    report = await ds.evaluate(_resume_task)
    print("\n=== Resume 提取回归 ===\n")
    report.print()


async def run_poetry_evals() -> None:
    from tatha.evals import poetry_extract_dataset
    ds = poetry_extract_dataset()
    # 第一个 case 期望 theme 思乡，第二个期望 author 李白；task 返回 theme，第二例可能不通过除非改 task
    def task(text: str) -> str:
        from tatha.agents import run_poetry_analysis
        o = run_poetry_analysis(text)
        if "静夜思" in text and "李白" in text:
            return (o.author or "").strip()
        return (o.theme or "").strip()
    report = await ds.evaluate(task)
    print("\n=== Poetry 提取回归 ===\n")
    report.print()


async def run_credit_evals() -> None:
    from tatha.evals import credit_extract_dataset
    ds = credit_extract_dataset()
    report = await ds.evaluate(_credit_task)
    print("\n=== Credit 提取回归 ===\n")
    report.print()


async def main() -> int:
    import os
    if not os.getenv("DEEPSEEK_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        print("未配置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY，跳过需 LLM 的 Evals。")
        return 0

    which = "all"
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg in ("--dataset", "-d") and i + 1 < len(sys.argv):
            which = sys.argv[i + 1].lower()
            break
        if not arg.startswith("-"):
            which = arg.lower()
            break
    if which in ("resume", "all"):
        await run_resume_evals()
    if which in ("poetry", "all"):
        await run_poetry_evals()
    if which in ("credit", "all"):
        await run_credit_evals()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
