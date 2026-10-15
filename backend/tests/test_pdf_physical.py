from __future__ import annotations

import json
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NumberObject,
    RectangleObject,
    TextStringObject,
)
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.main import create_app
from app.models import Base
from app.pdf_physical import (
    _bound_canonical_hierarchy,
    _bound_parser_observations,
    extract_pdf_physical,
)
from app.storage import LocalStore


def _physical_pdf(*, include_attachment: bool = True, rotation: int = 0,
                  crop_box: tuple[int, int, int, int] | None = None,
                  attachment_payload: bytes = b"attachment content") -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    writer.add_metadata({"/Title": "physical fixture", "/Author": "test"})
    if rotation:
        page[NameObject("/Rotate")] = NumberObject(rotation)
    if crop_box:
        page.cropbox = RectangleObject(crop_box)
    font = writer._add_object(DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica-Bold"),
    }))
    image = DecodedStreamObject()
    image.set_data(b"\xff\x00\x00")
    image.update({NameObject("/Type"): NameObject("/XObject"),
                  NameObject("/Subtype"): NameObject("/Image"),
                  NameObject("/Width"): NumberObject(1), NameObject("/Height"): NumberObject(1),
                  NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
                  NameObject("/BitsPerComponent"): NumberObject(8)})
    resources = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): font}),
        NameObject("/XObject"): DictionaryObject({NameObject("/Im0"): writer._add_object(image)}),
    })
    page[NameObject("/Resources")] = resources
    content = DecodedStreamObject()
    content.set_data(b"BT /F1 12 Tf 72 720 Td (Alpha) Tj 0 -18 Td (Beta) Tj ET "
                     b"0 0 1 RG 2 w 10 10 m 100 100 l S "
                     b"q 612 0 0 792 0 0 cm /Im0 Do Q q 100 0 0 100 10 20 cm /Im0 Do Q")
    page[NameObject("/Contents")] = writer._add_object(content)
    for uri in ("https://example.test/path", "javascript:alert(1)"):
        action = writer._add_object(DictionaryObject({
            NameObject("/S"): NameObject("/URI"), NameObject("/URI"): TextStringObject(uri)}))
        annotation = writer._add_object(DictionaryObject({
            NameObject("/Type"): NameObject("/Annot"), NameObject("/Subtype"): NameObject("/Link"),
            NameObject("/Rect"): ArrayObject([NumberObject(v) for v in (20, 20, 80, 40)]),
            NameObject("/A"): action,
        }))
        page.setdefault(NameObject("/Annots"), ArrayObject()).append(annotation)
    internal = writer._add_object(DictionaryObject({
        NameObject("/Type"): NameObject("/Annot"), NameObject("/Subtype"): NameObject("/Link"),
        NameObject("/Rect"): ArrayObject([NumberObject(1), NumberObject(1), NumberObject(10), NumberObject(10)]),
        NameObject("/Dest"): ArrayObject([page.indirect_reference, NameObject("/Fit")]),
    }))
    page.setdefault(NameObject("/Annots"), ArrayObject()).append(internal)
    comment = writer._add_object(DictionaryObject({
        NameObject("/Type"): NameObject("/Annot"), NameObject("/Subtype"): NameObject("/Text"),
        NameObject("/Rect"): ArrayObject([NumberObject(5), NumberObject(6), NumberObject(25), NumberObject(30)]),
        NameObject("/Contents"): TextStringObject("review note"),
        NameObject("/T"): TextStringObject("reviewer"),
    }))
    page[NameObject("/Annots")].append(comment)
    if include_attachment:
        embedded = DecodedStreamObject()
        embedded.set_data(attachment_payload)
        embedded.update({NameObject("/Type"): NameObject("/EmbeddedFile"),
                         NameObject("/Subtype"): NameObject("/text#2Fplain"),
                         NameObject("/Params"): DictionaryObject({
                             NameObject("/Size"): NumberObject(len(attachment_payload))})})
        embedded_ref = writer._add_object(embedded)
        filespec = writer._add_object(DictionaryObject({
            NameObject("/Type"): NameObject("/Filespec"), NameObject("/F"): TextStringObject("note.txt"),
            NameObject("/UF"): TextStringObject("note.txt"),
            NameObject("/Desc"): TextStringObject("fixture attachment"),
            NameObject("/AFRelationship"): NameObject("/Supplement"),
            NameObject("/EF"): DictionaryObject({NameObject("/F"): embedded_ref}),
        }))
        writer._root_object[NameObject("/Names")] = DictionaryObject({
            NameObject("/EmbeddedFiles"): DictionaryObject({
                NameObject("/Names"): ArrayObject([TextStringObject("note.txt"), filespec])})})
        attachment = writer._add_object(DictionaryObject({
            NameObject("/Type"): NameObject("/Annot"), NameObject("/Subtype"): NameObject("/FileAttachment"),
            NameObject("/Rect"): ArrayObject([NumberObject(30), NumberObject(6), NumberObject(45), NumberObject(30)]),
            NameObject("/FS"): filespec,
        }))
        page[NameObject("/Annots")].append(attachment)
    writer.add_outline_item("Contents", 0)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_physical_text_levels_styles_positions_and_optional_characters():
    model = extract_pdf_physical(_physical_pdf(), include_characters=True)
    page = model["pages"][0]
    assert [line["text"] for line in page["lines"]] == ["Alpha", "Beta"]
    assert page["blocks"] and page["spans"]
    assert page["spans"][0]["font"]["name"].endswith("Helvetica-Bold")
    assert page["spans"][0]["font"]["bold"] is True
    assert page["spans"][0]["origin"] is not None
    if model["canonical_text_engine"]["id"] == "pymupdf":
        assert page["spans"][0]["box"] is not None
    else:
        assert page["spans"][0]["box"] is None
    assert "".join(char["text"] for char in page["characters"]) == "".join(
        span["text"] for span in page["spans"])
    assert not any("text_bounds_unavailable" in warning for warning in page["diagnostics"])


