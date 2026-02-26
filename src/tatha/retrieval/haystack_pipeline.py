"""
Haystack：端到端检索/生成流水线，检索、排序、过滤可像搭积木一样组合。

适用于需要多组件编排（如 Retriever + Reranker + Generator）或对接 Qdrant/Elasticsearch 等向量库的场景。
当前提供最小示例：PromptBuilder + Generator；可扩展为「检索 → 排序 → 生成」完整链路。
"""
from __future__ import annotations

import os
from typing import Any, Optional

from tatha.core.config import get_default_model


def build_query_pipeline(
    template: str = "回答以下问题：{{query}}",
    model: Optional[str] = None,
    api_base_url: Optional[str] = None,
) -> "Pipeline":
    """
    组装 Haystack 流水线：PromptBuilder + LLM Generator。
    model: 不传则用 TATHA_DEFAULT_MODEL；api_base_url 不传则用 OPENAI 默认（可设 DEEPSEEK 等）。
    """
    from haystack import Pipeline
    from haystack.components.builders import PromptBuilder
    from haystack.components.generators import OpenAIGenerator

    model_name = model or get_default_model()
    # OpenAI 兼容 API：DeepSeek 等可设 OPENAI_API_BASE 或传入 api_base_url
    base_url = api_base_url or os.getenv("OPENAI_API_BASE")
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or ""
    # 若用 DeepSeek，模型名取 deepseek/deepseek-chat 后半或完整
    generator = OpenAIGenerator(
        model=model_name.split("/")[-1] if "/" in model_name else model_name,
        api_key=api_key or None,
        api_base_url=base_url,
    )
    pipe = Pipeline()
    pipe.add_component("prompt_builder", PromptBuilder(template=template))
    pipe.add_component("llm", generator)
    pipe.connect("prompt_builder", "llm")
    return pipe


def run_query_pipeline(
    query: str,
    template: Optional[str] = None,
    **pipeline_kwargs: Any,
) -> str:
    """
    运行「问题 → 回答」流水线，返回第一个回复文本。
    需要配置 OPENAI_API_KEY 或 DEEPSEEK_API_KEY；用 DeepSeek 时建议设 OPENAI_API_BASE=https://api.deepseek.com。
    """
    pipe = build_query_pipeline(template=template or "回答：{{query}}", **pipeline_kwargs)
    res = pipe.run({"prompt_builder": {"query": query}})
    replies = (res.get("llm") or {}).get("replies") or []
    return (replies[0] or "").strip() if replies else ""
