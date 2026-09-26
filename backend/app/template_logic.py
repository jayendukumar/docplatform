"""Bounded, data-only template evaluation for the MVP render contract."""
from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Any


class TemplateDataError(ValueError):
    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Missing template field: {path}")


class TemplateEvaluationLimitError(ValueError):
    """Raised when a declarative template exceeds the evaluation budget."""


MAX_RENDER_DEPTH = 20
MAX_RENDER_BLOCKS = 2_000
MAX_LOOP_ITEMS = 1_000


_PATH = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*|\[\d+\])*$")
_TOKEN = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")
_TRANSLATION_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")


def _sample_scalar(schema: dict[str, Any], path: str, locale: str) -> Any:
    kind = schema.get("type")
    if kind == "boolean":
        return True
    if kind in {"number", "integer"}:
        return 1234.5 if kind == "number" else 1234
    if kind == "array":
        return [_sample_value(schema.get("items", {}), f"{path}[0]", locale)]
    if kind == "object":
        return _sample_value(schema, path, locale)
    lowered = path.casefold()
    if "date" in lowered or lowered in {"issued", "due", "valid_from", "valid_until"} or lowered.endswith("_at") or lowered.endswith("_on"):
        return "2026-01-15"
    if "email" in lowered:
        return "alex@example.test"
    if "url" in lowered or "website" in lowered:
        return "https://example.test"
    if "name" in lowered:
        return "Alex"
    if "amount" in lowered or "total" in lowered or "price" in lowered:
        return 1234.5
    samples = {"de": "Beispieltext", "fr": "Texte exemple", "ar": "نص تجريبي", "hi": "उदाहरण", "th": "ตัวอย่าง", "zh": "示例文本", "ja": "サンプル"}
    return samples.get(locale.casefold().split("-", 1)[0], "Example text")


def _sample_value(schema: Any, path: str, locale: str) -> Any:
    if not isinstance(schema, dict):
        return _sample_scalar({}, path, locale)
    if schema.get("type") == "object" or "properties" in schema:
        return {str(key): _sample_value(value, f"{path}.{key}".strip("."), locale)
                for key, value in schema.get("properties", {}).items() if isinstance(key, str)}
    return _sample_scalar(schema, path, locale)


