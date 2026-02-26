"""
LiteLLM 统一多平台模型调用：一套请求逻辑、一套错误处理，换模型只改 model 字符串。

环境变量（任选其一即可）：OPENAI_API_KEY、ANTHROPIC_API_KEY、DEEPSEEK_API_KEY 等，
LiteLLM 会自动读取，无需在代码里区分厂商。
模型名使用 LiteLLM 格式，例如：openai/gpt-4o、anthropic/claude-3-5-sonnet、deepseek/deepseek-chat。
"""
from __future__ import annotations

from typing import Any

from tatha.core.config import get_default_model


def completion(
    model: str | None = None,
    messages: list[dict[str, str]] | None = None,
    **kwargs: Any,
) -> Any:
    """
    统一 completion 调用：GPT、Claude、DeepSeek 等逻辑完全一致。
    model: 不传则使用 TATHA_DEFAULT_MODEL。
    messages: [{"role": "user", "content": "..."}] 或含 system 的多轮消息。
    返回 litellm 的 response，调用方取 response.choices[0].message.content。
    """
    from litellm import completion as litellm_completion

    model = model or get_default_model()
    if not messages:
        messages = [{"role": "user", "content": ""}]
    return litellm_completion(model=model, messages=messages, **kwargs)


def ask_ai(
    prompt: str,
    model: str | None = None,
    system: str | None = None,
    **kwargs: Any,
) -> str:
    """
    单轮问答：传入用户 prompt，返回模型回复正文。
    换模型只需改 model 字符串（或用默认）。
    """
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt or ""})
    resp = completion(model=model, messages=messages, **kwargs)
    return (resp.choices[0].message.content or "").strip()
