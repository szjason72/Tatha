"""
PydanticAI 文档解读智能体：result_type 定义数据边界，AI 只返回结构化结果，避免「好的，这是你要的 JSON」导致解析崩溃。
模型通过 LiteLLM 统一切换（openai/deepseek/anthropic 等）。
"""
from __future__ import annotations

from typing import Any

from tatha.core.config import get_default_model
from .schemas import ResumeAnalysis, PoetryAnalysis, CreditAnalysis


def _model():
    """LiteLLM 模型实例，与 TATHA_DEFAULT_MODEL 一致。"""
    from pydantic_ai_litellm import LiteLLMModel
    return LiteLLMModel(model_name=get_default_model())


def _resume_agent():
    from pydantic_ai import Agent
    return Agent(
        model=_model(),
        output_type=ResumeAnalysis,
        system_prompt=(
            "你是一个简历解析器。根据用户提供的简历文本，提取并仅返回结构化信息："
            "姓名、学历或毕业院校、技能关键词（逗号分隔）、工作经历摘要。"
            "不要输出任何解释或前缀（如「好的」「这是」），只输出符合 ResumeAnalysis 的 JSON 结构。"
        ),
    )


def _poetry_agent():
    from pydantic_ai import Agent
    return Agent(
        model=_model(),
        output_type=PoetryAnalysis,
        system_prompt=(
            "你是一个诗词/赏析解析器。根据用户提供的诗词或赏析文本，提取并仅返回结构化信息："
            "诗词标题、作者、朝代、正文或摘录句、主题或情感（如送别、思乡）。"
            "不要输出任何解释或前缀，只输出符合 PoetryAnalysis 的 JSON 结构。"
        ),
    )


def _credit_agent():
    from pydantic_ai import Agent
    return Agent(
        model=_model(),
        output_type=CreditAnalysis,
        system_prompt=(
            "你是一个征信/信用文本解析器。根据用户提供的文本，提取并仅返回结构化信息："
            "主体名称、报告类型、摘要说明。不要输出任何解释或前缀，只输出符合 CreditAnalysis 的 JSON 结构。"
        ),
    )


# 懒加载单例，避免重复创建 Agent
_agents: dict[str, Any] = {}


def _get_agent(name: str):
    if name not in _agents:
        if name == "resume":
            _agents[name] = _resume_agent()
        elif name == "poetry":
            _agents[name] = _poetry_agent()
        elif name == "credit":
            _agents[name] = _credit_agent()
        else:
            raise ValueError(f"未知文档类型: {name}，支持 resume / poetry / credit")
    return _agents[name]


def run_resume_analysis(text: str) -> ResumeAnalysis:
    """简历解读：类型安全，返回 ResumeAnalysis。"""
    agent = _get_agent("resume")
    result = agent.run_sync(text)
    return result.output


def run_poetry_analysis(text: str) -> PoetryAnalysis:
    """诗词/赏析解读：类型安全，返回 PoetryAnalysis。"""
    agent = _get_agent("poetry")
    result = agent.run_sync(text)
    return result.output


def run_credit_analysis(text: str) -> CreditAnalysis:
    """征信文本解读：类型安全，返回 CreditAnalysis。"""
    agent = _get_agent("credit")
    result = agent.run_sync(text)
    return result.output


def run_document_analysis(document_type: str, text: str) -> ResumeAnalysis | PoetryAnalysis | CreditAnalysis:
    """统一入口：按 document_type 调用对应智能体，返回类型化结果。"""
    agent = _get_agent(document_type)
    result = agent.run_sync(text)
    return result.output
