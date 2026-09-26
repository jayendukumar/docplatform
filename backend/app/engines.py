"""Versioned extraction-engine contract and offline plugin discovery."""
from __future__ import annotations

import importlib.util
import math
import re
from dataclasses import dataclass
from importlib.metadata import entry_points
from typing import Any, Protocol

from app.extraction import extract_local


class ExtractionEngineError(ValueError):
    pass


class ExtractionEngine(Protocol):
    id: str
    version: str

    def extract(self, page_model: dict[str, Any], schema: dict[str, Any], locale: str) -> dict[str, Any]: ...


@dataclass(frozen=True)
class EngineDescriptor:
    id: str
    version: str
    available: bool
    capabilities: tuple[str, ...]
    reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        result = {"id": self.id, "version": self.version, "available": self.available,
                  "capabilities": list(self.capabilities)}
        if self.reason:
            result["reason"] = self.reason
        return result


class LocalLabelEngine:
    id = "local-label-extractor"
    version = "0.1"

    def extract(self, page_model: dict[str, Any], schema: dict[str, Any], locale: str) -> dict[str, Any]:
        return extract_local(page_model, schema, locale)


def _optional_descriptor(engine_id: str, package: str, capabilities: tuple[str, ...]) -> EngineDescriptor:
    installed = importlib.util.find_spec(package) is not None
    return EngineDescriptor(engine_id, "external", installed, capabilities,
                            None if installed else f"optional dependency {package!r} is not installed")


