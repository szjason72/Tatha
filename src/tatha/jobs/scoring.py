"""
简历 vs 职位 LLM 打分：PydanticAI Agent，输入简历+职位描述，输出 JobMatchScore。
借鉴 DailyJobMatch / resume-optimization-crew 的多维度打分结构。
"""
from __future__ import annotations

from tatha.core.config import get_default_model
from tatha.jobs.schemas import JobMatchScore


def _model():
    from pydantic_ai_litellm import LiteLLMModel
    return LiteLLMModel(model_name=get_default_model())


def _job_match_agent():
    from pydantic_ai import Agent
    return Agent(
        model=_model(),
        output_type=JobMatchScore,
        system_prompt=(
            "你是一个职位匹配评分员。根据「简历」与「职位描述」两段文本，从以下维度打分并只输出结构化结果。"
            "不要输出任何解释或前缀（如「好的」「这是」），只输出符合 JobMatchScore 的 JSON。\n"
            "维度与范围：\n"
            "- background_match: 领域/背景匹配 0–10\n"
            "- skills_overlap: 技能重叠 0–30\n"
            "- experience_relevance: 经历相关性 0–30\n"
            "- seniority: 职级匹配 0–10\n"
            "- language_requirement: 语言要求匹配 0–10\n"
            "- company_score: 公司/岗位吸引力 0–10\n"
            "- salary_match: 钱多——薪资/待遇与候选人期望或市场匹配 0–10，未提及则 5\n"
            "- location_match: 离家近——工作地点、远程/混合与候选人偏好匹配 0–10，未提及则 5\n"
            "- culture_workload_match: 事少——工作强度、弹性、加班文化、团队氛围匹配 0–10，未提及则 5\n"
            "- overall: 综合分 0–100，需综合考虑上述所有维度（含钱多、事少、离家近），为各项加权综合\n"
            "同时填写 summary（一句话匹配摘要，可提及薪资/地点/强度亮点）、keywords、fit_bullets（最多 5 条）。"
        ),
    )


_agent = None


def score_resume_vs_job(resume_text: str, job_description: str) -> JobMatchScore:
    """
    对单条职位做简历匹配打分。
    若 LLM 调用失败，返回 overall=0 的默认分。
    """
    global _agent
    if _agent is None:
        _agent = _job_match_agent()
    user_message = f"【简历】\n{resume_text[:8000]}\n\n【职位描述】\n{(job_description or '')[:4000]}"
    try:
        result = _agent.run_sync(user_message)
        return result.output
    except Exception as e:
        # 简短错误提示，便于排查（不暴露 key 或长栈）
        err_msg = (str(e).strip() or type(e).__name__)[:120]
        if "key" in err_msg.lower() or "secret" in err_msg.lower() or "auth" in err_msg.lower():
            err_msg = type(e).__name__ + "（请检查 .env 中对应 API Key 与 TATHA_DEFAULT_MODEL）"
        return JobMatchScore(
            overall=0,
            background_match=0,
            skills_overlap=0,
            experience_relevance=0,
            seniority=0,
            language_requirement=0,
            company_score=0,
            salary_match=5,
            location_match=5,
            culture_workload_match=5,
            summary=f"打分失败: {err_msg}",
            keywords=[],
            fit_bullets=[],
        )
