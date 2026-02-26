# PydanticAI 类型安全智能体 + Marvin 轻量 AI 函数

from .schemas import ResumeAnalysis, PoetryAnalysis, CreditAnalysis
from .document_agents import (
    run_resume_analysis,
    run_poetry_analysis,
    run_credit_analysis,
    run_document_analysis,
)

__all__ = [
    "ResumeAnalysis",
    "PoetryAnalysis",
    "CreditAnalysis",
    "run_resume_analysis",
    "run_poetry_analysis",
    "run_credit_analysis",
    "run_document_analysis",
]
