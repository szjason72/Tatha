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