def _plugin_descriptor(engine: Any) -> EngineDescriptor | None:
    engine_id = getattr(engine, "id", None)
    version = getattr(engine, "version", None)
    capabilities = getattr(engine, "capabilities", ("page-model",))
    if not isinstance(engine_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", engine_id):
        return None
    if not isinstance(version, str) or not version or len(version) > 64:
        return None
    if not isinstance(capabilities, (tuple, list)) or not capabilities or len(capabilities) > 32:
        return None
    if any(not isinstance(item, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", item) for item in capabilities):
        return None
    normalized_capabilities = tuple(dict.fromkeys(capabilities))
    return EngineDescriptor(engine_id, version, True, normalized_capabilities)


def _plugin_engines() -> list[tuple[EngineDescriptor, ExtractionEngine]]:
    found: list[tuple[EngineDescriptor, ExtractionEngine]] = []
    try:
        candidates = entry_points().select(group="docplatform.extraction_engines")
    except (AttributeError, RuntimeError):
        candidates = []
    for candidate in candidates:
        try:
            factory = candidate.load()
            engine = factory() if callable(factory) else factory
            if not callable(getattr(engine, "extract", None)):
                continue
            descriptor = _plugin_descriptor(engine)
            if descriptor is None:
                continue
            found.append((descriptor, engine))
        except Exception:  # noqa: BLE001,S112 - broken optional plugins must fail closed
            # A broken optional plugin must not prevent the local engine or API from starting.
            continue
    return found


def _validate_result(result: dict[str, Any], engine_id: str) -> None:
    """Enforce the common extraction-engine-v1 result envelope."""
    if result.get("schema_version") != 1:
        raise ExtractionEngineError(f"extraction engine {engine_id!r} returned unsupported schema_version")
    if not isinstance(result.get("fields"), dict) or not isinstance(result.get("tables"), dict):
        raise ExtractionEngineError(f"extraction engine {engine_id!r} returned invalid fields or tables")
    def validate_source(source: Any, context: str) -> None:
        if source is None:
            return
        if not isinstance(source, dict):
            raise ExtractionEngineError(f"extraction engine {engine_id!r} returned invalid provenance for {context}")
        page_number = source.get("page_number")
        box = source.get("box")
        if isinstance(page_number, bool) or not isinstance(page_number, int) or page_number < 1:
            raise ExtractionEngineError(f"extraction engine {engine_id!r} returned invalid source page for {context}")
        if not isinstance(box, list) or len(box) != 4 or any(
                isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item)
                for item in box):
            raise ExtractionEngineError(f"extraction engine {engine_id!r} returned invalid source box for {context}")
        if box[0] < 0 or box[1] < 0 or box[2] <= box[0] or box[3] <= box[1]:
            raise ExtractionEngineError(f"extraction engine {engine_id!r} returned invalid source box for {context}")
        if "element_id" in source and source["element_id"] is not None and not isinstance(source["element_id"], str):
            raise ExtractionEngineError(f"extraction engine {engine_id!r} returned invalid source element for {context}")

    def validate_field(field: dict[str, Any], context: str) -> None:
        value_present = field.get("original_value") is not None or field.get("normalized_value") is not None
        source = field.get("source")
        if value_present and source is None:
            raise ExtractionEngineError(f"extraction engine {engine_id!r} returned missing provenance for {context}")
        validate_source(source, context)

    for field_name, field in result["fields"].items():
        if not isinstance(field_name, str) or not isinstance(field, dict):
            raise ExtractionEngineError(f"extraction engine {engine_id!r} returned an invalid field")
        confidence = field.get("confidence")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise ExtractionEngineError(f"extraction engine {engine_id!r} returned invalid confidence for {field_name!r}")
        validate_field(field, repr(field_name))
        if not isinstance(field.get("validation", []), list):
            raise ExtractionEngineError(f"extraction engine {engine_id!r} returned invalid validation findings")
    for table_name, table in result["tables"].items():
        if not isinstance(table_name, str) or not isinstance(table, dict):
            raise ExtractionEngineError(f"extraction engine {engine_id!r} returned an invalid table")
        if not isinstance(table.get("columns"), list) or not isinstance(table.get("rows"), list):
            raise ExtractionEngineError(f"extraction engine {engine_id!r} returned invalid table rows")
        for row in table["rows"]:
            if not isinstance(row, dict) or not isinstance(row.get("fields"), dict):
                raise ExtractionEngineError(f"extraction engine {engine_id!r} returned an invalid table row")
            for field_name, field in row["fields"].items():
                if not isinstance(field_name, str) or not isinstance(field, dict):
                    raise ExtractionEngineError(f"extraction engine {engine_id!r} returned an invalid table field")
                confidence = field.get("confidence")
                if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
                    raise ExtractionEngineError(f"extraction engine {engine_id!r} returned invalid table confidence")
                validate_field(field, f"{table_name}.{field_name}")


def engine_descriptors() -> list[EngineDescriptor]:
    descriptors = [EngineDescriptor(LocalLabelEngine.id, LocalLabelEngine.version, True,
                                    ("scalar-fields", "repeating-tables", "provenance")),
                    _optional_descriptor("docling", "docling", ("layout", "reading-order", "tables")),
                    _optional_descriptor("paddleocr", "paddleocr", ("ocr", "language-packs"))]
    known = {descriptor.id for descriptor in descriptors}
    for descriptor, _ in _plugin_engines():
        if descriptor.id not in known:
            descriptors.append(descriptor)
            known.add(descriptor.id)
    return descriptors


def extract_with_engine(engine_id: str, page_model: dict[str, Any], schema: dict[str, Any], locale: str) -> dict[str, Any]:
    if engine_id == LocalLabelEngine.id:
        engine: ExtractionEngine = LocalLabelEngine()
    else:
        plugin = next(((descriptor, engine) for descriptor, engine in _plugin_engines()
                       if descriptor.id == engine_id), None)
        if plugin is None:
            descriptor = next((item for item in engine_descriptors() if item.id == engine_id), None)
            reason = descriptor.reason if descriptor else "engine is not registered"
            raise ExtractionEngineError(f"extraction engine {engine_id!r} unavailable: {reason}")
        engine = plugin[1]
    result = engine.extract(page_model, schema, locale)
    if not isinstance(result, dict):
        raise ExtractionEngineError(f"extraction engine {engine_id!r} returned a non-object result")
    result.setdefault("engine", {"id": engine.id, "version": str(getattr(engine, "version", "unknown"))})
    _validate_result(result, engine_id)
    return result
