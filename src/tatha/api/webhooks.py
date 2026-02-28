"""
V1 阶段 7：支付平台 Webhook（Lemon Squeezy）。

POST /v1/webhooks/payment：接收 Lemon Squeezy 的 order_created / subscription_created，
校验 X-Signature 后从 meta.custom_data.user_id 与订单 variant 解析档位并写入 tier_store。
"""
import hmac
import json
import os
from typing import Any

from fastapi import HTTPException, Request

from .tier_store import set_tier

# 从环境变量构建 variant_id -> tier（basic | pro）映射，与 orders.py 使用的 key 一致
def _variant_to_tier_map() -> dict[str, str]:
    out: dict[str, str] = {}
    for tier in ("basic", "pro"):
        for interval in ("monthly", "yearly"):
            key = f"LEMON_SQUEEZY_VARIANT_{tier.upper()}_{interval.upper()}"
            vid = os.environ.get(key, "").strip()
            if vid:
                out[vid] = tier
    return out


def _verify_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """Lemon Squeezy：X-Signature 为 HMAC-SHA256(body, secret) 的 hex。"""
    secret = os.environ.get("LEMON_SQUEEZY_WEBHOOK_SECRET", "").strip()
    if not secret or not signature_header:
        return False
    expected = hmac.new(secret.encode(), raw_body, "sha256").hexdigest()
    return hmac.compare_digest(expected, signature_header.strip())


def _tier_from_variant_id(variant_id: int | str) -> str | None:
    m = _variant_to_tier_map()
    return m.get(str(variant_id))


async def handle_payment_webhook(request: Request) -> dict[str, str]:
    """
    处理 POST /v1/webhooks/payment。需读取 raw body 校验签名，再解析 JSON。
    仅处理 order_created、subscription_created；成功则更新档位并返回 200。
    """
    raw = await request.body()
    sig = request.headers.get("X-Signature")
    if not _verify_signature(raw, sig):
        raise HTTPException(status_code=401, detail="invalid webhook signature")

    try:
        body = json.loads(raw.decode())
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="invalid JSON")

    meta = body.get("meta") or {}
    event_name = (meta.get("event_name") or request.headers.get("X-Event-Name") or "").strip()
    custom_data = meta.get("custom_data") or {}
    user_id = custom_data.get("user_id")
    if isinstance(user_id, (int, float)):
        user_id = str(int(user_id))
    if not user_id or not isinstance(user_id, str):
        # 无 user_id 时无法关联档位，仅确认收到
        return {"ok": True, "message": "no user_id in custom_data"}

    if event_name not in ("order_created", "subscription_created"):
        return {"ok": True, "message": f"event {event_name} ignored"}

    # 从订单首条 line item 取 variant_id，映射为 tier
    data = body.get("data") or {}
    attrs = data.get("attributes") or {}
    first_item = attrs.get("first_order_item") or {}
    variant_id = first_item.get("variant_id")
    if variant_id is None and data.get("type") == "subscriptions":
        # subscription 对象可能结构不同，尝试从 relationships 或 attributes 取
        variant_id = (attrs.get("variant_id") or attrs.get("first_order_item") or {}).get("variant_id")
    tier = _tier_from_variant_id(variant_id) if variant_id is not None else None
    if not tier:
        return {"ok": True, "message": "variant_id not mapped to tier"}

    set_tier(user_id, tier)
    return {"ok": True, "tier": tier, "user_id": user_id}


def _is_real_checkout_configured() -> bool:
    """与 orders 一致：仅当 API Key、Store ID、至少一个 Variant 都配置时才算「真实支付已配置」。"""
    from .orders import _api_key, _store_id, _variant_id
    return bool(_api_key() and _store_id() and _variant_id("basic", "month"))


def handle_stub_upgrade(user_id: str, tier: str) -> dict[str, str]:
    """
    仅当「未完整配置 Lemon Squeezy」（缺 Store ID 或 Variant 时）可用，用于本地 stub 验证档位更新链路。
    一旦配置了 API Key + Store ID + Variant，本接口返回 404，避免生产误用。
    POST /v1/webhooks/stub-upgrade，body: { "user_id": "...", "tier": "basic"|"pro" }。
    """
    if _is_real_checkout_configured():
        raise HTTPException(status_code=404, detail="stub upgrade disabled when payment is configured")
    if tier not in ("basic", "pro"):
        raise HTTPException(status_code=400, detail="tier must be basic or pro")
    if not user_id or not isinstance(user_id, str):
        raise HTTPException(status_code=400, detail="user_id required")
    set_tier(user_id, tier)
    return {"ok": True, "tier": tier, "user_id": user_id}