def test_physical_style_and_vector_records_keep_parser_evidence():
    pymupdf = pytest.importorskip("pymupdf")
    document = pymupdf.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((40, 80), "Underlined", fontsize=18)
    page.draw_line((40, 83), (125, 83), color=(1, 0, 0), width=1.5)
    model = extract_pdf_physical(document.tobytes())
    document.close()

    result = model["pages"][0]
    span = next(item for item in result["spans"] if item["text"] == "Underlined")
    assert span["font"]["superscript_source"] == "pymupdf_computed_flag"
    assert span["style_evidence"]["underline"]["source"] == "pymupdf_char_flags"
    assert span["font"]["underline"] is True
    path = next(item for item in result["vector_graphics"] if item["item_count"])
    assert path["items"][0][0] == "l"
    assert path["color"] == [1.0, 0.0, 0.0]
    assert path["width_points"] == 1.5


def test_physical_images_vectors_links_and_bookmarks_are_provenance_linked():
    model = extract_pdf_physical(_physical_pdf())
    page = model["pages"][0]
    assert len(page["images"]) == 2
    assert page["images"][0]["asset_id"] == page["images"][1]["asset_id"]
    image = page["images"][0]
    assert image["box"] == [0, 0, 612, 792]
    assert page["images"][1]["box"] == [10, 672, 110, 772]
    asset = next(item for item in model["assets"] if item["id"] == image["asset_id"])
    assert asset["media_type"] == "image/png"
    assert asset["byte_length"] > 0 and asset["data_base64"]
    assert page["vector_graphics"][0]["box"] == [10, 692, 100, 782]
    assert len(model["links"]) == 3
    assert model["links"][0]["target"]["uri"] == "https://example.test/path"
    assert model["links"][1]["target"]["unsupported_reason"] == "unsupported_uri_scheme"
    assert model["links"][2]["target"]["page_number"] == 1
    comment = next(item for item in model["annotations"] if item["subtype"] == "Text")
    assert comment["contents"] == "review note" and comment["author"] == "reviewer" and comment["box"]
    attachment = next(item for item in model["annotations"] if item["subtype"] == "FileAttachment")
    assert attachment["file_attachment"]["filename"] == "note.txt"
    assert attachment["file_attachment"]["payload_extracted"] is False
    assert attachment["file_attachment"]["description"] == "fixture attachment"
    assert attachment["file_attachment"]["media_type"] == "text/plain"
    assert model["attachments"][0]["file_attachment"]["declared_size_bytes"] == len(b"attachment content")
    assert model["attachments"][0]["source"] == "document_embedded_files_name_tree"
    assert attachment["file_attachment"]["id"] == model["attachments"][0]["id"]
    assert model["bookmarks"] == [{"title": "Contents", "level": 0, "page_number": 1}]


def test_physical_character_capture_is_disabled_by_default():
    page = extract_pdf_physical(_physical_pdf())["pages"][0]
    assert page["characters"] is None


def test_physical_content_records_independent_parser_observations():
    pytest.importorskip("pymupdf")
    pytest.importorskip("pdfplumber")
    pytest.importorskip("pdfminer.high_level")
    model = extract_pdf_physical(_physical_pdf(), include_characters=True)
    assert model["schema_version"] == 2
    assert model["canonical_text_engine"]["id"] == "pymupdf"
    assert {item["id"] for item in model["parsers"]} == {"pypdf", "pymupdf", "pdfplumber", "pdfminer.six"}
    page = model["pages"][0]
    by_parser = {item["parser"]: item for item in page["parser_observations"]}
    assert by_parser["pdfplumber"]["characters"]
    assert by_parser["pdfminer.six"]["text_boxes"]
    assert all("coordinate_space" in item for item in by_parser.values())
    assert page["spans"] and page["spans"][0]["source"]["parser"] == "pymupdf"
    assert page["spans"][0]["box"] and page["spans"][0]["character_ids"]


