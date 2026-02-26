"""
单入口 /v1/ask 的请求与响应模型。
"""
from pydantic import BaseModel, Field
from typing import Any, Optional


class AskRequest(BaseModel):
    """用户/助理发往中央大脑的请求。"""
    message: str = Field(..., description="用户输入或意图描述")
    context: Optional[dict[str, Any]] = Field(default_factory=dict, description="可选上下文（user_id、session_id 等）")


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
