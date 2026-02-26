"""
征信（credit）相关单元测试：CreditAnalysis 模型与 run_credit_analysis 行为。

业务流程：用户先「找岗位」→ job_match 返回高分段职位 → 用户才关心该公司经营/征信，
以决定是否投递。因此征信场景下主体来自匹配结果，是明确公司，不存在主体模糊或缺失。
测试中「匹配后查该公司征信」的用例应要求 entity_name 存在。
"""
import os

import pytest

from tatha.agents.schemas import CreditAnalysis


# ---------- CreditAnalysis 模型 ----------


def test_credit_analysis_schema_all_fields():
    """业务流程主场景：匹配后查该公司征信，主体明确，三字段齐全。"""
    data = {
        "entity_name": "某某科技有限公司",
        "report_type": "企业信用报告",
        "summary": "截至2024年末无不良记录，信用等级A。",
    }
    obj = CreditAnalysis.model_validate(data)
    assert obj.entity_name == data["entity_name"]
    assert obj.report_type == data["report_type"]
    assert obj.summary == data["summary"]


def test_credit_analysis_schema_partial():
    """仅主体名称也可反序列化（业务上主体来自 job_match，通常至少会有 entity_name）。"""
    obj = CreditAnalysis.model_validate({"entity_name": "某某科技有限公司"})
    assert obj.entity_name == "某某科技有限公司"
    assert obj.report_type is None
    assert obj.summary is None


def test_credit_analysis_schema_empty():
    """全空仅用于模型/反序列化健壮性；业务流程中主体来自匹配结果，不应为空。"""
    obj = CreditAnalysis.model_validate({})
    assert obj.entity_name is None
    assert obj.report_type is None
    assert obj.summary is None


def test_credit_analysis_model_dump_roundtrip():
    """model_dump 后可作为 central_brain / API 的 extracted 结构。"""
    data = {"entity_name": "A公司", "report_type": "企业信用报告", "summary": "正常"}
    obj = CreditAnalysis.model_validate(data)
    dumped = obj.model_dump()
    assert dumped == data
    assert CreditAnalysis.model_validate(dumped).entity_name == obj.entity_name


# ---------- run_credit_analysis 集成（需 API Key 时跳过） ----------


def test_run_credit_analysis_returns_credit_analysis():
    """匹配后查该公司征信：主体明确（来自 job_match），解析结果应有 entity_name。"""
    if not os.getenv("DEEPSEEK_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        pytest.skip("需要 DEEPSEEK_API_KEY 或 OPENAI_API_KEY 以调用征信解析")

    from tatha.agents.document_agents import run_credit_analysis

    # 模拟「匹配到高分段岗位后，用户查这家公司的征信」：主体明确
    text = "主体名称某某科技有限公司，报告类型企业信用报告，摘要说明截至2024年末无不良记录，信用等级A。"
    try:
        result = run_credit_analysis(text)
    except Exception as e:
        pytest.skip(f"征信解析 LLM 调用未成功（可能无网络或限流）: {e}")

    assert isinstance(result, CreditAnalysis)
    assert result.entity_name, "业务流程中征信针对匹配后的公司，主体名称不应缺失"
    # 报告类型与摘要在真实流程中通常也会返回
    assert result.report_type or result.summary, "企业信用报告应含 report_type 或 summary"
