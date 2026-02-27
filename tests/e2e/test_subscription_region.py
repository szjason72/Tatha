"""
V1 阶段 3：订阅页按地区展示价格 — Playwright E2E。
要求：API 已启动（127.0.0.1:8010）。验证 index.html 加载 /v1/region 后展示正确币种与价格。
"""
import pytest
from playwright.sync_api import Page, expect


def test_subscription_page_loads_region_prices(page: Page, base_url: str):
    """打开订阅页，等待 /v1/region 生效后，应有价格数字与币种符号。"""
    page.goto(f"{base_url}/index.html")
    # 等待价格由接口填充（由 -- 变为数字）
    page.locator(".price-value").first.wait_for(state="visible")
    page.wait_for_function(
        "document.querySelectorAll('.price-value')[1]?.textContent !== '--' && document.querySelectorAll('.price-value')[2]?.textContent !== '--'",
        timeout=5000,
    )
    # Basic/Pro 至少有一个为数字
    basic_val = page.locator("[data-region-price='basic_monthly'] .price-value").text_content()
    pro_val = page.locator("[data-region-price='pro_monthly'] .price-value").text_content()
    assert basic_val and basic_val != "--", "基础版月价应由 /v1/region 填充"
    assert pro_val and pro_val != "--", "Pro 版月价应由 /v1/region 填充"
    # 币种符号应为 ¥ 或 $
    sym = page.locator(".currency-symbol").first.text_content()
    assert sym in ("¥", "$"), "应展示人民币或美元符号"


def test_subscription_page_has_pricing_cards(page: Page, base_url: str):
    """订阅页存在三档卡片与定价占位（不依赖接口即可通过）。"""
    page.goto(f"{base_url}/index.html")
    expect(page.locator("h1")).to_contain_text("可持续")
    expect(page.locator(".card")).to_have_count(3)
    expect(page.locator("[data-region-price='basic_monthly']")).to_be_visible()
    expect(page.locator("[data-region-price='pro_monthly']")).to_be_visible()
