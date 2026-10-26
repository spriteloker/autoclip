"""Consistent Simplified Chinese output for model-generated copy and saved drafts."""
from __future__ import annotations

from typing import Any
import re

_converter = None
_KANA = re.compile(r'[\u3040-\u30ff]')
_JAPANESE_CORPORATE_TITLE = re.compile(r'経営責任者')


def simplified_chinese(text: str) -> str:
    global _converter
    if not text or _KANA.search(text) or _JAPANESE_CORPORATE_TITLE.search(text):
        return text
    if _converter is None:
        from opencc import OpenCC
        _converter = OpenCC('t2s')
    return _converter.convert(text)


def simplified_payload(value: Any) -> Any:
    if isinstance(value, str):
        return simplified_chinese(value)
    if isinstance(value, list):
        return [simplified_payload(item) for item in value]
    if isinstance(value, tuple):
        return tuple(simplified_payload(item) for item in value)
    if isinstance(value, dict):
        return {key: simplified_payload(item) for key, item in value.items()}
    return value
