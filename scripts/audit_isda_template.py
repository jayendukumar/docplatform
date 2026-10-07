"""Audit the bounded ISDA semantic authoring contract offline."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.isda_template import editable_isda_blocks, isda_data_schema, isda_sample_data  # noqa: E402
from app.rendering import render_definition  # noqa: E402


def _schema_node(properties: dict, path: str) -> dict | None:
    node: dict = {"properties": properties}
    for part in path.split("."):
        node = node.get("properties", {}).get(part, {})
        if not isinstance(node, dict):
            return None
    return node


def _sample_node(sample: dict, path: str):
    value = sample
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def audit() -> dict:
    blocks = editable_isda_blocks()
    schema = isda_data_schema()
    failures: list[str] = []
    semantic_ids = [block.get("semantic_id") for block in blocks]
    anchors = [block.get("anchor_id") for block in blocks]
    if len(blocks) != 381:
        failures.append(f"expected 381 objects, found {len(blocks)}")
    if len(semantic_ids) != len(set(semantic_ids)):
        failures.append("semantic IDs are not unique")
    if any(not isinstance(semantic_id, str) or not semantic_id.strip() for semantic_id in semantic_ids):
        failures.append("every semantic object must have a non-empty semantic ID")
    if any(not isinstance(anchor, str) or not anchor.strip() for anchor in anchors):
        failures.append("every semantic object must have a non-empty page anchor")
    if len(anchors) != len(set(anchors)):
        failures.append("page anchors are not unique")
    if any(not isinstance(block.get("page_number"), int) or not 1 <= block.get("page_number") <= 36 for block in blocks):
        failures.append("semantic object has invalid page ownership")
    if any(block.get("position_unit") != "mm" for block in blocks):
        failures.append("semantic object does not use millimetre position units")
    if {block.get("page_number") for block in blocks} != set(range(1, 37)):
        failures.append("page ownership does not cover pages 1-36")
    if any(block.get("semantic_kind") not in {"clause", "field", "schedule", "signature"} for block in blocks):
        failures.append("unsupported semantic kind present")
    expected_kind_counts = {"clause": 220, "field": 143, "schedule": 10, "signature": 8}
    actual_kind_counts = Counter(block.get("semantic_kind") for block in blocks)
    for kind, expected_count in expected_kind_counts.items():
        if actual_kind_counts[kind] != expected_count:
            failures.append(f"expected {expected_count} {kind} objects, found {actual_kind_counts[kind]}")
    for block in blocks:
        kind = block.get("semantic_kind")
        field_path = block.get("field_path")
        if kind == "field" and (not field_path or not block.get("field_role")):
            failures.append(f"field object lacks binding metadata: {block.get('semantic_id')}")
        if field_path and kind not in {"field", "signature"}:
            failures.append(f"non-field semantic object has a scalar binding: {block.get('semantic_id')}")
        if block.get("type") == "table" and kind != "schedule":
            failures.append(f"table is not a Schedule object: {block.get('semantic_id')}")

    required_semantic_ids = {
        25: {"definitions-indemnifiable-tax", "definitions-law", "definitions-local-business-day", "definitions-loss", "definitions-market-quotation"},
        26: {"definitions-non-defaulting-party", "definitions-notice", "definitions-office", "definitions-potential-event-of-default", "definitions-proceedings"},
        27: {"definitions-specified-entity", "definitions-specified-indebtedness", "definitions-tax", "definitions-termination-event", "definitions-transaction-term", "definitions-unpaid-amounts"},
        29: {"schedule-intro", "schedule-agreement-date", "schedule-party-x", "schedule-party-y", "schedule-part-1"},
        30: {"schedule-cross-default", "specified-transaction", "specified-transaction-detail", "specified-indebtedness-detail", "additional-termination-event-detail", "cross-default-party-x", "cross-default-party-y", "automatic-early-termination-party-x", "automatic-early-termination-party-y", "termination-currency", "termination-currency-detail"},
        31: {"schedule-tax", "payer-tax-party-x", "payer-tax-party-y", "payee-tax-party-x", "payee-tax-party-y", "specified-treaty-party-x", "specified-treaty-party-y", "specified-jurisdiction-party-x", "specified-jurisdiction-party-y", "payer-representation-detail-party-x", "payer-representation-detail-party-y", "payee-representation-detail-party-x", "payee-representation-detail-party-y"},
        32: {"schedule-agreements", "schedule-tax-documents", "document-delivery-party-x", "document-delivery-party-y"},
        33: {"schedule-documents-heading", "schedule-documents", "notice-address-party-x", "notice-address-party-y", "notice-email-party-x", "notice-email-party-y"},
        34: {"schedule-process-agent", "process-agent-party-x", "process-agent-party-y", "office-party-x", "office-party-y", "multibranch-offices-party-x", "multibranch-offices-party-y", "calculation-agent", "credit-support-provider-party-x", "credit-support-provider-party-y", "governing-law"},
        35: {"schedule-payment-netting", "payment-netting-election", "netting-transactions", "netting-start-date", "affiliate", "absence-litigation-specified-entity-party-x", "absence-litigation-specified-entity-party-y", "additional-representation", "recording-conversations"},
        36: {"schedule-other-provisions", "execution-clause", "signature-attestation", "signature-party-x-by", "signature-party-y-by", "signature-party-x-date", "signature-party-y-date"},
    }
    ids_by_page = {}
    page_kind_counts: dict[int, Counter[str]] = defaultdict(Counter)
    for block in blocks:
        ids_by_page.setdefault(block.get("page_number"), set()).add(block.get("semantic_id"))
        page_kind_counts[block.get("page_number")][block.get("semantic_kind")] += 1
    for page_number, required_ids in required_semantic_ids.items():
        for semantic_id in required_ids - ids_by_page.get(page_number, set()):
            failures.append(f"missing source-observed semantic object: page {page_number}::{semantic_id}")
    for page_number in range(28, 37):
        if page_kind_counts[page_number]["field"] == 0:
            failures.append(f"execution/Schedule page has no field objects: page {page_number}")
    for page_number in (29, 31, 32, 33, 34, 35, 36):
        if page_kind_counts[page_number]["schedule"] == 0:
            failures.append(f"Schedule page has no Schedule objects: page {page_number}")
    for page_number in (28, 36):
        if page_kind_counts[page_number]["signature"] == 0:
            failures.append(f"execution page has no signature objects: page {page_number}")
    for page_number in (32, 33):
        if not any(block.get("type") == "table" and block.get("page_number") == page_number for block in blocks):
            failures.append(f"repeatable Schedule table missing: page {page_number}")

    properties = schema.get("properties", {})
    sample = isda_sample_data()
    bound_field_count = 0
    table_reports = []
    for block in blocks:
        path = block.get("field_path")
        if path:
            bound_field_count += 1
            if not _schema_node(properties, path):
                failures.append(f"missing schema binding: {path}")
            if _sample_node(sample, path) in (None, ""):
                failures.append(f"empty local sample value: {path}")
        if block.get("type") != "table":
            continue
        item_schema = properties.get(block.get("items"), {}).get("items", {})
        item_properties = item_schema.get("properties", {})
        sample_rows = sample.get(block.get("items"), [])
        if not isinstance(sample_rows, list) or not sample_rows:
            failures.append(f"table has no local sample rows: {block.get('semantic_id')}")
        for column in block.get("columns", []):
            if column.get("path") not in item_properties:
                failures.append(f"missing table column schema: {block.get('semantic_id')}::{column.get('path')}")
            if any(not isinstance(row, dict) or row.get(column.get("path")) in (None, "") for row in sample_rows):
                failures.append(f"table column has empty local sample value: {block.get('semantic_id')}::{column.get('path')}")
        table_reports.append({
            "semantic_id": block.get("semantic_id"),
            "page_number": block.get("page_number"),
            "items": block.get("items"),
            "sample_row_count": len(sample_rows) if isinstance(sample_rows, list) else 0,
            "columns": [column.get("path") for column in block.get("columns", [])],
        })

    absolute = [block for block in blocks if block.get("position_mode") == "absolute"]
    for block in absolute:
        if block.get("position_unit") != "mm" or not (0 <= block.get("position_x", -1) <= 215.9) or not (0 <= block.get("position_y", -1) <= 279.4):
            failures.append(f"absolute object outside Letter bounds: {block.get('semantic_id')}")
        if block.get("position_provenance") != "provisional-source-region":
            failures.append(f"missing coordinate provenance: {block.get('semantic_id')}")

    rendered = render_definition({"blocks": blocks, "data_schema": schema}, sample)
    artifact = rendered.get("artifact", "")
    if rendered.get("missing_fields"):
        failures.append(f"sample data leaves missing fields: {rendered['missing_fields']}")
    if artifact.count('class="page-surface') != 36:
        failures.append("rendered artifact does not contain 36 owned page surfaces")

    return {
        "status": "pass" if not failures else "fail",
        "object_count": len(blocks),
        "anchor_count": len(anchors),
        "page_count": len({block.get("page_number") for block in blocks}),
        "table_count": len(table_reports),
        "absolute_object_count": len(absolute),
        "bound_field_count": bound_field_count,
        "semantic_kind_counts": {
            kind: sum(1 for block in blocks if block.get("semantic_kind") == kind)
            for kind in ("clause", "field", "schedule", "signature")
        },
        "page_semantic_kind_counts": {
            str(page_number): dict(page_kind_counts[page_number])
            for page_number in sorted(page_kind_counts)
        },
        "rendered_page_surface_count": artifact.count('class="page-surface'),
        "missing_fields": rendered.get("missing_fields", []),
        "tables": table_reports,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit()
    encoded = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.resolve().parent.mkdir(parents=True, exist_ok=True)
        args.output.resolve().write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
