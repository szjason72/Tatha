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