def generate_sample_data(definition: dict[str, Any], locale: str | None = None) -> dict[str, Any]:
    """Generate deterministic preview data from the bounded template contract."""
    selected_locale = locale or str(definition.get("locale", "en"))
    schema = definition.get("data_schema")
    if isinstance(schema, dict):
        value = _sample_value(schema, "", selected_locale)
        return value if isinstance(value, dict) else {"value": value}

    result: dict[str, Any] = {}

    def put(path: str, value: Any) -> None:
        if not _PATH.fullmatch(path):
            return
        parts = path.split(".")
        cursor = result
        for part in parts[:-1]:
            existing = cursor.get(part)
            if not isinstance(existing, dict):
                existing = {}
                cursor[part] = existing
            cursor = existing
        cursor.setdefault(parts[-1], value)

    def walk(blocks: Any, scope: str = "") -> None:
        for block in blocks if isinstance(blocks, list) else []:
            if not isinstance(block, dict):
                continue
            for raw in _TOKEN.findall(str(block.get("text", "")) + " " + str(block.get("value", ""))):
                token = raw.strip()
                match = re.fullmatch(r"(?:number|currency|date|percent|text)\(\s*([^()]+?)\s*\)", token)
                path = match.group(1).strip() if match else token
                if scope and path.startswith(f"{scope}."):
                    path = path[len(scope) + 1:]
                if _PATH.fullmatch(path) and not path.startswith(("item.", "row.")):
                    put(path, _sample_scalar({}, path, selected_locale))
            kind = block.get("type")
            if kind in {"table", "loop"} and isinstance(block.get("items"), str):
                items = str(block["items"])
                item_scope = str(block.get("as", "item"))
                columns = block.get("columns", [])
                row: dict[str, Any] = {}
                for column in columns if isinstance(columns, list) else []:
                    if isinstance(column, dict) and isinstance(column.get("path"), str):
                        path = column["path"]
                        row[path] = _sample_scalar({}, path, selected_locale)
                nested = block.get("blocks", [])
                for raw in _TOKEN.findall(json_text(nested)):
                    token = raw.strip()
                    path = token.split("(")[-1].rstrip(") ").strip()
                    if path.startswith(f"{item_scope}."):
                        path = path[len(item_scope) + 1:]
                    if _PATH.fullmatch(path):
                        row.setdefault(path, _sample_scalar({}, path, selected_locale))
                put(items, [row or {"description": "Example item"}])
                walk(nested, item_scope)
            if kind == "if" and isinstance(block.get("condition"), dict):
                condition = block["condition"]
                if isinstance(condition.get("path"), str):
                    put(condition["path"], condition.get("equals", True))
                walk(block.get("then", []), scope)
            walk(block.get("then", []), scope)
            walk(block.get("else", []), scope)

    def json_text(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else str(value)

    walk(definition.get("blocks", []))
    return result


def resolve_path(data: Any, path: str) -> tuple[Any, bool]:
    if not _PATH.fullmatch(path):
        raise ValueError(f"Unsupported template expression: {path}")
    if any(segment.startswith("__") for segment in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", path)):
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


_LOCALE_PROFILES: dict[str, tuple[str, str, bool, str, bool]] = {
    "en": (".", ",", False, "$", True),
    "en-gb": (".", ",", False, "£", True),
    "de": (",", ".", False, "€", False),
    "fr": (",", "\u202f", False, "€", False),
    "hi": (".", ",", True, "₹", True),
    "ar": ("٫", "٬", False, "د.إ", False),
    "th": (".", ",", False, "฿", True),
    "zh": (".", ",", False, "¥", True),
    "ja": (".", ",", False, "¥", True),
    "ko": (".", ",", False, "₩", True),
}

# The original profile table is retained for history; these explicit Unicode
# values are the active locale symbols rather than mojibake spellings.
_LOCALE_PROFILES.update({
    "en-gb": (".", ",", False, "£", True),
    "de": (",", ".", False, "€", False),
    "fr": (",", "\u202f", False, "€", False),
    "hi": (".", ",", True, "₹", True),
    "ar": ("٫", "٬", False, "د.إ", False),
    "th": (".", ",", False, "฿", True),
    "zh": (".", ",", False, "¥", True),
    "ja": (".", ",", False, "¥", True),
    "ko": (".", ",", False, "₩", True),
})


def _locale_profile(locale: str) -> tuple[str, str, bool, str, bool]:
    """Return separators/grouping/currency for the bounded offline locale set."""
    normalized = locale.replace("_", "-").casefold()
    language = normalized.split("-", 1)[0]
    return _LOCALE_PROFILES.get(normalized, _LOCALE_PROFILES.get(language, _LOCALE_PROFILES["en"]))


def _group_digits(integer: str, separator: str, indian: bool) -> str:
    sign = ""
    if integer.startswith(("-", "+")):
        sign, integer = integer[0], integer[1:]
    if len(integer) <= 3:
        return sign + integer
    if indian:
        tail, head = integer[-3:], integer[:-3]
        groups = []
        while head:
            groups.insert(0, head[-2:])
            head = head[:-2]
        return sign + separator.join(groups + [tail])
    groups = []
    while integer:
        groups.insert(0, integer[-3:])
        integer = integer[:-3]
    return sign + separator.join(groups)


def _localize_digits(value: str, locale: str) -> str:
    """Apply the bounded default Arabic-Indic digit system for Arabic locales."""
    language = locale.replace("_", "-").casefold().split("-", 1)[0]
    if language != "ar":
        return value
    return value.translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))


def format_value(value: Any, locale: str, function: str | None = None) -> str:
    if value is None:
        return ""
    if function == "text":
        return str(value)
    if function in {"number", "currency", "percent"} or isinstance(value, (int, float, Decimal)):
        decimal_separator, grouping_separator, indian_grouping, currency, currency_prefix = _locale_profile(locale)
        numeric = Decimal(str(value))
        if function == "percent":
            numeric *= 100
        raw = f"{numeric:.2f}" if function == "currency" else f"{numeric:f}"
        if function == "percent":
            raw = raw.rstrip("0").rstrip(".")
        integer, _, fraction = raw.partition(".")
        formatted = _group_digits(integer, grouping_separator, indian_grouping)
        if fraction:
            formatted += decimal_separator + fraction
        formatted = _localize_digits(formatted, locale)
        if function == "currency":
            return f"{currency}{formatted}" if currency_prefix else f"{formatted} {currency}"
        return formatted + ("٪" if function == "percent" and locale.casefold().startswith("ar")
                            else "%" if function == "percent" else "")
        if function == "percent":
            value = Decimal(str(value)) * 100
        raw = f"{value:,.2f}" if function == "currency" else f"{value:,}"
        if locale.startswith(("de", "fr")):
            raw = raw.replace(",", "\u202f").replace(".", ",")
        return f"{raw} {('€' if locale.startswith('de') else '$')}" if function == "currency" else (raw + "%" if function == "percent" else raw)
    if function == "date":
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return value
        if isinstance(value, (date, datetime)):
            normalized = locale.replace("_", "-").casefold()
            if normalized.startswith(("en-gb", "de", "fr")):
                return value.strftime("%d/%m/%Y")
            if normalized.startswith(("ja", "zh")):
                return value.strftime("%Y/%m/%d")
            return value.strftime("%Y-%m-%d")
    return str(value)


