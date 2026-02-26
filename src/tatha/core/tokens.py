"""
tiktoken：请求前算账，精准计算 Token 消耗，控制单次调用与月度成本。

使用前可对 prompt / 回复做 token 计数，避免超长请求导致意外扣费。
"""
from __future__ import annotations

from typing import Optional

# 常用模型与 tiktoken 编码的映射（OpenAI 兼容 API 多用 cl100k_base）
_MODEL_ENCODING = {
    "gpt-4o": "cl100k_base",
    "gpt-4o-mini": "cl100k_base",
    "gpt-4": "cl100k_base",
    "gpt-4-turbo": "cl100k_base",
    "gpt-3.5-turbo": "cl100k_base",
    "deepseek": "cl100k_base",  # DeepSeek 兼容 cl100k_base 估算
}
_DEFAULT_ENCODING = "cl100k_base"


def _get_encoding_for_model(model_name: Optional[str] = None) -> "tiktoken.Encoding | None":
    """根据模型名获取 tiktoken 编码；未知模型用 cl100k_base。失败时返回 None（count_tokens 用近似）。"""
    import tiktoken
    try:
        if not model_name:
            return tiktoken.get_encoding(_DEFAULT_ENCODING)
        name = (model_name or "").strip().lower()
        for key, enc in _MODEL_ENCODING.items():
            if key in name:
                return tiktoken.get_encoding(enc)
        try:
            return tiktoken.encoding_for_model(name.split("/")[-1] if "/" in name else name)
        except Exception:
            return tiktoken.get_encoding(_DEFAULT_ENCODING)
    except Exception:
        return None


def count_tokens(
    text: str,
    model_name: Optional[str] = None,
) -> int:
    """
    计算文本的 token 数量，用于请求前成本预估。
    model_name: 可选，如 openai/gpt-4o、deepseek/deepseek-chat；不传则用 cl100k_base。
    若 tiktoken 不可用（如无网络加载编码表），回退为约 len(text)//2 的近似值。
    """
    if not text:
        return 0
    enc = _get_encoding_for_model(model_name)
    if enc is not None:
        return len(enc.encode(text))
    return max(1, len(text) // 2)


def estimate_input_cost(
    text: str,
    model_name: Optional[str] = None,
    price_per_1k_input: Optional[float] = None,
) -> tuple[int, float]:
    """
    估算单次输入 token 数与成本（美元）。
    price_per_1k_input: 每 1k input token 价格（美元），不传则只返回 token 数、成本为 0。
    常用参考：gpt-4o 约 0.0025，deepseek-chat 约 0.00014。
    """
    n = count_tokens(text, model_name=model_name)
    cost = 0.0
    if price_per_1k_input is not None and price_per_1k_input > 0:
        cost = (n / 1000.0) * price_per_1k_input
    return n, cost
