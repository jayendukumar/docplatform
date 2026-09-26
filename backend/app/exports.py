"""Small, dependency-free export writers for approved extraction results."""
from __future__ import annotations

from io import BytesIO
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape


EXPORT_COLUMNS = (
    "field", "original_value", "normalized_value", "confidence", "review_status",
    "source_page", "source_box", "validation", "result_status",
)


def extraction_rows(result: dict[str, Any], result_status: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for name, field in result.get("fields", {}).items():
        if not isinstance(field, dict):
            continue
        source = field.get("source") or {}
        rows.append([
            str(name),
            _cell_value(field.get("original_value")),
            _cell_value(field.get("normalized_value")),
            _cell_value(field.get("confidence")),
            _cell_value(field.get("review_status")),
            _cell_value(source.get("page_number")),
            _cell_value(source.get("box")),
            _cell_value(field.get("validation")),
            str(result_status),
        ])
    return rows


def _cell_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        import json
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def extraction_xlsx(result: dict[str, Any], result_status: str) -> bytes:
    """Create a minimal OOXML workbook using inline strings.

    Inline strings avoid a shared-string table and keep this export offline and
    independent of a spreadsheet package. Values are intentionally exported as
    strings so original/normalized values and diagnostics cannot be coerced.
    """
    rows = [list(EXPORT_COLUMNS), *extraction_rows(result, result_status)]
    sheet_rows = []
    for row_index, row in enumerate(rows, 1):
        cells = []
        for column_index, value in enumerate(row):
            reference = f"{_column_name(column_index + 1)}{row_index}"
            cells.append(f'<c r="{reference}" t="inlineStr"><is><t>{escape(value)}</t></is></c>')
        sheet_rows.append(f'<row r="{row_index}">' + "".join(cells) + "</row>")
    worksheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheetData>' + "".join(sheet_rows) + '</sheetData></worksheet>'
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Extraction" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/></Relationships>'
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>'
    )
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as bundle:
        bundle.writestr("[Content_Types].xml", content_types)
        bundle.writestr("_rels/.rels", root_rels)
        bundle.writestr("xl/workbook.xml", workbook)
        bundle.writestr("xl/_rels/workbook.xml.rels", rels)
        bundle.writestr("xl/worksheets/sheet1.xml", worksheet)
    return output.getvalue()


def _column_name(number: int) -> str:
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result
