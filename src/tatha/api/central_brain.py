"""
中央大脑：意图解析 + 分发到内部能力端口。

设计原则：不以占位为长期方案。中央大脑需结合 LLM 进化——意图解析、多轮理解、
编排与反思均可由 LLM 承担，通过改 Prompt 或模型即可迭代；规则仅作无 key 或
LLM 失败时的回退，保证链路可跑通。
"""
import json
import re
from typing import Any

from tatha.core.config import use_llm_intent
from tatha.core.llm import completion as llm_completion
from .schemas import AskRequest, AskResponse

# 支持的意图（与 LLM 的 system prompt 一致，便于进化）
INTENTS = ("job_match", "resume_upload", "poetry", "credit", "mbti", "unknown")

# 规则回退：关键词 → 意图（仅当 LLM 未启用或失败时使用）
INTENT_KEYWORDS = {
    "job_match": ["匹配", "职位", "找工作", "推荐", "有没有适合", "岗位"],
    "resume_upload": ["上传", "简历", "解析简历"],
    "poetry": ["诗词", "诗人", "古诗", "推荐一句", "陪伴", "安慰"],
    "credit": ["征信", "信用", "验证"],
    "mbti": ["人格", "MBTI", "测评", "性格"],
}


def _parse_intent_llm(message: str) -> tuple[str, float, dict[str, Any]] | None:
    """
    用 LLM 解析意图（主路径）。返回 (intent, confidence, slots) 或 None（失败时回退）。
    通过改 prompt 或模型即可让中央大脑进化，无需改代码逻辑。
    """
    try:
        system = (
            "你是一个意图分类器。根据用户输入，输出且仅输出一个 JSON 对象，不要其他文字。"
            "JSON 必须包含：\"intent\"（取值仅限: job_match, resume_upload, poetry, credit, mbti, unknown），"
            "\"confidence\"（0 到 1 的浮点数），可选 \"slots\"（对象，如 {\"query\": \"...\"}）。"
            "job_match=求职/职位匹配，resume_upload=上传或解析简历，poetry=诗词/诗人/陪伴，credit=征信/验证，mbti=人格测评。"
        )
        resp = llm_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": message.strip() or "（无输入）"},
            ],
        )
        text = (resp.choices[0].message.content or "").strip()
        # 允许被 markdown 代码块包裹
        if "```" in text:
            m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
            if m:
                text = m.group(1).strip()
        data = json.loads(text)
        intent = (data.get("intent") or "unknown").lower()
        if intent not in INTENTS:
            intent = "unknown"
        confidence = float(data.get("confidence", 0.5))
        slots = data.get("slots") if isinstance(data.get("slots"), dict) else {}
        return (intent, confidence, slots)
    except Exception:
        return None


def _parse_intent_rules(message: str) -> str:
    """规则回退：关键词匹配。"""
    msg = (message or "").strip().lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(kw in msg for kw in keywords):
            return intent
    return "unknown"


def parse_intent(message: str) -> tuple[str, float, dict[str, Any]]:
    """
    解析用户消息得到意图 + 置信度 + 槽位。
    主路径：LLM（可进化）；回退：规则（保证无 key 时也能跑）。
    """
    if use_llm_intent():
        out = _parse_intent_llm(message)
        if out is not None:
            return out
    intent = _parse_intent_rules(message)
    return (intent, 0.8 if intent != "unknown" else 0.3, {})


def _document_analysis(document_type: str, text: str) -> dict[str, Any] | None:
    """
    文档解读：优先 PydanticAI（result_type 数据边界），回退 Marvin（JSON schema 动态）。
    返回可序列化的 dict，无有效结果时返回 None。
    """
    from tatha.core.config import document_analysis_backend
    backend = document_analysis_backend()
    if backend == "pydantic_ai":
        try:
            from tatha.agents import run_document_analysis
            data = run_document_analysis(document_type, text)
            return data.model_dump() if data else None
        except Exception:
            backend = "marvin"
    if backend == "marvin":
        _ensure_extractors_loaded()
        from tatha.ai.fn_from_schema import get_extractor
        extract_fn = get_extractor(document_type)
        if not extract_fn:
            return None
        out = extract_fn(text)
        if out and not out.get("_placeholder"):
            return out
    return None


