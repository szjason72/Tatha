# 向量索引与检索（LlamaIndex + FAISS；可选 Haystack 流水线）

from .llama_index_rag import (
    build_index_from_dir,
    build_index_from_documents,
    load_index,
    get_query_engine,
    get_retriever,
)

def build_query_pipeline(*args: object, **kwargs: object) -> object:
    """Haystack 流水线：PromptBuilder + Generator。懒加载避免 Haystack 初始化影响主路径。"""
    from .haystack_pipeline import build_query_pipeline as _build
    return _build(*args, **kwargs)

def run_query_pipeline(*args: object, **kwargs: object) -> str:
    """运行 Haystack 查询流水线。懒加载。"""
    from .haystack_pipeline import run_query_pipeline as _run
    return _run(*args, **kwargs)

__all__ = [
    "build_index_from_dir",
    "build_index_from_documents",
    "load_index",
    "get_query_engine",
    "get_retriever",
    "build_query_pipeline",
    "run_query_pipeline",
]
