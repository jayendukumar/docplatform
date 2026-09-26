"""Bounded, offline DOCX placeholder and repeated-row merging."""
from __future__ import annotations

import copy
import io
import re
from pathlib import PurePosixPath
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from app.template_logic import resolve_path


class WordMergeError(ValueError):
    pass


_TOKEN = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_.]*(?:\[\d+\])*)\s*\}\}")
_LOOP = re.compile(r"\{\{\s*#\s*([A-Za-z_][A-Za-z0-9_.]*(?:\[\d+\])*)\s*\}\}.*?\{\{\s*/\s*\1\s*\}\}", re.DOTALL)
_TEXT_TAG = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
_ROW_TAG = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr"
_MAX_ENTRIES = 1_000
_MAX_UNCOMPRESSED = 50 * 1024 * 1024


def _safe_package(data: bytes) -> ZipFile:
    try:
        package = ZipFile(io.BytesIO(data))
    except BadZipFile:
        raise WordMergeError("DOCX package is not a valid ZIP archive") from None
    if len(package.infolist()) > _MAX_ENTRIES:
        package.close()
        raise WordMergeError("DOCX package contains too many entries")
    total = 0
    for info in package.infolist():
        name = info.filename.replace("\\", "/")
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or name.startswith("/"):
            package.close()
            raise WordMergeError("DOCX package contains an unsafe path")
        total += info.file_size
        if total > _MAX_UNCOMPRESSED:
            package.close()
            raise WordMergeError("DOCX package is too large after decompression")
        if name.lower().endswith("vbaProject.bin"):
            package.close()
            raise WordMergeError("DOCX macros are not supported")
        content = package.read(info)
        if b'TargetMode="External"' in content or b"TargetMode='External'" in content:
            package.close()
            raise WordMergeError("DOCX external relationships are not supported")
    if "word/document.xml" not in package.namelist():
        package.close()
        raise WordMergeError("DOCX package has no main document")
    return package


def validate_docx_package(data: bytes) -> None:
    """Validate a DOCX package without interpreting or modifying its XML."""
    package = _safe_package(data)
    package.close()


def _value(data: Any, path: str, *, scalar: bool = True) -> Any:
    value, found = resolve_path(data, path)
    if not found or value is None:
        raise WordMergeError(f"Missing Word template field: {path}")
    if scalar and isinstance(value, (dict, list)):
        raise WordMergeError(f"Word template field must be scalar: {path}")
    return value


def _replace_text(text: str, data: Any, *, loop_item: Any = None) -> str:
    context = data
    if loop_item is not None:
        context = dict(data) if isinstance(data, dict) else {}
        context["item"] = loop_item
    return _TOKEN.sub(lambda match: str(_value(context, match.group(1))), text)


def _row_text(row: ET.Element) -> str:
    return "".join(node.text or "" for node in row.iter(_TEXT_TAG))


def _merge_xml(xml: bytes, data: dict[str, Any]) -> bytes:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        raise WordMergeError("DOCX XML part is malformed") from None
    parents = {child: parent for parent in root.iter() for child in parent}
    for row in list(root.iter(_ROW_TAG)):
        text = _row_text(row)
        marker = _LOOP.fullmatch(text.strip())
        if not marker:
            continue
        values = _value(data, marker.group(1), scalar=False)
        if not isinstance(values, list) or len(values) > 1_000:
            raise WordMergeError(f"Word loop source must be an array of at most 1000 items: {marker.group(1)}")
        parent = parents.get(row)
        if parent is None:
            raise WordMergeError("Word loop row has no parent")
        position = list(parent).index(row)
        parent.remove(row)
        for offset, item in enumerate(values):
            clone = copy.deepcopy(row)
            for text_node in clone.iter(_TEXT_TAG):
                text_node.text = _replace_text(text_node.text or "", data, loop_item=item)
                text_node.text = text_node.text.replace("{{#" + marker.group(1) + "}}", "")
                text_node.text = text_node.text.replace("{{/" + marker.group(1) + "}}", "")
            parent.insert(position + offset, clone)
    for text_node in root.iter(_TEXT_TAG):
        text_node.text = _replace_text(text_node.text or "", data)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def merge_docx(template: bytes, data: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    """Merge scalar tokens and same-row repeated tables into a safe DOCX package.

    Tokens must be contained in individual Word text nodes. Repeated rows use
    ``{{#items}} ... {{/items}}`` in one table row and reference ``{{item.field}}``.
    Images and arbitrary Word fields are preserved but not interpreted.
    """
    if not isinstance(data, dict):
        raise WordMergeError("Word merge data must be an object")
    package = _safe_package(template)
    output = io.BytesIO()
    merged_parts: list[str] = []
    try:
        with ZipFile(output, "w", ZIP_DEFLATED) as destination:
            for info in package.infolist():
                content = package.read(info)
                if info.filename == "word/document.xml" or info.filename.startswith(("word/header", "word/footer")):
                    content = _merge_xml(content, data)
                    merged_parts.append(info.filename)
                destination.writestr(info, content)
    finally:
        package.close()
    return output.getvalue(), {"format": "docx", "merged_parts": merged_parts,
                               "data_keys": sorted(data), "engine": "docx-merge-v1"}
