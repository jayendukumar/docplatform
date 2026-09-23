"""Small, deterministic, CPU-only render contract used until E4-01 selects a PDF engine."""
from __future__ import annotations

import html
from typing import Any

from app.template_logic import format_value, interpolate, render_blocks, resolve_path, validate_data

SUPPORTED_SCRIPTS = ("arabic", "hebrew", "devanagari", "tamil", "thai", "cjk", "latin")
SCRIPT_STACKS = {
    "arabic": "Noto Naskh Arabic, Noto Sans Arabic, sans-serif",
    "hebrew": "Noto Sans Hebrew, sans-serif",
    "devanagari": "Noto Sans Devanagari, sans-serif",
    "tamil": "Noto Sans Tamil, sans-serif",
    "thai": "Noto Sans Thai, sans-serif",
    "cjk": "Noto Sans CJK SC, Noto Sans CJK JP, sans-serif",
    "latin": "Noto Sans, sans-serif",
}

_RANGES = {
    "arabic": ((0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF)),
    "hebrew": ((0x0590, 0x05FF),),
    "devanagari": ((0x0900, 0x097F),),
    "tamil": ((0x0B80, 0x0BFF),),
    "thai": ((0x0E00, 0x0E7F),),
    "cjk": ((0x2E80, 0x9FFF), (0xF900, 0xFAFF)),
}


def script_for(char: str) -> str:
    code = ord(char)
    for script, ranges in _RANGES.items():
        if any(start <= code <= end for start, end in ranges):
            return script
    return "latin"


def scripts_in(text: str) -> list[str]:
    return sorted({script_for(char) for char in text if not char.isspace()})


def render_definition(definition: dict[str, Any], data: dict[str, Any] | None = None,
                      locale: str | None = None, missing_policy: str | None = None) -> dict[str, Any]:
    data = data or definition.get("sample_data", {})
    locale = locale or definition.get("locale", "en")
    policy = missing_policy or definition.get("missing_policy", "blank")
    if policy not in {"error", "blank", "placeholder"}:
        raise ValueError("missing_policy must be error, blank, or placeholder")
    validation_errors = validate_data(definition["data_schema"], data) if definition.get("data_schema") else []
    if validation_errors:
        raise ValueError({"message": "Render data failed schema validation", "errors": validation_errors})
    blocks = definition.get("blocks", [])
    missing: list[str] = []
    rendered = []
    seen_scripts: set[str] = set()
    for text in render_blocks(blocks, data, locale, policy, missing):
        seen_scripts.update(scripts_in(text))
        rendered.append(f'<p dir="auto">{html.escape(text)}</p>')
    stacks = [SCRIPT_STACKS[script] for script in sorted(seen_scripts)]
    css_stack = ", ".join(stacks) if stacks else SCRIPT_STACKS["latin"]
    page = definition.get("page", {})
    body = "".join(rendered)
    artifact = ("<!doctype html><html lang=\"" + html.escape(locale) + "\"><head>"
        "<meta charset=\"utf-8\"><style>body{font-family:" + css_stack + ";"
        "direction:auto;margin:" + str(page.get("margin_mm", 20)) + "mm;}"
        "p{white-space:pre-wrap;line-height:1.45;break-inside:avoid;}</style></head>"
        "<body>" + body + "</body></html>")
    return {"artifact": artifact, "content_type": "text/html", "locale": locale,
            "scripts": sorted(seen_scripts), "font_stacks": stacks, "missing_fields": missing,
            "missing_glyphs": [],
            "engine": "deterministic-html-0.1", "status": "candidate"}


def compare_candidates(fixtures: list[dict[str, Any]]) -> dict[str, Any]:
    results = []
    for fixture in fixtures:
        rendered = render_definition(fixture, fixture.get("sample_data", {}))
        results.append({"name": fixture.get("name", "fixture"), "engine": rendered["engine"],
                        "scripts": rendered["scripts"], "missing_glyphs": rendered["missing_glyphs"]})
    return {"status": "pending-native-review", "candidates": ["deterministic-html-0.1"],
            "results": results, "native_reader_scores": None}
