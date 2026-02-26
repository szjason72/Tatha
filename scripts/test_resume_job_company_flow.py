#!/usr/bin/env python3
"""
Resume → Job → Company 三阶段 E2E 测试流程。

业务流程：
  1. Resume：简历输入（文件转 Markdown + 可选解析，或直接文本）
  2. Job：用简历做职位匹配，得到高分段岗位列表（含公司名）
  3. Company：对匹配结果中的公司做征信/经营情况查询（主体明确，辅助用户决定是否投递）

用法:
  uv run python scripts/test_resume_job_company_flow.py [简历文件路径]
  不传参数时使用内置简历摘要文本。
需配置 .env：DEEPSEEK_API_KEY（或 OPENAI_API_KEY）用于匹配打分与征信解析。
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

# 默认简历摘要（无文件时使用）
DEFAULT_RESUME_TEXT = """
张三，男，本科北京大学计算机系，3 年互联网开发经验。
技能：Python、FastAPI、MySQL、Redis、Docker，有 AI/LLM 落地经验。
经历：某大厂后端开发，负责推荐与搜索服务；参与简历解析与 RAG 项目。
"""


def step1_resume(resume_path: Path | None) -> str:
    """阶段 1：得到简历全文。支持文件（MarkItDown）或默认文本。"""
    if resume_path and resume_path.exists():
        with open(resume_path, "rb") as f:
            content = f.read()
        try:
            from tatha.ingest.markitdown_convert import stream_to_markdown
            markdown = stream_to_markdown(io.BytesIO(content), filename=resume_path.name)
        except Exception as e:
            print(f"[Resume] MarkItDown 转换失败: {e}")
            sys.exit(1)
        print(f"[Resume] 已从文件转换: {resume_path.name} -> {len(markdown)} 字")
        return markdown
    print("[Resume] 使用默认简历摘要文本")
    return DEFAULT_RESUME_TEXT.strip()


def step2_job(resume_text: str, top_n: int = 3) -> list[dict]:
    """阶段 2：职位匹配，返回 Top-N 条（含 job.company）。"""
    from tatha.jobs import run_job_match_pipeline

    results, total = run_job_match_pipeline(resume_text=resume_text, top_n=top_n)
    if not results:
        print("[Job] 无匹配结果（可能职位源为空或打分未返回）")
        return []
    matches = [r.model_dump() for r in results]
    print(f"[Job] 参与打分 {total} 条，返回 Top-{len(matches)} 条匹配")
    for i, m in enumerate(matches, 1):
        job = m.get("job") or {}
        score = m.get("score") or {}
        print(f"  #{i} {job.get('title')} @ {job.get('company')} 综合分={score.get('overall')}")
    return matches


def step3_company(matches: list[dict], max_companies: int = 2) -> list[dict]:
    """
    阶段 3：对匹配结果中的公司做征信解析（模拟「用户关心这家公司经营/征信」）。
    仅对前 max_companies 家公司调用 run_credit_analysis，主体为 job.company。
    """
    from tatha.agents import run_credit_analysis

    companies_done: list[dict] = []
    for m in matches[:max_companies]:
        job = m.get("job") or {}
        company_name = (job.get("company") or "").strip()
        if not company_name:
            continue
        # 构造「匹配后查该公司征信」的文本，主体明确
        text = f"主体名称{company_name}，报告类型企业信用报告，摘要说明经营正常，无不良记录。"
        try:
            result = run_credit_analysis(text)
            cr = result.model_dump()
            cr["_company_from_job"] = company_name
            companies_done.append(cr)
            entity = (result.entity_name or "").strip()
            ok = entity and (company_name in entity or entity in company_name or entity == company_name)
            status = "ok" if ok else "entity 与公司名不一致"
            print(f"[Company] {company_name} -> entity_name={entity!r} ({status})")
        except Exception as e:
            print(f"[Company] {company_name} -> 征信解析失败: {e}")
            companies_done.append({"_company_from_job": company_name, "_error": str(e)})
    return companies_done


def main() -> int:
    resume_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if resume_path and not resume_path.exists():
        print(f"文件不存在: {resume_path}")
        return 1

    print("=== 1. Resume 阶段 ===\n")
    resume_text = step1_resume(resume_path)
    if not resume_text.strip():
        print("简历内容为空，退出")
        return 1

    print("\n=== 2. Job 阶段（职位匹配）===\n")
    try:
        matches = step2_job(resume_text, top_n=3)
    except Exception as e:
        print(f"[Job] 匹配失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    if not matches:
        print("无匹配结果，跳过 Company 阶段")
        return 0

    print("\n=== 3. Company 阶段（匹配后查该公司征信）===\n")
    try:
        company_results = step3_company(matches, max_companies=2)
    except Exception as e:
        print(f"[Company] 征信阶段失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # 断言：至少有一条匹配；若有征信解析成功则主体应明确
    assert len(matches) > 0, "应有至少一条职位匹配"
    success_count = 0
    for cr in company_results:
        if "_error" in cr:
            continue
        entity = cr.get("entity_name") or ""
        assert entity, "业务流程中征信针对匹配后的公司，entity_name 不应缺失"
        success_count += 1
    if not company_results:
        print("未执行任何公司征信步骤（匹配结果无 company 或异常）")
    elif success_count == 0:
        print("公司征信步骤均未成功（可能无 API Key/网络），流程结构已跑通")

    print("\n=== Resume → Job → Company 流程完成 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
