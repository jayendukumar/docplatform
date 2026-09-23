"""Bounded, data-only template evaluation for the MVP render contract."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import re
from typing import Any, Callable


class TemplateDataError(ValueError):
    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Missing template field: {path}")


_PATH = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*|\[\d+\])*$")
_TOKEN = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")


def resolve_path(data: Any, path: str) -> tuple[Any, bool]:
    if not _PATH.fullmatch(path):
        raise ValueError(f"Unsupported template expression: {path}")
    value = data
    for match in re.finditer(r"[A-Za-z_][A-Za-z0-9_]*|\[(\d+)\]", path):
        key = (match.group(1) or match.group(0)).strip("[]")
        if isinstance(value, dict) and key in value:
            value = value[key]
        elif isinstance(value, list) and key.isdigit() and int(key) < len(value):
            value = value[int(key)]
        else:
            return "", False
    return value, True


def _missing(path: str, policy: str) -> Any:
    if policy == "error":
        raise TemplateDataError(path)
    if policy == "placeholder":
        return f"[[{path}]]"
    return ""


def _value(data: Any, path: str, policy: str) -> Any:
    value, found = resolve_path(data, path)
    return value if found and value is not None else _missing(path, policy)


def format_value(value: Any, locale: str, function: str | None = None) -> str:
    if value is None:
        return ""
    if function == "text":
        return str(value)
    if function in {"number", "currency", "percent"} or isinstance(value, (int, float, Decimal)):
        if function == "percent":
            value = Decimal(str(value)) * 100
        raw = f"{value:,.2f}" if function == "currency" else f"{value:,}"
        if locale.startswith(("de", "fr")):
            raw = raw.replace(",", "\u202f").replace(".", ",")
        return f"{raw} {('€' if locale.startswith('de') else '$')}" if function == "currency" else (raw + "%" if function == "percent" else raw)
    if function == "date" and isinstance(value, (date, datetime)):
        return value.strftime("%d/%m/%Y") if locale.startswith("en-GB") else value.isoformat()
    return str(value)


def interpolate(text: str, data: Any, locale: str, policy: str,
                on_missing: Callable[[str], None] | None = None) -> str:
    def replace(match: re.Match[str]) -> str:
        token = match.group(1).strip()
        function = None
        path = token
        function_match = re.fullmatch(r"(number|currency|date|percent|text)\(\s*([^()]+?)\s*\)", token)
        if function_match:
            function, path = function_match.groups()
        try:
            value, found = resolve_path(data, path)
        except ValueError:
            raise
        if not found or value is None:
            if on_missing:
                on_missing(path)
            value = _missing(path, policy)
        return format_value(value, locale, function)

    return _TOKEN.sub(replace, text)


def condition_matches(condition: Any, data: Any, policy: str) -> bool:
    if not isinstance(condition, dict):
        raise ValueError("condition must be an object")
    if "and" in condition:
        return all(condition_matches(item, data, policy) for item in condition["and"])
    if "or" in condition:
        return any(condition_matches(item, data, policy) for item in condition["or"])
    if "not" in condition:
        return not condition_matches(condition["not"], data, policy)
    path = condition.get("path")
    if not isinstance(path, str):
        raise ValueError("condition.path is required")
    actual = _value(data, path, policy)
    if "equals" in condition:
        return actual == condition["equals"]
    if "not_equals" in condition:
        return actual != condition["not_equals"]
    if "in" in condition:
        return actual in condition["in"]
    if "truthy" in condition:
        return bool(actual) is bool(condition["truthy"])
    raise ValueError("condition needs equals, not_equals, in, or truthy")


def validate_data(schema: dict[str, Any], data: Any, path: str = "") -> list[dict[str, str]]:
    """Validate the small JSON-Schema subset used by template requests."""
    errors: list[dict[str, str]] = []
    expected = schema.get("type")
    type_ok = {"object": isinstance(data, dict), "array": isinstance(data, list),
               "string": isinstance(data, str),
               "number": isinstance(data, (int, float, Decimal)) and not isinstance(data, bool),
               "integer": isinstance(data, int) and not isinstance(data, bool),
               "boolean": isinstance(data, bool)}
    if expected in type_ok and not type_ok[expected]:
        return [{"path": path or "$", "message": f"expected {expected}"}]
    if isinstance(data, dict):
        for required in schema.get("required", []):
            if required not in data:
                errors.append({"path": f"{path}.{required}".lstrip("."), "message": "is required"})
        for key, child in schema.get("properties", {}).items():
            if key in data and isinstance(child, dict):
                errors.extend(validate_data(child, data[key], f"{path}.{key}".lstrip(".")))
    if isinstance(data, list) and isinstance(schema.get("items"), dict):
        for index, item in enumerate(data):
            errors.extend(validate_data(schema["items"], item, f"{path}[{index}]"))
    return errors


def render_blocks(blocks: list[dict[str, Any]], data: Any, locale: str, policy: str,
                  missing: list[str]) -> list[str]:
    output: list[str] = []
    for block in blocks:
        kind = block.get("type", "text")
        if kind == "text":
            output.append(interpolate(str(block.get("text", "")), data, locale, policy,
                                      lambda path: missing.append(path) if path not in missing else None))
        elif kind == "if":
            branch = block.get("then", []) if condition_matches(block.get("condition"), data, policy) else block.get("else", [])
            output.extend(render_blocks(branch, data, locale, policy, missing))
        elif kind == "loop":
            items_path = block.get("items")
            if not isinstance(items_path, str):
                raise ValueError("loop.items is required")
            items = _value(data, items_path, policy)
            if not isinstance(items, list):
                raise ValueError(f"Loop source is not an array: {items_path}")
            if not items and block.get("empty") is not None:
                output.extend(render_blocks([{"type": "text", "text": block["empty"]}], data, locale, policy, missing))
            for item in items:
                local = dict(data) if isinstance(data, dict) else {"value": data}
                local[str(block.get("as", "item"))] = item
                output.extend(render_blocks(block.get("blocks", []), local, locale, policy, missing))
        elif kind != "spacer":
            raise ValueError(f"Unsupported block type: {kind}")
    return output
