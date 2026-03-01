"""
V1 阶段 7：创建托管支付结账（Lemon Squeezy）。

POST /v1/orders/checkout：需鉴权，入参 tier/interval/return_url，返回 checkout_url。
未配置 LEMON_SQUEEZY_API_KEY 或对应 Variant 时返回 stub URL，便于本地跑通流程。
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from fastapi import HTTPException

from .auth import AuthContext
from .schemas import CheckoutRequest, CheckoutResponse


def _variant_id(tier: str, interval: str) -> str | None:
    """从环境变量取 Lemon Squeezy Variant ID；tier=basic|pro，interval=month|year。"""
    key = f"LEMON_SQUEEZY_VARIANT_{tier.upper()}_{interval.upper()}"
    return os.environ.get(key, "").strip() or None


def _store_id() -> str | None:
    return os.environ.get("LEMON_SQUEEZY_STORE_ID", "").strip() or None


def _api_key() -> str | None:
    return os.environ.get("LEMON_SQUEEZY_API_KEY", "").strip() or None


def create_checkout(auth: AuthContext, body: CheckoutRequest) -> CheckoutResponse:
    """
    创建结账：若已配置 Lemon Squeezy 则调用 API 返回真实 checkout_url；
    否则返回 stub URL（前端可跳转后用于 stub Webhook 测试）。
    """
    tier = (body.tier or "").strip().lower()
    interval = (body.interval or "month").strip().lower()
    if tier not in ("basic", "pro"):
        raise HTTPException(status_code=400, detail="tier 必须为 basic 或 pro")
    if interval not in ("month", "year"):
        raise HTTPException(status_code=400, detail="interval 必须为 month 或 year")

    api_key = _api_key()
    store_id = _store_id()
    variant_id = _variant_id(tier, interval)

    if not api_key or not store_id or not variant_id:
        # Stub：返回同源占位页，便于前端跳转 + 后续用 stub Webhook 验证档位更新
        base = os.environ.get("TATHA_PUBLIC_URL", "http://localhost:8010").strip().rstrip("/")
        return_url = (body.return_url or f"{base}/index.html").strip()
        stub = f"{base}/index.html?stub_checkout=1&tier={tier}&interval={interval}&user_id={auth.user_id}&return_url={urllib.parse.quote(return_url)}"
        return CheckoutResponse(checkout_url=stub, tier=tier, interval=interval)

    # Lemon Squeezy: POST /v1/checkouts
    payload: dict[str, Any] = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": {
                    "custom": {"user_id": auth.user_id},
                },
                "product_options": {},
            },
            "relationships": {
                "store": {"data": {"type": "stores", "id": store_id}},
                "variant": {"data": {"type": "variants", "id": str(variant_id)}},
            },
        },
    }
    if body.return_url:
        payload["data"]["attributes"]["product_options"]["redirect_url"] = body.return_url

    req = urllib.request.Request(
        "https://api.lemonsqueezy.com/v1/checkouts",
        data=json.dumps(payload).encode(),
        headers={
            "Accept": "application/vnd.api+json",
            "Content-Type": "application/vnd.api+json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_read = e.read().decode() if e.fp else ""
        raise HTTPException(
            status_code=502,
            detail=f"Lemon Squeezy 创建结账失败: {e.code} {body_read[:200]}",
        )
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise HTTPException(status_code=502, detail=f"调用支付平台失败: {e}")

    attrs = (data.get("data") or {}).get("attributes") or {}
    url = attrs.get("url") or ""
    if not url:
        raise HTTPException(status_code=502, detail="支付平台未返回 checkout URL")
    return CheckoutResponse(checkout_url=url, tier=tier, interval=interval)
