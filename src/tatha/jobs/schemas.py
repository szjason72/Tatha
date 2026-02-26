"""
职位与匹配结果的数据模型。
打分维度借鉴 DailyJobMatch / resume-optimization-crew：多维度 + 结构化。
"""
from pydantic import BaseModel, Field
from typing import Optional


class JobInfo(BaseModel):
    """职位信息（来自职位源：Mock / Apify LinkedIn 等）。"""
    title: str = Field(..., description="职位名称")
    company: str = Field(..., description="公司名称")
    url: Optional[str] = Field(None, description="职位链接")
    location: Optional[str] = Field(None, description="工作地点")
    description: Optional[str] = Field(None, description="职位描述全文或摘要，用于打分")
    source: Optional[str] = Field(None, description="来源标识，如 mock、apify_linkedin")


class JobMatchScore(BaseModel):
    """
    简历与职位的匹配打分（LLM 输出，PydanticAI 数据边界）。
    维度参考 DailyJobMatch，总分 0–100。
    """
    overall: int = Field(..., ge=0, le=100, description="综合匹配分 0–100")
    background_match: int = Field(0, ge=0, le=10, description="领域/背景匹配 0–10")
    skills_overlap: int = Field(0, ge=0, le=30, description="技能重叠 0–30")
    experience_relevance: int = Field(0, ge=0, le=30, description="经历相关性 0–30")
    seniority: int = Field(0, ge=0, le=10, description="职级匹配 0–10")
    language_requirement: int = Field(0, ge=0, le=10, description="语言要求匹配 0–10")
    company_score: int = Field(0, ge=0, le=10, description="公司/岗位吸引力 0–10")
    summary: str = Field("", description="一句话匹配摘要")
    keywords: list[str] = Field(default_factory=list, description="匹配关键词")
    fit_bullets: list[str] = Field(default_factory=list, description="匹配要点列表")


class MatchResult(BaseModel):
    """单条匹配结果：职位 + 打分。"""
    job: JobInfo = Field(..., description="职位信息")
    score: JobMatchScore = Field(..., description="匹配打分")


class JobMatchRequest(BaseModel):
    """POST /v1/jobs/match 请求。"""
    resume_text: str = Field(..., description="简历全文或摘要，用于与职位描述对比打分")
    top_n: Optional[int] = Field(5, ge=1, le=20, description="返回前 N 条匹配，默认 5")
    source: Optional[str] = Field(None, description="职位源：mock（默认）| apify_linkedin，不传则用配置")


class JobMatchResponse(BaseModel):
    """POST /v1/jobs/match 响应。"""
    matches: list[MatchResult] = Field(default_factory=list, description="按综合分排序的匹配列表")
    total_evaluated: int = Field(0, description="参与打分的职位数")
    message: Optional[str] = Field(None, description="提示信息")
    error: Optional[str] = Field(None, description="错误信息")