def test_canonical_hierarchy_ids_orders_and_parent_links_are_repeatable():
    pytest.importorskip("pymupdf")
    data = _physical_pdf()
    first = extract_pdf_physical(data, include_characters=True)["pages"][0]
    second = extract_pdf_physical(data, include_characters=True)["pages"][0]
    for kind in ("blocks", "lines", "spans", "characters"):
        items = first[kind]
        assert [item["id"] for item in items] == [item["id"] for item in second[kind]]
        assert len({item["id"] for item in items}) == len(items)
        assert [item["source_order"] for item in items] == sorted(
            item["source_order"] for item in items)
    block_ids = {item["id"] for item in first["blocks"]}
    line_by_id = {item["id"]: item for item in first["lines"]}
    span_by_id = {item["id"]: item for item in first["spans"]}
    char_by_id = {item["id"]: item for item in first["characters"]}
    all_ids = [item["id"] for kind in ("blocks", "lines", "spans", "characters")
               for item in first[kind]]
    assert len(all_ids) == len(set(all_ids))
    for block in first["blocks"]:
        assert all(line_id in line_by_id for line_id in block["line_ids"])
        assert block["text"] == "\n".join(line_by_id[line_id]["text"] for line_id in block["line_ids"])
    for line in first["lines"]:
        assert line["block_id"] in block_ids
        assert all(span_id in span_by_id for span_id in line["span_ids"])
        assert line["text"] == "".join(span_by_id[span_id]["text"] for span_id in line["span_ids"])
    for span in first["spans"]:
        assert span["block_id"] in block_ids
        assert span["line_id"] in line_by_id
        assert all(char_id in char_by_id for char_id in span["character_ids"])
    assert "".join(item["text"] for item in first["characters"]) == "".join(
        item["text"] for item in first["spans"])


def test_pypdf_fallback_keeps_a_linked_hierarchy_when_optional_parser_is_missing(monkeypatch):
    import builtins

    original_import = builtins.__import__

    def without_pymupdf(name, *args, **kwargs):
        if name == "pymupdf":
            raise ImportError("simulated optional dependency absence")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_pymupdf)
    model = extract_pdf_physical(_physical_pdf(), include_characters=True)
    page = model["pages"][0]
    assert model["canonical_text_engine"]["id"] == "pypdf"
    assert any(item.startswith("pymupdf_canonical_text_unavailable")
               for item in model["diagnostics"])
    line_by_id = {item["id"]: item for item in page["lines"]}
    span_by_id = {item["id"]: item for item in page["spans"]}
    assert all(line["block_id"] for line in line_by_id.values())
    assert all(span["line_ids"] or not span["text"].strip() for span in span_by_id.values())
    assert all(line_id in line_by_id for span in span_by_id.values()
               for line_id in span["line_ids"])


def test_canonical_boxes_respect_crop_and_page_rotation():
    pytest.importorskip("pymupdf")
    unrotated = extract_pdf_physical(
        _physical_pdf(rotation=0, crop_box=(20, 50, 590, 750)))['pages'][0]['spans'][0]['box']
    rotated = extract_pdf_physical(
        _physical_pdf(rotation=90, crop_box=(20, 50, 590, 750)))['pages'][0]['spans'][0]['box']
    assert rotated == pytest.approx([700 - unrotated[3], unrotated[0],
                                     700 - unrotated[1], unrotated[2]])
    for rotation in (0, 90, 180, 270):
        model = extract_pdf_physical(_physical_pdf(rotation=rotation, crop_box=(20, 50, 590, 750)))
        page = model["pages"][0]
        width, height = ((700, 570) if rotation % 180 else (570, 700))
        boxes = [item["box"] for item in page["blocks"] + page["lines"] + page["spans"]]
        assert boxes
        assert all(0 <= box[0] <= box[2] <= width and 0 <= box[1] <= box[3] <= height
                   for box in boxes)