def translated_text(block: dict[str, Any], translations: Any, locale: str,
                   missing_translations: list[str] | None = None) -> str:
    """Resolve a bounded template translation key, retaining block text as fallback."""
    fallback = str(block.get("text", ""))
    key = block.get("translation_key")
    if key is None:
        return fallback
    if not isinstance(key, str) or not _TRANSLATION_KEY.fullmatch(key):
        raise ValueError("translation_key must be a bounded identifier")
    if not isinstance(translations, dict):
        translations = {}
    candidates = [locale]
    base = locale.split("-", 1)[0]
    if base not in candidates:
        candidates.append(base)
    if "default" not in candidates:
        candidates.append("default")
    for language in candidates:
        values = translations.get(language)
        if isinstance(values, dict) and isinstance(values.get(key), str):
            return values[key]
    if missing_translations is not None and f"{locale}:{key}" not in missing_translations:
        missing_translations.append(f"{locale}:{key}")
    return fallback


def interpolate(text: str, data: Any, locale: str, policy: str,
                on_missing: Callable[[str], None] | None = None) -> str:
    def replace(match: re.Match[str]) -> str:
        token = match.group(1).strip()
        function = None
        path = token
        function_match = re.fullmatch(r"(number|currency|date|percent|text)\(\s*([^()]+?)\s*\)", token)
        if function_match:
            function, path = function_match.groups()
        value, found = resolve_path(data, path)
        if not found or value is None:
            if on_missing:
                on_missing(path)
            value = _missing(path, policy)
        return format_value(value, locale, function)

    return _TOKEN.sub(replace, text)


def condition_matches(condition: Any, data: Any, policy: str) -> bool:
    if not isinstance(condition, dict):
        raise ValueError("condition must be an object")  # noqa: TRY004
    if "and" in condition:
        return all(condition_matches(item, data, policy) for item in condition["and"])
    if "or" in condition:
        return any(condition_matches(item, data, policy) for item in condition["or"])
    if "not" in condition:
        return not condition_matches(condition["not"], data, policy)
    path = condition.get("path")
    if not isinstance(path, str):
        raise ValueError("condition.path is required")  # noqa: TRY004
    actual = _value(data, path, policy)
    if "equals" in condition:
        return actual == condition["equals"]
    if "not_equals" in condition:
        return actual != condition["not_equals"]
    if "in" in condition:
        return actual in condition["in"]
    if "truthy" in condition:
        return bool(actual) is bool(condition["truthy"])
    comparisons = {
        "greater_than": lambda expected: actual > expected,
        "greater_or_equal": lambda expected: actual >= expected,
        "less_than": lambda expected: actual < expected,
        "less_or_equal": lambda expected: actual <= expected,
    }
    for operator, compare in comparisons.items():
        if operator in condition:
            try:
                return bool(compare(condition[operator]))
            except TypeError:
                return False
    raise ValueError("condition needs equals, not_equals, in, truthy, or a comparison")


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
                  missing: list[str], *, depth: int = 0, budget: list[int] | None = None,
                  translations: Any = None, missing_translations: list[str] | None = None) -> list[str]:
    if depth > MAX_RENDER_DEPTH:
        raise TemplateEvaluationLimitError(f"Template nesting exceeds {MAX_RENDER_DEPTH} levels")
    budget = budget if budget is not None else [0]
    output: list[str] = []
    for block in blocks:
        budget[0] += 1
        if budget[0] > MAX_RENDER_BLOCKS:
            raise TemplateEvaluationLimitError(f"Template expands beyond {MAX_RENDER_BLOCKS} blocks")
        kind = block.get("type", "text")
        if kind == "text":
            output.append(interpolate(translated_text(block, translations, locale, missing_translations), data, locale, policy,
                                      lambda path: missing.append(path) if path not in missing else None))
        elif kind == "if":
            branch = block.get("then", []) if condition_matches(block.get("condition"), data, policy) else block.get("else", [])
            output.extend(render_blocks(branch, data, locale, policy, missing, depth=depth + 1, budget=budget,
                                        translations=translations, missing_translations=missing_translations))
        elif kind == "loop":
            items_path = block.get("items")
            if not isinstance(items_path, str):
                raise ValueError("loop.items is required")
            items = _value(data, items_path, policy)
            if not isinstance(items, list):
                raise ValueError(f"Loop source is not an array: {items_path}")
            if len(items) > MAX_LOOP_ITEMS:
                raise TemplateEvaluationLimitError(f"Loop exceeds {MAX_LOOP_ITEMS} items: {items_path}")
            if not items and block.get("empty") is not None:
                output.extend(render_blocks([{"type": "text", "text": block["empty"]}], data, locale, policy, missing,
                                            depth=depth + 1, budget=budget, translations=translations,
                                            missing_translations=missing_translations))
            for item in items:
                local = dict(data) if isinstance(data, dict) else {"value": data}
                local[str(block.get("as", "item"))] = item
                output.extend(render_blocks(block.get("blocks", []), local, locale, policy, missing,
                                            depth=depth + 1, budget=budget, translations=translations,
                                            missing_translations=missing_translations))
        elif kind != "spacer":
            raise ValueError(f"Unsupported block type: {kind}")
    return output
