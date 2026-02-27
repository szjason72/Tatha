"""
V1 地区与定价：根据请求 IP 返回 country、currency、locale、pricing，供订阅页按地区展示价格。

与《按地区区分定价与币种_参考ServBay》一致；国内（CN）返回人民币与 pricing_cn，境外返回美元与 pricing_intl。
"""
import json
import os
import urllib.error
import urllib.request
from typing import Any

from fastapi import Request

# 默认两套定价（可被环境变量覆盖，见 get_pricing）
PRICING_CN: dict[str, Any] = {
    "currency": "CNY",
    "basic_monthly": 99,
    "basic_yearly": 599,
    "pro_monthly": 199,
    "pro_yearly": 1199,
}
PRICING_INTL: dict[str, Any] = {
    "currency": "USD",
    "basic_monthly": 9.9,
    "basic_yearly": 59,
    "pro_monthly": 19.9,
    "pro_yearly": 119,
}


def get_client_ip(request: Request) -> str:
    """从请求取客户端 IP：X-Forwarded-For 最左端 > X-Real-IP > request.client.host。"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real = request.headers.get("X-Real-IP")
    if real:
        return real.strip()
    if request.client:
        return request.client.host or "127.0.0.1"
    return "127.0.0.1"


def _is_private_ip(ip: str) -> bool:
    if not ip or ip == "127.0.0.1" or ip.startswith("192.168.") or ip.startswith("10."):
        return True
    if ip == "::1" or ip.startswith("fe80:"):
        return True
    return False


def _country_from_cdn(request: Request) -> str | None:
    """若在 Cloudflare 等 CDN 后，直接读注入的国家码。"""
    cf = request.headers.get("CF-IPCountry")
    if cf and len(cf) == 2:
        return cf.upper()
    return None


def _country_from_ip_api(ip: str) -> str | None:
    """调用 ip-api.com 解析国家码（免费、无需 key，有频率限制）。"""
    if _is_private_ip(ip):
        return None
    try:
        url = f"http://ip-api.com/json/{ip}?fields=countryCode"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status != 200:
                return None
            data = json.loads(resp.read().decode())
            cc = data.get("countryCode")
            return str(cc).upper() if cc else None
    except (urllib.error.URLError, OSError, ValueError):
        return None


def get_country(request: Request) -> str:
    """
    解析请求对应国家码：CDN 头 > 环境变量 TATHA_DEFAULT_REGION > ip-api.com。
    返回 "CN" 或其它两字母码；无法解析时默认 TATHA_DEFAULT_REGION，再否则 "US"。
    """
    country = _country_from_cdn(request)
    if country:
        return country
    default = os.environ.get("TATHA_DEFAULT_REGION", "").strip().upper()
    if default and len(default) >= 2:
        return default[:2]
    ip = get_client_ip(request)
    country = _country_from_ip_api(ip)
    if country:
        return country
    return default or "US"


def get_pricing(country: str) -> dict[str, Any]:
    """国内（CN）返回 pricing_cn，否则 pricing_intl；数值可由环境变量覆盖。"""
    is_cn = country.upper() == "CN"
    base = PRICING_CN if is_cn else PRICING_INTL
    out: dict[str, Any] = dict(base)
    prefix = "TATHA_PRICING_CN_" if is_cn else "TATHA_PRICING_INTL_"
    for key in ("basic_monthly", "basic_yearly", "pro_monthly", "pro_yearly"):
        env_key = prefix + key.upper()
        val = os.environ.get(env_key)
        if val is not None:
            try:
                out[key] = float(val) if "." in str(val) else int(val)
            except ValueError:
                pass
    return out


def get_region_response(request: Request, country_override: str | None = None) -> dict[str, Any]:
    """GET /v1/region 的响应体：country、currency、locale、pricing。可选 ?country=CN 或 ?region=intl 用于前端切换地区展示。"""
    raw = (country_override or request.query_params.get("country") or request.query_params.get("region") or "").strip().upper()
    if raw == "INTL" or raw == "US" or raw == "EN":
        country = "US"
    elif raw == "CN" or raw == "CNY" or raw == "ZH":
        country = "CN"
    elif len(raw) >= 2:
        country = raw[:2]
    else:
        country = get_country(request)
    pricing = get_pricing(country)
    currency = pricing.get("currency", "CNY" if country == "CN" else "USD")
    locale = "zh-CN" if country == "CN" else "en-US"
    return {
        "country": country,
        "currency": currency,
        "locale": locale,
        "pricing": pricing,
    }
