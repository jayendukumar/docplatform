"""Deterministic local extraction over a versioned PageModel."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
from typing import Any


class ExtractionSchemaError(ValueError):
    pass


# Small, explicit aliases for the bundled schemas. These are contract fixtures,
# not a claim of broad translation coverage or native-sample accuracy.
LABEL_DICTIONARIES: dict[str, dict[str, list[str]]] = {
    "ar": {"invoice_number": ["\u0631\u0642\u0645 \u0627\u0644\u0641\u0627\u062a\u0648\u0631\u0629"], "invoice_date": ["\u062a\u0627\u0631\u064a\u062e \u0627\u0644\u0641\u0627\u062a\u0648\u0631\u0629", "\u0627\u0644\u062a\u0627\u0631\u064a\u062e"], "total": ["\u0627\u0644\u0625\u062c\u0645\u0627\u0644\u064a", "\u0627\u0644\u0645\u0628\u0644\u063a \u0627\u0644\u0645\u0633\u062a\u062d\u0642"], "merchant": ["\u0627\u0644\u062a\u0627\u062c\u0631", "\u0627\u0644\u0645\u062a\u062c\u0631"]},
    "hi": {"invoice_number": ["\u091a\u093e\u0932\u093e\u0928 \u0938\u0902\u0916\u094d\u092f\u093e", "\u092c\u093f\u0932 \u0938\u0902\u0916\u094d\u092f\u093e"], "invoice_date": ["\u091a\u093e\u0932\u093e\u0928 \u0926\u093f\u0928\u093e\u0902\u0915", "\u0926\u093f\u0928\u093e\u0902\u0915"], "total": ["\u0915\u0941\u0932", "\u0926\u0947\u092f \u0930\u093e\u0936\u093f"], "merchant": ["\u0935\u094d\u092f\u093e\u092a\u093e\u0930\u0940", "\u0926\u0941\u0915\u093e\u0928"]},
    "th": {"invoice_number": ["\u0e40\u0e25\u0e02\u0e17\u0e35\u0e48\u0e43\u0e1a\u0e40\u0e2a\u0e23\u0e47\u0e08\u0e2f"], "invoice_date": ["\u0e27\u0e31\u0e19\u0e17\u0e35\u0e48\u0e43\u0e1a\u0e40\u0e2a\u0e23\u0e47\u0e08\u0e2f", "\u0e27\u0e31\u0e19\u0e17\u0e35\u0e48"], "total": ["\u0e23\u0e27\u0e21\u0e17\u0e31\u0e49\u0e07\u0e2b\u0e21\u0e14", "\u0e22\u0e2d\u0e14\u0e17\u0e35\u0e48\u0e15\u0e49\u0e2d\u0e07\u0e0a\u0e33\u0e23\u0e30"], "merchant": ["\u0e23\u0e49\u0e32\u0e19\u0e04\u0e49\u0e32", "\u0e1c\u0e39\u0e49\u0e04\u0e49\u0e32"]},
    "zh": {"invoice_number": ["\u53d1\u7968\u53f7"], "invoice_date": ["\u53d1\u7968\u65e5\u671f", "\u65e5\u671f"], "total": ["\u5408\u8ba1", "\u5e94\u4ed8\u91d1\u989d"], "merchant": ["\u5546\u6237", "\u5e97\u94fa"]},
}

# A second East-Asian label set keeps the bounded dictionary useful beyond the
# four minimum locales while remaining explicit and reviewable offline.
LABEL_DICTIONARIES["ja"] = {
    "invoice_number": ["\u8acb\u6c42\u66f8\u756a\u53f7", "\u4f1d\u7968\u756a\u53f7"],
    "invoice_date": ["\u8acb\u6c42\u66f8\u65e5\u4ed8", "\u8acb\u6c42\u65e5", "\u65e5\u4ed8"],
    "total": ["\u5408\u8a08", "\u8acb\u6c42\u91d1\u984d", "\u652f\u6255\u91d1\u984d"],
    "merchant": ["\u53d6\u5f15\u5148", "\u5e97\u8217", "\u8ca9\u58f2\u8005"],
}


def label_aliases(definition: dict[str, Any], locale: str = "en") -> list[str]:
    labels = [str(label) for label in definition.get("labels", []) if str(label).strip()]
    language = locale.replace("_", "-").casefold().split("-")[0]
    labels.extend(LABEL_DICTIONARIES.get(language, {}).get(str(definition.get("name", "")), []))
    return list(dict.fromkeys(labels))


def _field(name: str, kind: str, labels: list[str], required: bool = False, **rules: Any) -> dict[str, Any]:
    return {"name": name, "type": kind, "labels": labels, "required": required, **rules}


BUNDLED_SCHEMAS: dict[str, dict[str, Any]] = {
    "invoice": {"schema_version": 1, "id": "invoice", "name": "Invoice", "fields": [
        _field("invoice_number", "string", ["invoice number", "invoice #"], True),
        _field("invoice_date", "date", ["invoice date", "date"]),
        _field("total", "currency", ["total", "amount due"], True, minimum=0),
    ], "tables": [{"name": "line_items", "labels": ["line items", "items"], "columns": [
        _field("description", "string", ["description", "item", "product"]),
        _field("quantity", "number", ["quantity", "qty"]),
        _field("unit_price", "currency", ["unit price", "price"]),
        _field("amount", "currency", ["amount", "line total"]),
    ]}], "totals": [{"field": "total", "table": "line_items", "column": "amount", "tolerance": "0.01"}]},
    "receipt": {"schema_version": 1, "id": "receipt", "name": "Receipt", "fields": [
        _field("merchant", "string", ["merchant", "store"]),
        _field("receipt_date", "date", ["date"]),
        _field("total", "currency", ["total", "amount"], True, minimum=0),
    ]},
    "purchase-order": {"schema_version": 1, "id": "purchase-order", "name": "Purchase order", "fields": [
        _field("purchase_order_number", "string", ["purchase order", "po number", "po #"], True),
        _field("order_date", "date", ["order date", "date"]),
        _field("total", "currency", ["total", "order total"], True, minimum=0),
    ], "tables": [{"name": "line_items", "labels": ["line items", "items"], "columns": [
        _field("description", "string", ["description", "item", "product"]),
        _field("quantity", "number", ["quantity", "qty"]),
        _field("unit_price", "currency", ["unit price", "price"]),
        _field("amount", "currency", ["amount", "line total"]),
    ]}]},
}


BUNDLED_SAMPLES: dict[str, dict[str, Any]] = {
    "invoice": {"filename": "sample-invoice.pdf", "locale": "en-US",
                 "page_model": {"schema_version": 1, "document_id": "sample-invoice", "pages": [{
                     "page_number": 1, "elements": [
                         {"id": "invoice-number", "text": "Invoice Number: INV-SAMPLE", "box": [72, 72, 260, 86]},
                         {"id": "invoice-date", "text": "Invoice Date: 2025-01-15", "box": [72, 90, 260, 104]},
                         {"id": "invoice-total", "text": "Total: $6.00", "box": [72, 108, 260, 122]},
                         {"id": "invoice-row-1", "text": "Widget | 2 | $3.00 | $6.00", "box": [72, 126, 360, 140]},
                     ]}]},
                 "expected": {"fields": {"invoice_number": "INV-SAMPLE", "invoice_date": "2025-01-15", "total": "6.00"},
                              "tables": {"line_items": [{"description": "Widget", "quantity": "2", "unit_price": "3.00", "amount": "6.00"}]}}},
    "receipt": {"filename": "sample-receipt.pdf", "locale": "en-US",
                 "page_model": {"schema_version": 1, "document_id": "sample-receipt", "pages": [{
                     "page_number": 1, "elements": [
                         {"id": "receipt-merchant", "text": "Merchant: Sample Market", "box": [72, 72, 260, 86]},
                         {"id": "receipt-date", "text": "Date: 2025-02-03", "box": [72, 90, 260, 104]},
                         {"id": "receipt-total", "text": "Total: $8.25", "box": [72, 108, 260, 122]},
                     ]}]},
                 "expected": {"fields": {"merchant": "Sample Market", "receipt_date": "2025-02-03", "total": "8.25"}, "tables": {}}},
    "purchase-order": {"filename": "sample-purchase-order.pdf", "locale": "en-US",
                        "page_model": {"schema_version": 1, "document_id": "sample-purchase-order", "pages": [{
                            "page_number": 1, "elements": [
                                {"id": "po-number", "text": "PO Number: PO-SAMPLE", "box": [72, 72, 260, 86]},
                                {"id": "po-date", "text": "Order Date: 2025-03-04", "box": [72, 90, 260, 104]},
                                {"id": "po-total", "text": "Order Total: $12.00", "box": [72, 108, 260, 122]},
                                {"id": "po-row-1", "text": "Widget | 1 | $12.00 | $12.00", "box": [72, 126, 360, 140]},
                            ]}]},
                        "expected": {"fields": {"purchase_order_number": "PO-SAMPLE", "order_date": "2025-03-04", "total": "12.00"},
                                     "tables": {"line_items": [{"description": "Widget", "quantity": "1", "unit_price": "12.00", "amount": "12.00"}]}}},
}


def schema_to_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    validate_schema(schema)
    properties: dict[str, Any] = {}
    required: list[str] = []
    type_map = {"string": "string", "number": "number", "currency": "number",
                "date": "string", "boolean": "boolean"}
    for field in schema["fields"]:
        definition: dict[str, Any] = {"type": type_map[field.get("type", "string")],
                                      "title": field["name"].replace("_", " ").title(),
                                      "x-labels": field.get("labels", [])}
        if field.get("type") == "date":
            definition["format"] = "date"
        for rule in ("minimum", "maximum", "pattern"):
            if rule in field:
                definition[rule] = field[rule]
        properties[field["name"]] = definition
        if field.get("required"):
            required.append(field["name"])
    for table in schema.get("tables", []):
        table_properties: dict[str, Any] = {}
        table_required: list[str] = []
        for column in table["columns"]:
            column_definition: dict[str, Any] = {"type": type_map[column.get("type", "string")],
                                                 "x-labels": column.get("labels", [])}
            if column.get("type") == "date":
                column_definition["format"] = "date"
            table_properties[column["name"]] = column_definition
            if column.get("required"):
                table_required.append(column["name"])
        properties[table["name"]] = {"type": "array", "items": {"type": "object",
            "properties": table_properties, "required": table_required, "additionalProperties": False}}
    result: dict[str, Any] = {"$schema": "https://json-schema.org/draft/2020-12/schema",
                              "title": schema.get("name", schema.get("id", "Extraction")),
                              "type": "object", "properties": properties,
                              "required": required, "additionalProperties": False,
                              "x-docplatform-schema-id": schema.get("id"),
                              "x-docplatform-schema-version": schema.get("schema_version", 1)}
    return result


def validate_schema(schema: Any) -> None:
    if not isinstance(schema, dict) or not isinstance(schema.get("fields"), list):
        raise ExtractionSchemaError("schema.fields must be an array")
    names: set[str] = set()
    for field in schema["fields"]:
        if not isinstance(field, dict) or not isinstance(field.get("name"), str):
            raise ExtractionSchemaError("each schema field needs a name")
        if field["name"] in names:
            raise ExtractionSchemaError(f"duplicate schema field: {field['name']}")
        names.add(field["name"])
        if field.get("type", "string") not in {"string", "number", "currency", "date", "boolean"}:
            raise ExtractionSchemaError(f"unsupported field type: {field.get('type')}")
    table_names: set[str] = set()
    for table in schema.get("tables", []):
        if not isinstance(table, dict) or not isinstance(table.get("name"), str):
            raise ExtractionSchemaError("each schema table needs a name")
        if table["name"] in table_names:
            raise ExtractionSchemaError(f"duplicate schema table: {table['name']}")
        table_names.add(table["name"])
        if not isinstance(table.get("columns"), list) or not table["columns"]:
            raise ExtractionSchemaError(f"table {table['name']} columns must be a non-empty array")
        column_names: set[str] = set()
        for column in table["columns"]:
            if not isinstance(column, dict) or not isinstance(column.get("name"), str):
                raise ExtractionSchemaError(f"table {table['name']} columns need names")
            if column["name"] in column_names:
                raise ExtractionSchemaError(f"duplicate column in table {table['name']}: {column['name']}")
            column_names.add(column["name"])
            if column.get("type", "string") not in {"string", "number", "currency", "date", "boolean"}:
                raise ExtractionSchemaError(f"unsupported table column type: {column.get('type')}")
    for total in schema.get("totals", []):
        if not isinstance(total, dict) or not all(isinstance(total.get(key), str)
                                                  for key in ("field", "table", "column")):
            raise ExtractionSchemaError("each total rule needs field, table, and column")


def _text_elements(page_model: dict[str, Any]) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    for page in page_model.get("pages", []):
        for element in page.get("elements", []):
            if isinstance(element, dict) and isinstance(element.get("text"), str):
                item = dict(element)
                item.setdefault("page_number", page.get("page_number"))
                elements.append(item)
    return elements


def _candidate(elements: list[dict[str, Any]], labels: list[str]) -> tuple[str, dict[str, Any]] | None:
    normalized_labels = sorted((label.strip().casefold() for label in labels if label.strip()), key=len, reverse=True)
    for element in elements:
        text = element["text"].strip()
        folded = text.casefold()
        for label in normalized_labels:
            match = re.search(rf"(?:^|\b){re.escape(label)}\s*(?:[:#-]|\s{{1,3}})\s*(.+)$", folded)
            if match:
                start = match.start(1)
                return text[start:].strip(), element
    return None


def _locale_decimal_comma(locale: str) -> bool:
    language = locale.replace("_", "-").casefold().split("-")[0]
    return language in {"de", "fr", "es", "it", "pt", "nl", "da", "el", "tr", "ru", "pl", "cs"}


def _normalize(value: str, kind: str, locale: str = "en") -> Any:
    if kind == "string":
        return value
    if kind in {"number", "currency"}:
        cleaned = re.sub(r"[^0-9,.-]", "", value)
        comma_decimal = _locale_decimal_comma(locale)
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".") if comma_decimal else cleaned.replace(",", "")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".") if comma_decimal else cleaned.replace(",", "")
        elif comma_decimal and "." in cleaned:
            cleaned = cleaned.replace(".", "")
        try:
            number = Decimal(cleaned)
        except InvalidOperation:
            return None
        quantized = number.quantize(Decimal("0.01") if kind == "currency" else Decimal("0.001"))
        return f"{quantized:.2f}" if kind == "currency" else str(quantized.normalize())
    if kind == "boolean":
        if value.casefold() in {"yes", "true", "y", "1"}:
            return True
        if value.casefold() in {"no", "false", "n", "0"}:
            return False
        return None
    if kind == "date":
        date_patterns = ["%Y-%m-%d", "%d.%m.%Y"]
        date_patterns.extend(("%m/%d/%Y", "%d/%m/%Y") if not _locale_decimal_comma(locale)
                             else ("%d/%m/%Y", "%m/%d/%Y"))
        for pattern in date_patterns:
            try:
                return datetime.strptime(value[:10], pattern).date().isoformat()
            except ValueError:
                continue
        return None
    return None


def _luhn_valid(value: str) -> bool:
    digits = [int(character) for character in re.sub(r"\D", "", value)]
    if len(digits) < 2:
        return False
    checksum = 0
    for index, digit in enumerate(reversed(digits)):
        if index % 2:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def _validation_findings(original: str, normalized: Any, definition: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if normalized is None:
        findings.append({"code": "type", "message": "Value could not be normalized to the field type"})
    if isinstance(normalized, str) and definition.get("minimum") is not None:
        try:
            if Decimal(normalized) < Decimal(str(definition["minimum"])):
                findings.append({"code": "minimum", "message": "Value is below the configured minimum"})
        except InvalidOperation:
            pass
    if isinstance(normalized, str) and definition.get("maximum") is not None:
        try:
            if Decimal(normalized) > Decimal(str(definition["maximum"])):
                findings.append({"code": "maximum", "message": "Value is above the configured maximum"})
        except InvalidOperation:
            pass
    if definition.get("pattern") and not re.fullmatch(definition["pattern"], str(normalized or "")):
        findings.append({"code": "pattern", "message": "Value does not match the configured pattern"})
    if definition.get("checksum") == "luhn" and not _luhn_valid(original):
        findings.append({"code": "checksum", "message": "Value failed the Luhn checksum"})
    return findings


def _table_rows(elements: list[dict[str, Any]], table: dict[str, Any], locale: str) -> list[dict[str, Any]]:
    columns = table["columns"]
    labels = [str(column.get("name", "")).replace("_", " ").casefold() for column in columns]
    aliases = [{str(label).strip().casefold() for label in label_aliases({**column, "name": column.get("name", "")}, locale)} | {labels[index]}
               for index, column in enumerate(columns)]
    rows: list[dict[str, Any]] = []
    for element in elements:
        parts = [part.strip() for part in element["text"].split("|")]
        if len(parts) < len(columns):
            continue
        folded = {part.casefold() for part in parts}
        if any(alias in folded for group in aliases for alias in group):
            continue
        values: dict[str, Any] = {}
        for index, column in enumerate(columns):
            original = parts[index]
            normalized = _normalize(original, column.get("type", "string"), locale)
            findings = _validation_findings(original, normalized, column)
            values[column["name"]] = {
                "original_value": original, "normalized_value": normalized,
                "confidence": 0.90 if not findings else 0.35,
                "source": {"page_number": element.get("page_number"), "element_id": element.get("id"),
                           "box": element.get("box")}, "validation": findings,
                "review_status": "needs_review" if findings else "new",
            }
        rows.append({"fields": values, "source": {"page_number": element.get("page_number"),
                                                     "element_id": element.get("id"), "box": element.get("box")}})
    return rows


def extract_local(page_model: dict[str, Any], schema: dict[str, Any], locale: str = "en") -> dict[str, Any]:
    validate_schema(schema)
    elements = _text_elements(page_model)
    fields: dict[str, Any] = {}
    for definition in schema["fields"]:
        name = definition["name"]
        found = _candidate(elements, label_aliases({**definition, "name": name,
                                                    "labels": definition.get("labels", [name.replace("_", " ")])}, locale))
        findings: list[dict[str, str]] = []
        if found is None:
            if definition.get("required"):
                findings.append({"code": "required", "message": "Value was not found"})
            fields[name] = {"original_value": None, "normalized_value": None, "confidence": 0.0,
                            "source": None, "validation": findings, "review_status": "needs_review"}
            continue
        original, source = found
        normalized = _normalize(original, definition.get("type", "string"), locale)
        findings = _validation_findings(original, normalized, definition)
        fields[name] = {"original_value": original, "normalized_value": normalized,
                        "confidence": 0.90 if not findings else 0.35,
                        "source": {"page_number": source.get("page_number"), "element_id": source.get("id"),
                                   "box": source.get("box")},
                        "validation": findings,
                        "review_status": "needs_review" if findings else "new"}
    tables: dict[str, Any] = {}
    for table in schema.get("tables", []):
        rows = _table_rows(elements, table, locale)
        tables[table["name"]] = {"columns": [column["name"] for column in table["columns"]],
                                  "rows": rows, "row_count": len(rows),
                                  "engine": "local-delimited-row-extractor"}
    for total_rule in schema.get("totals", []):
        target = fields.get(total_rule.get("field"))
        table = tables.get(total_rule.get("table"))
        if not target or not table:
            continue
        try:
            expected_total = Decimal(str(target.get("normalized_value")))
            calculated = sum(Decimal(str(row["fields"][total_rule["column"]]["normalized_value"]))
                             for row in table["rows"])
            tolerance = Decimal(str(total_rule.get("tolerance", "0.01")))
            if abs(expected_total - calculated) > tolerance:
                target["validation"].append({"code": "total", "message": "Value does not equal the line-item total"})
        except (KeyError, TypeError, InvalidOperation):
            target["validation"].append({"code": "total", "message": "Line-item total could not be calculated"})
        if target["validation"]:
            target["confidence"] = 0.35
            target["review_status"] = "needs_review"
    table_needs_review = any(field.get("review_status") == "needs_review"
                             for table in tables.values() for row in table["rows"]
                             for field in row["fields"].values())
    return {"schema_version": 1, "schema_id": schema.get("id"), "locale": locale,
            "document_id": page_model.get("document_id"), "fields": fields, "tables": tables,
            "status": "needs_review" if (any(field["review_status"] == "needs_review" for field in fields.values())
                                           or table_needs_review) else "new",
            "engine": {"id": "local-label-extractor", "version": "0.1"}}
