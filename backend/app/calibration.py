"""Validated, offline confidence-calibration profiles for extraction results."""
from __future__ import annotations

from copy import deepcopy
from itertools import pairwise
from typing import Any


class CalibrationProfileError(ValueError):
    """Raised when a calibration profile is malformed or unsafe to apply."""


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalibrationProfileError(f"{label} must be a number")
    result = float(value)
    if not 0 <= result <= 1:
        raise CalibrationProfileError(f"{label} must be between 0 and 1")
    return result


def validate_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Validate and return a profile suitable for application to a result.

    Profiles are intentionally data-only. They cannot contain expressions,
    imports, or arbitrary result paths. Each mapping is monotone and consists
    of bounded raw-confidence/calibrated-confidence points.
    """
    if not isinstance(profile, dict) or profile.get("contract") != "confidence-calibration-v1":
        raise CalibrationProfileError("profile contract must be confidence-calibration-v1")
    if profile.get("method") != "isotonic":
        raise CalibrationProfileError("profile method must be isotonic")
    schemas = profile.get("schemas")
    if not isinstance(schemas, dict):
        raise CalibrationProfileError("profile schemas must be an object")
    for schema_id, schema_profile in schemas.items():
        if not isinstance(schema_id, str) or not isinstance(schema_profile, dict):
            raise CalibrationProfileError("profile schema entries must be objects")
        for section_name in ("fields", "tables"):
            section = schema_profile.get(section_name, {})
            if not isinstance(section, dict):
                raise CalibrationProfileError(f"{section_name} calibration must be an object")
            for name, mapping in _walk_mappings(section, section_name):
                _validate_mapping(mapping, f"{schema_id}.{name}")
    return profile


def _walk_mappings(section: dict[str, Any], prefix: str):
    for name, mapping in section.items():
        if prefix == "tables":
            if not isinstance(mapping, dict):
                raise CalibrationProfileError(f"{prefix}.{name} must be an object")
            columns = mapping.get("columns", {})
            if not isinstance(columns, dict):
                raise CalibrationProfileError(f"{prefix}.{name}.columns must be an object")
            for column, column_mapping in columns.items():
                yield f"{name}.columns.{column}", column_mapping
        else:
            yield name, mapping


def _validate_mapping(mapping: Any, label: str) -> None:
    if not isinstance(mapping, dict) or not isinstance(mapping.get("points"), list):
        raise CalibrationProfileError(f"{label} must contain points")
    points = mapping["points"]
    if not points:
        raise CalibrationProfileError(f"{label}.points must not be empty")
    previous_raw = -1.0
    previous_calibrated = -1.0
    for index, point in enumerate(points):
        if not isinstance(point, dict):
            raise CalibrationProfileError(f"{label}.points[{index}] must be an object")
        raw = _number(point.get("raw"), f"{label}.points[{index}].raw")
        calibrated = _number(point.get("calibrated"), f"{label}.points[{index}].calibrated")
        if raw < previous_raw or calibrated < previous_calibrated:
            raise CalibrationProfileError(f"{label} points must be monotone")
        previous_raw, previous_calibrated = raw, calibrated


def calibrate_score(score: float, mapping: dict[str, Any]) -> float:
    """Linearly interpolate a validated monotone mapping and clamp its range."""
    raw = _number(score, "confidence")
    points = mapping["points"]
    if raw <= points[0]["raw"]:
        return float(points[0]["calibrated"])
    for left, right in pairwise(points):
        if raw <= right["raw"]:
            span = float(right["raw"]) - float(left["raw"])
            if span == 0:
                return float(right["calibrated"])
            fraction = (raw - float(left["raw"])) / span
            return float(left["calibrated"]) + fraction * (
                float(right["calibrated"]) - float(left["calibrated"]))
    return float(points[-1]["calibrated"])


def apply_profile(result: dict[str, Any], profile: dict[str, Any], schema_id: str | None = None) -> dict[str, Any]:
    """Return a calibrated result copy, preserving raw confidence values."""
    validate_profile(profile)
    calibrated = deepcopy(result)
    selected = profile.get("schemas", {}).get(schema_id or result.get("schema_id"), {})
    field_mappings = selected.get("fields", {})
    applied_count = 0
    for name, field in calibrated.get("fields", {}).items():
        mapping = field_mappings.get(name)
        if isinstance(mapping, dict) and isinstance(field, dict) and field.get("confidence") is not None:
            field["raw_confidence"] = field["confidence"]
            field["confidence"] = calibrate_score(float(field["confidence"]), mapping)
            applied_count += 1
    table_mappings = selected.get("tables", {})
    for table_name, table in calibrated.get("tables", {}).items():
        table_mapping = table_mappings.get(table_name, {})
        column_mappings = table_mapping.get("columns", {}) if isinstance(table_mapping, dict) else {}
        for row in table.get("rows", []):
            for column, field in row.get("fields", {}).items():
                mapping = column_mappings.get(column)
                if isinstance(mapping, dict) and isinstance(field, dict) and field.get("confidence") is not None:
                    field["raw_confidence"] = field["confidence"]
                    field["confidence"] = calibrate_score(float(field["confidence"]), mapping)
                    applied_count += 1
    calibrated["confidence_calibration"] = {
        "contract": profile["contract"], "method": profile["method"],
        "profile_id": profile.get("profile_id"), "applied": applied_count > 0,
        "mapped_fields": applied_count,
    }
    return calibrated
