"""
单入口 /v1/ask 的请求与响应模型。
"""
from pydantic import BaseModel, Field
from typing import Any, Optional


class AskRequest(BaseModel):
    """用户/助理发往中央大脑的请求。"""
    message: str = Field(..., description="用户输入或意图描述")
    context: Optional[dict[str, Any]] = Field(default_factory=dict, description="可选上下文（user_id、session_id、resume_text 等）")
    resume_text: Optional[str] = Field(None, description="可选：用于 job_match 的简历全文，也可放在 context.resume_text")


class AskResponse(BaseModel):
    """中央大脑统一返回格式。"""
    intent: str = Field(..., description="解析出的意图")
    result: dict[str, Any] = Field(default_factory=dict, description="能力端口返回的结果")
    suggestions: list[str] = Field(default_factory=list, description="可选：后续建议或提示")


class DocumentConvertResponse(BaseModel):
    """文档上传转 Markdown + 可选结构化提取的响应。"""
    markdown: str = Field(..., description="MarkItDown 转换后的 Markdown 全文")
    document_type: str | None = Field(None, description="请求的文档类型（如 resume）")
    extracted: dict[str, Any] | None = Field(None, description="若为 resume/poetry/credit 等且已配置提取器，则返回结构化结果")
    error: str | None = Field(None, description="转换或提取失败时的错误信息")


class RagQueryRequest(BaseModel):
    """私有数据 RAG 查询请求。"""
    namespace: str = Field(..., description="索引命名空间，如 resume、poetry")
    query: str = Field(..., description="自然语言查询，如「总结文档的核心观点」")


class RagQueryResponse(BaseModel):
    """RAG 查询响应。"""
    answer: str = Field(..., description="基于私有索引检索后的回答")
    namespace: str = Field(..., description="查询的命名空间")
    error: str | None = Field(None, description="查询失败时的错误信息")


class JobMatchRequest(BaseModel):
    """POST /v1/jobs/match 请求（也可通过 /v1/ask 的 job_match 意图触发）。"""
    resume_text: str = Field(..., description="简历全文或摘要")
    top_n: Optional[int] = Field(5, ge=1, le=20, description="返回前 N 条匹配")
    source: Optional[str] = Field(None, description="职位源：mock | apify_linkedin，不传用配置")


class JobMatchResponse(BaseModel):
    """POST /v1/jobs/match 响应。"""
    matches: list[dict[str, Any]] = Field(default_factory=list, description="按综合分排序的匹配列表")
    total_evaluated: int = Field(0, description="参与打分的职位数")
    message: Optional[str] = None
    error: Optional[str] = None
