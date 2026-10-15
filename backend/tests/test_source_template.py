import base64
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from app.ingestion import clean_extracted_text, simple_docx_document
from app.source_template import approved_items, interpret_page_model, template_from_interpretation


def test_extracted_word_markup_is_not_presented_as_document_content():
    cleaned = clean_extracted_text('Ideas <w:tblPr><w:tblW w:type="auto" w:w="0"/> shaping the quarter')
    assert cleaned == 'Ideas shaping the quarter'
    assert '<w:' not in cleaned


def test_interpretation_preserves_source_coordinates_and_versions():
    interpretation = interpret_page_model({
        "schema_version": 7,
        "pages": [{"page_number": 2, "elements": [{"id": "t1", "type": "text",
                                                        "text": "Invoice {{number}}", "box": [1, 2, 3, 4]}]}],
    })
    item = interpretation["items"][0]
    assert item["kind"] == "variable"
    assert item["provenance"] == {"page_number": 2, "element_id": "t1", "box": [1, 2, 3, 4]}
    assert item["source_version"] == 7


def test_structural_content_is_ready_without_individual_approval():
    interpretation = interpret_page_model({
        "pages": [{"page_number": 1, "elements": [
            {"id": "h1", "type": "text", "role": "heading", "text": "NORTHBRIDGE SIGNAL", "box": [1, 20, 300, 40]},
            {"id": "p1", "type": "text", "role": "text", "text": "A readable paragraph.", "box": [1, 80, 300, 100]},
            {"id": "f1", "type": "text", "role": "text", "text": "Revenue = price × volume", "box": [1, 120, 300, 140]},
        ]}],
    })
    assert [item["kind"] for item in interpretation["items"]] == ["header", "paragraph", "formula"]
    assert [item["status"] for item in interpretation["items"]] == ["auto_accepted", "auto_accepted", "suggested"]
    assert interpretation["summary"]["review_required"] == 1
    assert len(approved_items(interpretation)) == 2


def test_generation_uses_only_approved_items():
    interpretation = {"engine": {"version": "1"}, "items": [
        {"id": "approved", "kind": "fixed", "normalized_value": "Keep", "status": "approved"},
        {"id": "suggested", "kind": "fixed", "normalized_value": "Do not use", "status": "suggested"},
    ], "summary": {"elements": 2, "ready": 0, "review_required": 2}}
    assert approved_items(interpretation)[0]["id"] == "approved"
    definition = template_from_interpretation(interpretation, "Draft")
    assert [block["text"] for block in definition["blocks"]] == ["Keep"]
    assert definition["source_generation"]["approved_item_ids"] == ["approved"]


def test_generation_accepts_legacy_fixed_items_from_previous_sessions():
    interpretation = {"engine": {"version": "1"}, "items": [
        {"id": "legacy-fixed", "kind": "fixed", "normalized_value": "Northbridge Signal", "status": "suggested"},
        {"id": "candidate", "kind": "variable", "normalized_value": "{{quarter}}", "status": "suggested"},
    ]}
    assert [item["id"] for item in approved_items(interpretation)] == ["legacy-fixed"]


def test_empty_interpretation_reports_a_user_actionable_warning():
    interpretation = interpret_page_model({
        "pages": [{"page_number": 1, "elements": []}],
        "processing": {"route": "scan"},
    })
    assert interpretation["status"] == "needs_review"
    assert interpretation["summary"]["pages"] == 1
    assert interpretation["summary"]["review_required"] == 0
    assert any("OCR" in warning for warning in interpretation["warnings"])


def test_docx_structure_and_page_setup_survive_into_editable_definition():
    document_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
      xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body>
      <w:p><w:pPr><w:pStyle w:val="Heading1"/><w:jc w:val="center"/></w:pPr>
        <w:r><w:rPr><w:b/><w:sz w:val="36"/><w:color w:val="123456"/></w:rPr><w:t>Executive Brief</w:t></w:r></w:p>
      <w:p><w:pPr><w:pStyle w:val="ListBullet"/></w:pPr><w:r><w:t>First action</w:t></w:r></w:p>
      <w:tbl><w:tr><w:tc><w:p><w:r><w:t>Metric</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>Value</w:t></w:r></w:p></w:tc></w:tr>
        <w:tr><w:tc><w:p><w:r><w:t>Release cycle</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>6 weeks</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
      <w:sectPr><w:headerReference w:type="default" r:id="rId9"/><w:footerReference w:type="default" r:id="rId10"/>
        <w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="900" w:right="1000" w:bottom="900" w:left="1000"/></w:sectPr>
      </w:body></w:document>'''
    relationships = b'''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId9" Target="header1.xml"/><Relationship Id="rId10" Target="footer1.xml"/></Relationships>'''
    header_xml = b'''<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
      xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
      xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
      xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><w:p><w:r><w:t>NORTHBRIDGE GROUP</w:t></w:r>
      <w:r><w:drawing><wp:inline><wp:extent cx="952500" cy="300000"/><wp:docPr id="1" name="Logo" descr="Brand logo"/>
      <a:graphic><a:graphicData><a:blip r:embed="rId1"/></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p></w:hdr>'''
    header_relationships = b'''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId1" Target="media/logo.png"/></Relationships>'''
    footer_xml = b'''<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>CONFIDENTIAL</w:t></w:r></w:p></w:ftr>'''
    archive_bytes = BytesIO()
    with ZipFile(archive_bytes, "w", ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/_rels/document.xml.rels", relationships)
        archive.writestr("word/header1.xml", header_xml)
        archive.writestr("word/_rels/header1.xml.rels", header_relationships)
        archive.writestr("word/footer1.xml", footer_xml)
        archive.writestr("word/media/logo.png", base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jZ1sAAAAASUVORK5CYII="))

    elements, source_document = simple_docx_document(archive_bytes.getvalue())
    assert [element["type"] for element in elements] == ["text", "text", "table"]
    assert elements[0]["role"] == "heading"
    assert elements[0]["runs"][0]["bold"] is True
    assert elements[1]["role"] == "list_item"
    assert elements[2]["table"]["rows"] == [["Metric", "Value"], ["Release cycle", "6 weeks"]]
    assert source_document["page"]["size"] == "Letter"
    assert source_document["page"]["header_left"] == "NORTHBRIDGE GROUP"
    assert source_document["page"]["footer_left"] == "CONFIDENTIAL"
    assert source_document["header_images"][0]["alt"] == "Brand logo"

    interpretation = interpret_page_model({"schema_version": 1,
        "source_document": source_document,
        "pages": [{"page_number": 1, "elements": elements}]})
    definition = template_from_interpretation(interpretation, "Draft")
    assert definition["page"]["size"] == "Letter"
    assert definition["page"]["header_left"] == "NORTHBRIDGE GROUP"
    assert any(block["type"] == "image" and block["alt"] == "Brand logo"
               for block in definition["blocks"])
    assert any(block["type"] == "table" and block["columns"][0]["header"] == "Metric"
               for block in definition["blocks"])
    assert any(block["type"] == "list" and block["static_items"] == ["First action"]
               for block in definition["blocks"])
    assert any(block["type"] == "rich_text" for block in definition["blocks"])
