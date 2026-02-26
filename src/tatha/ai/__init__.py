"""
AI 能力封装：从「解析后的 JSON」生产 Marvin 风格的提取/分类函数。

- document_types：按文档类型（resume、poetry、credit 等）生成 extract_xxx(text) -> 结构化结果
- classifiers：按分类任务生成 classify_xxx(text) -> 标签或 list[str]
"""
from .fn_from_schema import (
    load_schema,
    load_and_produce,
    produce_extractors,
    produce_classifiers,
    get_extractor,
    get_classifier,
    REGISTRY,
)

__all__ = [
    "load_schema",
    "load_and_produce",
    "produce_extractors",
    "produce_classifiers",
    "get_extractor",
    "get_classifier",
    "REGISTRY",
]
