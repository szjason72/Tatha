"""
职位匹配流水线：职位源 + 简历 vs 职位 LLM 打分 + 中央大脑接入。
借鉴 Argus（职位来源）与 DailyJobMatch/resume-optimization-crew（打分结构），在 Tatha 内自建闭环。
"""
from .schemas import (
    JobInfo,
    JobMatchScore,
    MatchResult,
    JobMatchRequest,
    JobMatchResponse,
)
from .pipeline import run_job_match_pipeline

__all__ = [
    "JobInfo",
    "JobMatchScore",
    "MatchResult",
    "JobMatchRequest",
    "JobMatchResponse",
    "run_job_match_pipeline",
]
