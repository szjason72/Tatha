#!/usr/bin/env python3
"""
用本地测试简历跑完整 job_match：MarkItDown 转 Markdown → 职位匹配流水线 → 打印结果。
用法: uv run python scripts/test_job_match_with_resume.py [简历文件路径]
默认: /Users/szjason72/Downloads/测试简历/姜焘简历.pdf
"""
import io
import sys
from pathlib import Path

# 默认测试简历（优先 PDF；若未装 markitdown[pdf] 可改用同目录下 .html/.xls）
DEFAULT_RESUME = Path("/Users/szjason72/Downloads/测试简历/姜焘简历.pdf")
# 备用（无需 PDF 依赖）: 梁德锋简历_智联招聘.html
FALLBACK_RESUME = Path("/Users/szjason72/Downloads/测试简历/[梁德锋]简历_智联招聘.html")


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_RESUME
    if not path.exists() and path == DEFAULT_RESUME and FALLBACK_RESUME.exists():
        path = FALLBACK_RESUME
        print(f"使用备用简历: {path.name}\n")
    if not path.exists():
        print(f"文件不存在: {path}")
        sys.exit(1)

    print(f"=== 1. MarkItDown 转换: {path.name} ===\n")
    with open(path, "rb") as f:
        content = f.read()
    try:
        from tatha.ingest.markitdown_convert import stream_to_markdown
        markdown = stream_to_markdown(io.BytesIO(content), filename=path.name)
    except Exception as e:
        print(f"转换失败: {e}")
        sys.exit(1)
    print(markdown[:1500] or "(空)" + ("..." if len(markdown) > 1500 else ""))
    print("\n")

    print("=== 2. 职位匹配流水线（mock 职位源 + LLM 打分）===\n")
    try:
        from tatha.jobs import run_job_match_pipeline
        results, total = run_job_match_pipeline(resume_text=markdown, top_n=5)
    except Exception as e:
        print(f"匹配失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print(f"参与打分职位数: {total}，返回 Top: {len(results)}\n")
    if results and results[0].score.summary.startswith("打分失败"):
        print("提示: LLM 打分未成功，请检查 .env 中 DEEPSEEK_API_KEY（或 OPENAI_API_KEY）与 TATHA_DEFAULT_MODEL（如 deepseek/deepseek-chat）。\n")
    for i, r in enumerate(results, 1):
        job = r.job
        score = r.score
        print(f"--- 匹配 #{i} ---")
        print(f"职位: {job.title} @ {job.company}")
        print(f"地点: {job.location or '-'}")
        print(f"综合分: {score.overall} | 摘要: {score.summary}")
        print(f"关键词: {score.keywords[:5]}")
        print(f"链接: {job.url or '-'}\n")

    print("=== 完成 ===")


if __name__ == "__main__":
    main()
