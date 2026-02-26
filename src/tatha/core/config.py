"""
配置：从环境变量读取，供中央大脑与各能力模块使用。
"""
import os
from pathlib import Path

# 可选加载 .env（若存在）：先项目根（与 pyproject.toml 同层），再当前工作目录
_env_paths = [
    Path(__file__).resolve().parents[2] / ".env",  # 从 src/tatha/core 往上的项目根
    Path.cwd() / ".env",
]
for _p in _env_paths:
    if _p.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(_p)
            break
        except Exception:
            pass

# 中央大脑：是否用 LLM 做意图解析（有任一 key 且为 true 时走 LLM，否则规则回退）
def use_llm_intent() -> bool:
    key = (
        os.getenv("OPENAI_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or os.getenv("DEEPSEEK_API_KEY")
    )
    use = os.getenv("TATHA_USE_LLM_INTENT", "true").lower() in ("true", "1", "yes")
    return bool(key) and use


def get_default_model() -> str:
    return os.getenv("TATHA_DEFAULT_MODEL", "openai/gpt-4o")


def get_extractors_schema_path() -> Path | None:
    """提取器/分类器 JSON schema 路径；为空则使用默认示例路径（若存在）。"""
    env_path = os.getenv("TATHA_EXTRACTORS_SCHEMA")
    if env_path:
        p = Path(env_path)
        return p if p.exists() else None
    default = Path(__file__).resolve().parents[2] / "config" / "extractors_schema.example.json"
    return default if default.exists() else None


def document_analysis_backend() -> str:
    """文档解读后端：pydantic_ai（类型安全边界，默认）或 marvin（由 JSON schema 动态生成）。"""
    return (os.getenv("TATHA_DOCUMENT_ANALYSIS_BACKEND") or "pydantic_ai").strip().lower()


def embed_model_type() -> str:
    """
    索引/检索用的 embedding 模型类型。
    openai = 使用 OpenAI embedding（需 OPENAI_API_KEY）；
    local = 使用本地 HuggingFace（无需 API Key，适配仅配置 DeepSeek 的场景）。
    """
    return (os.getenv("TATHA_EMBED_MODEL") or "local").strip().lower()


def get_index_storage_root() -> Path:
    """
    私有索引存储根目录（简历等敏感数据仅存于此，不提交到仓库）。
    默认：项目根（与 pyproject.toml 同层）下的 .data/indices；可通过 TATHA_INDEX_STORAGE 覆盖。
    """
    env_path = os.getenv("TATHA_INDEX_STORAGE")
    if env_path:
        return Path(env_path)
    # src/tatha/core/config.py -> parents[3] = 项目根
    return Path(__file__).resolve().parents[3] / ".data" / "indices"