def test_canonical_source_order_preserves_multicolumn_stream_and_unicode_whitespace():
    pymupdf = pytest.importorskip("pymupdf")
    document = pymupdf.open()
    page = document.new_page(width=300, height=400)
    for point, text in (((20, 40), "LEFT TOP"), ((160, 40), "RIGHT TOP"),
                        ((20, 80), "LEFT BOTTOM"), ((160, 80), "RIGHT BOTTOM"),
                        ((20, 120), "Caf\u00e9  end")):
        page.insert_text(point, text, fontname="helv", fontsize=12)
    payload = document.tobytes()
    document.close()

    model = extract_pdf_physical(payload, include_characters=True)
    result = model["pages"][0]
    assert [block["source_order"] for block in result["blocks"]] == [0, 1, 2]
    assert result["blocks"][0]["text"] == "LEFT TOP\nRIGHT TOP"
    assert result["blocks"][1]["text"] == "LEFT BOTTOM\nRIGHT BOTTOM"
    assert any(span["text"] == "Caf\u00e9  end" for span in result["spans"])
    assert "".join(char["text"] for char in result["characters"]) == "".join(
        span["text"] for span in result["spans"])


def test_parser_observation_details_have_a_document_wide_output_limit():
    observations = [{"parser": "pymupdf", "text_spans": [{"text": "x" * 600_000}]},
                    {"parser": "pdfplumber", "characters": [{"text": "y" * 600_000}]}]
    assert _bound_parser_observations(observations) is True
    assert len(observations[1]["characters"]) == 0
    assert observations[1]["details_truncated"] is True


def test_canonical_hierarchy_budget_truncates_optional_characters_without_dangling_refs():
    ids = [f"char-{index}" for index in range(30_000)]
    page = {"page_number": 1, "blocks": [], "lines": [],
            "spans": [{"id": "span-1", "character_ids": ids}],
            "characters": [{"id": item, "span_id": "span-1", "text": "x"} for item in ids],
            "diagnostics": []}
    assert _bound_canonical_hierarchy([page]) is True
    assert page["characters"] == []
    assert page["spans"][0]["character_ids"] is None
    assert "canonical_characters_truncated_document_limit" in page["diagnostics"]


def test_canonical_hierarchy_budget_truncates_whole_page_subtrees():
    page = {"page_number": 1, "blocks": [{"id": "b1", "line_ids": ["l1"], "text": "x" * 800_000}],
            "lines": [{"id": "l1", "block_id": "b1", "span_ids": ["s1"], "text": "x" * 800_000}],
            "spans": [{"id": "s1", "block_id": "b1", "line_id": "l1", "text": "x" * 800_000}],
            "characters": None, "diagnostics": []}
    assert _bound_canonical_hierarchy([page]) is True
    assert page["blocks"] == page["lines"] == page["spans"] == []
    assert "canonical_text_page_truncated_document_limit" in page["diagnostics"]


def test_ingestion_persists_physical_contract_and_serves_separate_image_asset(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with TestClient(create_app(settings=Settings(job_cpu_seconds=20), engine=engine,
                               store=LocalStore(tmp_path / "objects", 2_000_000), frontend=tmp_path)) as client:
        response = client.post("/api/ingestions?filename=physical.pdf&include_characters=true",
                               content=_physical_pdf(include_attachment=False),
                               headers={"content-type": "application/pdf"})
        assert response.status_code == 201, response.text
        model = client.get(response.json()["result_url"]).json()["page_model"]
        physical = model["physical_content"]
        assert physical["schema_version"] == 2
        assert model["source"]["metadata"]["title"] == "physical fixture"
        assert physical["pages"][0]["spans"][0]["text"].startswith("Alpha")
        assert "".join(char["text"] for char in physical["pages"][0]["characters"]) == "".join(
            span["text"] for span in physical["pages"][0]["spans"])
        asset = physical["assets"][0]
        downloaded = client.get(asset["url"])
        assert downloaded.status_code == 200
        assert downloaded.headers["content-type"] == "image/png"
        assert downloaded.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_ingestion_accepts_opaque_embedded_file_metadata_without_exposing_payload(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    secret = b"opaque payload /OpenAction /JavaScript (do not expose)"
    with TestClient(create_app(settings=Settings(job_cpu_seconds=20), engine=engine,
                               store=LocalStore(tmp_path / "objects", 2_000_000), frontend=tmp_path)) as client:
        response = client.post("/api/ingestions?filename=with-attachment.pdf",
                               content=_physical_pdf(attachment_payload=secret),
                               headers={"content-type": "application/pdf"})
        assert response.status_code == 201, response.text
        result = client.get(response.json()["result_url"])
        assert result.status_code == 200
        physical = result.json()["page_model"]["physical_content"]
        serialized = json.dumps(physical)
        assert secret.decode() not in serialized
        attachment = physical["attachments"][0]
        assert attachment["file_attachment"]["payload_extracted"] is False
        assert client.get(f"/api/ingestions/{response.json()['id']}/assets/{attachment['id']}").status_code == 404
        for asset in physical["assets"]:
            downloaded = client.get(asset["url"])
            assert downloaded.status_code == 200
            assert secret not in downloaded.content
