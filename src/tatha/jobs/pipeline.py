"""
职位匹配流水线：拉取职位 → 逐条 LLM 打分 → 排序取 Top-N。
"""
from __future__ import annotations

from tatha.core.config import job_source_id, job_top_n
from tatha.jobs.schemas import JobInfo, JobMatchScore, MatchResult
from tatha.jobs.sources.registry import get_job_source
from tatha.jobs.scoring import score_resume_vs_job


# 单次流水线最多对多少条职位做 LLM 打分（控制成本）
MAX_JOBS_TO_SCORE = 20


def run_job_match_pipeline(
    resume_text: str,
    top_n: int | None = None,
    source_id: str | None = None,
) -> tuple[list[MatchResult], int]:
    """
    执行一次职位匹配：用指定职位源拉职位，对每条职位做简历 vs 职位描述打分，按 overall 排序后返回前 top_n 条。
    返回 (匹配列表, 参与打分的职位数)。resume_text 为空时返回 ([], 0)；top_n / source_id 不传则用配置。
    """
    resume_text = (resume_text or "").strip()
    if not resume_text:
        return [], 0

    n = top_n if top_n is not None else job_top_n()
    source = get_job_source(source_id)
    jobs = source.fetch_jobs(limit=MAX_JOBS_TO_SCORE)
    if not jobs:
        return [], 0

    results: list[MatchResult] = []
    for job in jobs:
        jd = (job.description or f"{job.title} @ {job.company}").strip()
        score = score_resume_vs_job(resume_text, jd)
        results.append(MatchResult(job=job, score=score))

    results.sort(key=lambda r: r.score.overall, reverse=True)
    return results[:n], len(results)
