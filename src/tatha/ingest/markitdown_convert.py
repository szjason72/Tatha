"""
MarkItDown：多格式文档统一转 Markdown。

支持 Word、Excel、PDF、PPT 等，便于后续 Marvin 提取、LlamaIndex 索引等。
扫描件或复杂图片表格解析效果会有波动，主要处理文字层。
"""
from __future__ import annotations

import io
import os
from pathlib import Path
from typing import BinaryIO

from markitdown import MarkItDown
from markitdown._base_converter import DocumentConverterResult
from markitdown._stream_info import StreamInfo


_converter_instance: MarkItDown | None = None


def _converter() -> MarkItDown:
    """单例式获取转换器，避免重复初始化。"""
    global _converter_instance
    if _converter_instance is None:
        _converter_instance = MarkItDown()
    return _converter_instance


def convert_file(path: str | Path) -> DocumentConverterResult:
    """
    将本地文件转为 Markdown。
    path: 本地路径（.pdf / .docx / .xlsx 等）。
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    return _converter().convert(str(path))


def convert_stream(
    stream: BinaryIO,
    *,
    filename: str | None = None,
    file_extension: str | None = None,
) -> DocumentConverterResult:
    """
    将二进制流（如上传文件内容）转为 Markdown。
    filename: 原始文件名，用于推断类型（如 resume.pdf）。
    file_extension: 若已知扩展名可直接传入（如 .pdf）；否则从 filename 推断。
    """
    ext = file_extension
    if not ext and filename:
        ext = os.path.splitext(filename)[1]
    stream_info = StreamInfo(extension=ext or None, filename=filename) if (ext or filename) else None
    return _converter().convert_stream(stream, stream_info=stream_info, file_extension=ext)


def file_to_markdown(path: str | Path) -> str:
    """便捷：本地文件 → Markdown 字符串。"""
    return convert_file(path).markdown


def stream_to_markdown(
    stream: BinaryIO,
    *,
    filename: str | None = None,
    file_extension: str | None = None,
) -> str:
    """便捷：二进制流 → Markdown 字符串。"""
    return convert_stream(
        stream, filename=filename, file_extension=file_extension
    ).markdown