def _ensure_extractors_loaded() -> None:
    """懒加载：若尚未根据 schema 生产函数，则加载默认或配置的 schema 并生产。"""
    from tatha.ai.fn_from_schema import REGISTRY
    if REGISTRY.get("_loaded"):
        return
    from tatha.core.config import get_extractors_schema_path
    path = get_extractors_schema_path()
    if path:
        from tatha.ai.fn_from_schema import load_and_produce
        load_and_produce(path=path)
    REGISTRY["_loaded"] = True


def dispatch(intent: str, request: AskRequest, slots: dict[str, Any] | None = None) -> dict[str, Any]:
    """按意图分发到内部能力端口，返回 result 字典（能力实现可逐步接入）。"""
    slots = slots or {}
    text = (request.message or "").strip() or (slots.get("text") or slots.get("content") or "")

    if intent == "job_match":
        return {"message": "匹配服务开发中", "status": "pending", "hint": "V0 将接入职位匹配 API", "slots": slots}
    if intent == "resume_upload":
        if text:
            try:
                extracted = _document_analysis("resume", text)
                if extracted is not None:
                    return {"message": "已解析简历结构化信息", "status": "ok", "extracted": extracted, "slots": slots}
                return {"message": "简历解析未返回结果", "status": "pending", "hint": "请检查 .env 中 OPENAI/DEEPSEEK 等 API Key 及 TATHA_DOCUMENT_ANALYSIS_BACKEND", "slots": slots}
            except Exception as e:
                return {"message": "简历解析失败", "status": "error", "error": str(e), "slots": slots}
        return {"message": "简历上传与解析服务开发中", "status": "pending", "hint": "V0 将接入 MarkItDown + 解析", "slots": slots}
    if intent == "poetry":
        if text:
            try:
                extracted = _document_analysis("poetry", text)
                if extracted is not None:
                    return {"message": "已解析诗词相关信息", "status": "ok", "extracted": extracted, "slots": slots}
            except Exception as e:
                return {"message": "诗词解析失败", "status": "error", "error": str(e), "slots": slots}
        return {"message": "诗人/诗词推荐开发中", "status": "pending", "hint": "将接入 poetry-knowledge-base RAG", "slots": slots}
    if intent == "credit":
        if text:
            try:
                extracted = _document_analysis("credit", text)
                if extracted is not None:
                    return {"message": "已解析征信相关信息", "status": "ok", "extracted": extracted, "slots": slots}
                return {"message": "征信解析未返回结果", "status": "pending", "hint": "请检查 API Key 与 TATHA_DOCUMENT_ANALYSIS_BACKEND", "slots": slots}
            except Exception as e:
                return {"message": "征信解析失败", "status": "error", "error": str(e), "slots": slots}
        return {"message": "征信/验证服务开发中", "status": "pending", "slots": slots}
    if intent == "mbti":
        return {"message": "职业人格测评开发中", "status": "pending", "slots": slots}
    return {"message": "暂未识别到明确意图", "status": "unknown", "received": (request.message or "")[:100]}


def handle_ask(request: AskRequest) -> AskResponse:
    """单入口处理：解析意图（LLM 主路径 + 规则回退）→ 分发 → 统一响应。"""
    intent, confidence, slots = parse_intent(request.message)
    result = dispatch(intent, request, slots)
    result["confidence"] = confidence
    suggestions = []
    if intent == "unknown":
        suggestions.append("可以说：帮我匹配职位、上传简历、推荐一句诗 等")
    return AskResponse(intent=intent, result=result, suggestions=suggestions)
