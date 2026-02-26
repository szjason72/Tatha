"""
文档解读结果的数据边界：Pydantic 模型，保证 AI 只返回结构化字段、不夹带「好的，这是你要的 JSON」等导致解析崩溃的文本。
"""
from pydantic import BaseModel, Field
from typing import Optional


class ResumeAnalysis(BaseModel):
    """简历解读结果：类型安全边界。"""
    name: Optional[str] = Field(None, description="姓名")
    education: Optional[str] = Field(None, description="学历或毕业院校")
    skills: Optional[str] = Field(None, description="技能关键词，逗号分隔")
    experience_summary: Optional[str] = Field(None, description="工作经历摘要")


class PoetryAnalysis(BaseModel):
    """诗词/赏析解读结果：类型安全边界。"""
    title: Optional[str] = Field(None, description="诗词标题")
    author: Optional[str] = Field(None, description="作者")
    dynasty: Optional[str] = Field(None, description="朝代")
    content: Optional[str] = Field(None, description="正文或摘录句")
    theme: Optional[str] = Field(None, description="主题或情感，如送别、思乡")


class CreditAnalysis(BaseModel):
    """征信/信用相关文本解读结果：类型安全边界。"""
    entity_name: Optional[str] = Field(None, description="主体名称")
    report_type: Optional[str] = Field(None, description="报告类型")
    summary: Optional[str] = Field(None, description="摘要说明")
