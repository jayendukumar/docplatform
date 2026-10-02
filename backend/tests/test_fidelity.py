"""E16 Phase A regression tests: SourceModel, comparison and capability manifest (DD-418)."""
import re
import sys
from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NumberObject,
)

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.capabilities import capability_manifest, declared_keys
from fidelity.compare import compare_models
from fidelity.source_model import PT_TO_MM, analyse_pdf, font_traits

REPOSITORY = BACKEND.parent


def make_pdf(content: str, *, widths: list[int] | None = None, first_char: int = 65,
             base_font: str = "Helvetica") -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(612, 792)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject(f"/{base_font}")})
    if widths is not None:
        font[NameObject("/FirstChar")] = NumberObject(first_char)
        font[NameObject("/LastChar")] = NumberObject(first_char + len(widths) - 1)
        font[NameObject("/Widths")] = ArrayObject(NumberObject(w) for w in widths)
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
    stream = DecodedStreamObject()
    stream.set_data(content.encode("latin-1"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def mm(points: float) -> float:
    return round(points * PT_TO_MM, 3)


def words_of(content: str, **kwargs) -> list[dict]:
    return analyse_pdf(make_pdf(content, **kwargs))["pages"][0]["words"]


def test_text_position_size_and_font_traits():
    model = analyse_pdf(make_pdf("BT /F1 12 Tf 1 0 0 1 72 720 Tm (Hello world) Tj ET", base_font="ABCDEF+Times-Bold"))
    first = model["pages"][0]["words"][0]
    assert model["contract"] == "source-model-v2"
    assert first["x_mm"] == pytest.approx(mm(72), abs=0.01)
    assert first["y_mm"] == pytest.approx(mm(792 - 720), abs=0.01)
    assert first["size_pt"] == pytest.approx(12)
    assert first["font"] == "Times-Bold" and first["bold"] and first["family_class"] == "serif"
    assert [w["text"] for w in model["pages"][0]["words"]] == ["Hello", "world"]
    assert font_traits("/LiberationSans-BoldItalic") == {"font": "LiberationSans-BoldItalic", "family_class": "sans",
                                                          "bold": True, "italic": True}


def test_leading_follows_the_pdf_text_state():
    # pypdf 6.1.3's extractor double-scales T* leading; the interpreter must not.
    content = ("BT /F1 10 Tf 72 700 Td (A) Tj 0 -14 TD (B) Tj T* (C) Tj ET "
               "BT /F1 10 Tf 14 TL 72 600 Td (D) Tj T* (E) Tj (F) ' ET")
    words = {w["text"]: w for w in words_of(content)}
    assert words["B"]["y_mm"] == pytest.approx(mm(792 - 686), abs=0.01)
    assert words["C"]["y_mm"] == pytest.approx(mm(792 - 672), abs=0.01)
    assert words["E"]["y_mm"] == pytest.approx(mm(792 - 586), abs=0.01)
    assert words["F"]["y_mm"] == pytest.approx(mm(792 - 572), abs=0.01)
    assert words["F"]["x_mm"] == pytest.approx(mm(72), abs=0.01)


def test_glyph_advance_uses_font_widths_spacing_and_kerning():
    # Widths: A=500, B=600 glyph units. Consecutive Tj continue after the previous advance.
    words = words_of("BT /F1 10 Tf 72 700 Td (AB) Tj (A) Tj ET", widths=[500, 600])
    assert [(w["text"], w["width_source"]) for w in words] == [("ABA", "font-widths")]
    assert words[0]["width_mm"] == pytest.approx(mm(16), abs=0.01)
    spaced = words_of("BT /F1 10 Tf 2 Tc 72 700 Td (AB) Tj ET", widths=[500, 600])
    assert spaced[0]["width_mm"] == pytest.approx(mm(15), abs=0.01)
    kerned = words_of("BT /F1 10 Tf 72 700 Td [(A) -1000 (B)] TJ ET", widths=[500, 600])
    assert [w["text"] for w in kerned] == ["A", "B"]
    assert kerned[1]["x_mm"] == pytest.approx(mm(72 + 5 + 10), abs=0.01)


def test_graphics_are_classified_as_rules_boxes_and_segments():
    content = ("72 700 400 0.5 re f 72 600 100 50 re S 72 500 100 50 re f "
               "72 400 m 300 400 l S 72 300 m 200 200 l S")
    kinds = sorted(g["kind"] for g in analyse_pdf(make_pdf(content))["pages"][0]["graphics"])
    assert kinds == ["box", "filled-box", "rule", "rule", "segment"]


def test_off_page_and_invisible_text_are_flagged_and_excluded_from_lines():
    model = analyse_pdf(make_pdf("BT /F1 10 Tf 72 -500 Td (Hidden) Tj ET BT 3 Tr /F1 10 Tf 72 650 Td (Ocr) Tj ET "
                                 "BT 0 Tr /F1 10 Tf 72 700 Td (Shown) Tj ET"))  # Tr persists after ET, per the PDF text state
    flags = {w["text"]: (w["off_page"], w["invisible"]) for w in model["pages"][0]["words"]}
    assert flags == {"Hidden": (True, False), "Ocr": (False, True), "Shown": (False, False)}
    assert model["summary"]["off_page_words"] == 1 and model["summary"]["invisible_words"] == 1
    assert [line["text"] for line in model["pages"][0]["lines"]] == ["Shown"]


def test_lines_split_at_large_gaps_and_words_split_at_size_changes():
    model = analyse_pdf(make_pdf("BT /F1 10 Tf 72 700 Td (Left) Tj 300 0 Td (Right) Tj ET "
                                 "BT /F1 1 Tf 72 650 Td (marker) Tj /F1 10 Tf (Body) Tj ET"))
    assert [line["text"] for line in model["pages"][0]["lines"]] == ["Left", "Right", "markerBody"]  # no visible gap, so no space
    assert [w["text"] for w in model["pages"][0]["words"]][-2:] == ["marker", "Body"]


SOURCE = "BT /F1 10 Tf 72 700 Td (Alpha beta gamma) Tj 0 -14 Td (delta epsilon) Tj ET 72 650 400 0.5 re f"


def test_identical_documents_compare_perfectly():
    model = analyse_pdf(make_pdf(SOURCE))
    report = compare_models(model, model)
    summary = report["summary"]
    assert report["contract"] == "fidelity-comparison-v1"
    assert summary["text"]["f1"] == 1.0 and summary["reading_order"] == 1.0
    assert summary["position_mm"]["within_1mm"] == 1.0
    assert summary["typography"]["size_within_tolerance"] == 1.0
    assert summary["graphics"]["recall"] == 1.0 and summary["differences"] == {}


def test_comparison_localises_moved_missing_and_artifact_text():
    source = analyse_pdf(make_pdf(SOURCE))
    candidate = analyse_pdf(make_pdf(
        "BT /F1 1 Tf 92 700 Td (__DOCPLATFORM_ANCHOR_a__) Tj /F1 12 Tf 0 0 Td (Alpha beta gamma) Tj "
        "0 -14 Td (delta) Tj ET"))
    report = compare_models(source, candidate)
    summary = report["summary"]
    assert summary["renderer_artifact_words"]["candidate"] == 1
    assert summary["text"]["recall"] == pytest.approx(0.8)
    assert summary["differences"] == {"moved": 1, "missing": 1}
    moved = next(d for d in report["differences"] if d["kind"] == "moved")
    # The first word moves exactly 20 pt; the larger candidate font pushes later words further right.
    assert mm(20) <= moved["median_shift_mm"][0] <= mm(20) + 3 and moved["median_shift_mm"][1] == 0
    missing = next(d for d in report["differences"] if d["kind"] == "missing")
    assert missing["source"]["excerpt"] == "epsilon"
    assert summary["typography"]["size_within_tolerance"] == 0.0
    assert summary["graphics"] == {"source": 1, "candidate": 0, "matched": 0, "recall": 0.0, "precision": None}


# --- capability manifest (E16-05) ---------------------------------------------------------------

_INTERNAL_OR_ALIAS = {"__html", "__marker", "richText", "rich_text", "type", "fontFamily", "fontSize", "type_name",
                      "name", "blocks", "data_schema", "sample_data", "allow_external_sources",
                      "allowed_image_hosts", "page"}


def test_manifest_declares_every_property_the_renderer_reads():
    source = (REPOSITORY / "backend" / "app" / "rendering.py").read_text(encoding="utf-8")
    read = set(re.findall(r'\b(?:block|page|column|style|run|paragraph|metadata|definition|row_condition)'
                          r'\.get\("([A-Za-z_]+)"', source))
    undeclared = read - declared_keys() - _INTERNAL_OR_ALIAS
    assert not undeclared, f"renderer reads properties missing from the capability manifest: {sorted(undeclared)}"


def test_manifest_control_properties_are_referenced_by_the_editor():
    frontend = "".join(path.read_text(encoding="utf-8") for path in (REPOSITORY / "frontend" / "src").glob("*.ts*"))
    manifest = capability_manifest()
    missing = []
    for name, component in manifest["components"].items():
        for key, spec in component["properties"].items():
            if spec["ui"] == "control" and not re.search(rf"\b{key}\b", frontend):
                missing.append(f"{name}.{key}")
    for key, spec in manifest["page"]["properties"].items():
        if spec["ui"] == "control" and not re.search(rf"\b{key}\b", frontend):
            missing.append(f"page.{key}")
    assert not missing, f"manifest claims editor controls the frontend never references: {missing}"


def test_manifest_is_a_defensive_copy_with_valid_ui_values():
    manifest = capability_manifest()
    manifest["components"].clear()
    assert capability_manifest()["components"]
    for component in capability_manifest()["components"].values():
        assert all(spec["ui"] in {"control", "json", "none"} for spec in component["properties"].values())


def test_capabilities_route_serves_the_manifest(tmp_path):
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    from app.main import create_app
    from app.models import Base
    from app.storage import LocalStore

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    frontend = tmp_path / "dist"
    frontend.mkdir()
    (frontend / "index.html").write_text("ok", encoding="utf-8")
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=frontend)) as client:
        response = client.get("/api/editor/capabilities")
        assert response.status_code == 200
        assert response.json()["version"] == "editor-capabilities-v1"
        assert "/api/editor/capabilities" in client.get("/openapi.json").json()["paths"]
