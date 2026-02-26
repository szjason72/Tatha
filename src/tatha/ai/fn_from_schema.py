"""
从「解析后的 JSON」生产 Marvin 风格的提取/分类函数。

JSON 结构：
- document_types: { <type_name>: { description, fields: [ {name, type, description} ] } }
  -> 为每种文档类型生成 extract_<type_name>(text) -> 单条结构化结果（Pydantic 或 dict）
- classifiers: { <name>: { description, labels: [...] } }
  -> 生成 classify_<name>(text) -> 标签（或 multi_label 时 list[str]）

依赖：marvin.extract / marvin.classify；若未安装或不可用则注册为占位，调用时再报错。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import create_model

# 全局注册表：按名称取生产出的函数
REGISTRY: dict[str, Any] = {
    "extractors": {},   # document_type -> callable(text) -> dict | BaseModel
    "classifiers": {},  # name -> callable(text) -> label | list[str]
}


def _load_json(path: Path | str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_schema(path: Path | str | None = None, data: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    加载 schema：要么传 path（JSON 文件路径），要么传 data（已解析的 dict）。
    返回规范结构：{ document_types: {...}, classifiers: {...} }。
    """
    if data is not None:
        doc = data
    elif path is not None:
        doc = _load_json(Path(path))
    else:
        return {"document_types": {}, "classifiers": {}}
    return {
        "document_types": doc.get("document_types") or {},
        "classifiers": doc.get("classifiers") or {},
    }


def _pydantic_type_from_str(t: str):
    """将 JSON 里的 type 字符串转为 Pydantic 类型。"""
    t = (t or "string").strip().lower()
    if t in ("str", "string"):
        return str
    if t in ("int", "integer"):
        return int
    if t in ("float", "number"):
        return float
    if t in ("bool", "boolean"):
        return bool
    return str


def produce_extractors(schema: dict[str, Any]) -> dict[str, Any]:
    """
    根据 schema["document_types"] 生产提取函数，并写入 REGISTRY["extractors"]。
    每个函数签名：extract_xxx(text: str) -> dict | BaseModel，单条结果（list 取首项）。
    """
    document_types = schema.get("document_types") or {}
    try:
        import marvin
        from marvin.fns.extract import extract as marvin_extract
    except Exception:
        # Marvin 未安装或初始化失败（如 .marvin 权限），先占位
        for name in document_types:
            REGISTRY["extractors"][name] = _placeholder_extractor(name)
        return REGISTRY["extractors"]

    for doc_type, spec in document_types.items():
        description = spec.get("description") or f"从文本中提取{doc_type}相关信息"
        fields_spec = spec.get("fields") or []
        if not fields_spec:
            REGISTRY["extractors"][doc_type] = _placeholder_extractor(doc_type)
            continue

        # 动态 Pydantic 模型
        field_defs = {}
        for f in fields_spec:
            fn = f.get("name") or "field"
            typ = _pydantic_type_from_str(f.get("type"))
            field_defs[fn] = (typ, None)
        model_name = f"Extract{doc_type.replace('_', ' ').title().replace(' ', '')}"
        Model = create_model(model_name, **field_defs)

        instructions = description + "。字段说明：" + "；".join(
            f"{x.get('name')}: {x.get('description', '')}" for x in fields_spec
        )

        def _make_extract(target_model: type, instr: str, dtype: str):
            def extract_one(text: str):
                out = marvin_extract(text, target=target_model, instructions=instr)
                if isinstance(out, list) and len(out) > 0:
                    item = out[0]
                    return item.model_dump() if hasattr(item, "model_dump") else item
                return None
            extract_one.__name__ = f"extract_{dtype}"
            return extract_one

        REGISTRY["extractors"][doc_type] = _make_extract(Model, instructions, doc_type)

    return REGISTRY["extractors"]


def _placeholder_extractor(name: str):
    """占位：Marvin 不可用时返回提示。"""
    def _placeholder(text: str):
        return {"_placeholder": True, "document_type": name, "message": "Marvin 未配置或不可用，请配置后重试"}
    _placeholder.__name__ = f"extract_{name}"
    return _placeholder


def produce_classifiers(schema: dict[str, Any]) -> dict[str, Any]:
    """
    根据 schema["classifiers"] 生产分类函数，并写入 REGISTRY["classifiers"]。
    每个函数签名：classify_xxx(text: str) -> label | list[str]（multi_label 时）。
    """
    classifiers = schema.get("classifiers") or {}
    try:
        import marvin
        from marvin.fns.classify import classify as marvin_classify
    except Exception:
        for name in classifiers:
            REGISTRY["classifiers"][name] = _placeholder_classifier(name)
        return REGISTRY["classifiers"]

    for name, spec in classifiers.items():
        description = spec.get("description") or f"对文本进行分类"
        labels = spec.get("labels") or []
        multi = bool(spec.get("multi_label", False))
        if not labels:
            REGISTRY["classifiers"][name] = _placeholder_classifier(name)
            continue

        def _make_classify(lbls: list, instr: str, multi_label: bool, cname: str):
            def classify_one(text: str):
                return marvin_classify(text, labels=lbls, instructions=instr, multi_label=multi_label)
            classify_one.__name__ = f"classify_{cname}"
            return classify_one

        REGISTRY["classifiers"][name] = _make_classify(labels, description, multi, name)

    return REGISTRY["classifiers"]


def _placeholder_classifier(name: str):
    def _placeholder(text: str):
        return {"_placeholder": True, "classifier": name, "message": "Marvin 未配置或不可用"}
    _placeholder.__name__ = f"classify_{name}"
    return _placeholder


def get_extractor(document_type: str):
    """按文档类型名获取提取函数；若无则返回 None。"""
    return REGISTRY["extractors"].get(document_type)


def get_classifier(name: str):
    """按分类器名获取分类函数；若无则返回 None。"""
    return REGISTRY["classifiers"].get(name)


def load_and_produce(path: Path | str | None = None, data: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    加载 schema 并一次性生产所有提取器与分类器。
    返回 { "extractors": {...}, "classifiers": {...} }（与 REGISTRY 一致）。
    """
    schema = load_schema(path=path, data=data)
    produce_extractors(schema)
    produce_classifiers(schema)
    return REGISTRY
