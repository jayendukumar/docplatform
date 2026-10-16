import json
import sys
import zlib
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, NumberObject
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.ingestion import (
    UploadClassification,
    _pdf_sources,
    count_pages,
    detect_page_routes,
    page_model,
)
from app.main import create_app
from app.models import Base
from app.pdf_classification import PageClassificationThresholds, classify_pdf_pages
from app.storage import LocalStore


def _png_header(width: int, height: int) -> bytes:
    return (b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" +
            width.to_bytes(4, "big") + height.to_bytes(4, "big") + b"\x08\x02\x00\x00\x00")


def _pdf_pages(*page_text: str | None) -> bytes:
    """Create parser-valid pages with optional Helvetica text for route tests."""
    writer = PdfWriter()
    font = writer._add_object(DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                                                NameObject("/Subtype"): NameObject("/Type1"),
                                                NameObject("/BaseFont"): NameObject("/Helvetica")}))
    for text in page_text or (None,):
        page = writer.add_blank_page(width=612, height=792)
        if text is None:
            continue
        lines = [line.replace("\\", "\\\\").replace("(", r"\(").replace(")", r"\)")
                 for line in text.split("\n")]
        stream = DecodedStreamObject()
        commands = "BT /F1 12 Tf 14 TL 72 720 Td " + " T* T* ".join(f"({line}) Tj" for line in lines) + " ET"
        stream.set_data(commands.encode("latin-1"))
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def _pdf_with_full_page_image(text: str | None = None) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    image = DecodedStreamObject()
    image.set_data(b"\x00\x00\x00")
    image.update({NameObject("/Type"): NameObject("/XObject"),
                  NameObject("/Subtype"): NameObject("/Image"),
                  NameObject("/Width"): NumberObject(1), NameObject("/Height"): NumberObject(1),
                  NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
                  NameObject("/BitsPerComponent"): NumberObject(8)})
    resources = DictionaryObject({NameObject("/XObject"): DictionaryObject({
        NameObject("/Im0"): writer._add_object(image)})})
    commands = "q 612 0 0 792 0 0 cm /Im0 Do Q"
    if text:
        font = writer._add_object(DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                                                      NameObject("/Subtype"): NameObject("/Type1"),
                                                      NameObject("/BaseFont"): NameObject("/Helvetica")}))
        resources[NameObject("/Font")] = DictionaryObject({NameObject("/F1"): font})
        commands += f" BT /F1 12 Tf 72 720 Td ({text}) Tj ET"
    page[NameObject("/Resources")] = resources
    stream = DecodedStreamObject()
    stream.set_data(commands.encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_ingestion_classifies_and_persists_digital_pdf(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        payload = _pdf_pages("hello")
        response = client.post("/api/ingestions?filename=invoice.pdf", content=payload,
                               headers={"content-type": "application/pdf"})
        assert response.status_code == 201, response.text
        document_id = response.json()["id"]
        assert response.json()["route"] == "digital"
        assert response.json()["pages_total"] == 1
        result = client.get(f"/api/ingestions/{document_id}/result")
        assert result.status_code == 200
        assert result.json()["page_model"]["schema_version"] == 1
        elements = result.json()["page_model"]["pages"][0]["elements"]
        assert elements[0]["text"] == "hello" and elements[0]["box"] is None
        assert elements[0]["role"] == "text"
        assert result.json()["page_model"]["pages"][0]["layout"]["reading_order"] == ["p1-text-1"]
        assert "element:p1-text-1 page:1 box:" in result.json()["markdown"]
        source = client.get(f"/api/ingestions/{document_id}/source")
        assert source.status_code == 200
        assert source.headers["content-type"].startswith("application/pdf")
        assert source.content == payload
        assert client.get(f"/api/ingestions/{document_id}").json()["status"] == "queued"
        assert client.get(f"/api/ingestions/{document_id}").json()["pages_processed"] == 0
        extracted = client.post(f"/api/ingestions/{document_id}/extract", json={"schema_id": "invoice"})
        assert extracted.status_code == 200, extracted.text
        progress = client.get(f"/api/ingestions/{document_id}").json()
        assert progress["status"] == "processed"
        assert progress["pages_processed"] == progress["pages_total"] == 1


def test_pdf_page_model_keeps_elements_on_their_source_pages_without_fake_geometry():
    model = page_model("doc", "agreement.pdf", UploadClassification("application/pdf", "digital"),
                       100, 2, [{"id": "p2-text-1", "type": "text", "text": "Clause", "page_number": 2}])
    assert model["pages"][0]["elements"] == []
    assert model["pages"][1]["elements"][0]["text"] == "Clause"
    assert model["pages"][1]["elements"][0]["box"] is None


def test_pdf_page_count_uses_parsed_page_tree():
    from io import BytesIO

    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_blank_page(width=612, height=792)
    output = BytesIO()
    writer.write(output)
    assert count_pages("agreement.pdf", output.getvalue()) == 2


def test_mixed_pdf_page_routes_are_recorded_conservatively():
    payload = _pdf_pages("digital page", None)
    assert detect_page_routes(payload, 2, "scan") == ["digital", "scan"]


def test_pdf_page_classifier_exposes_per_page_evidence_and_configurable_thresholds():
    payload = _pdf_pages("This page contains enough native text to classify it as digital.", None)
    pages = classify_pdf_pages(payload)
    assert [page["classification"] for page in pages] == ["native-text", "scanned"]
    assert pages[0]["metrics"]["text_character_count"] > 20
    assert pages[0]["metrics"]["image_coverage"] == 0
    assert pages[1]["metrics"]["image_placement_count"] == 0
    # Tuned thresholds are retained as classification evidence.
    tuned = classify_pdf_pages(payload, PageClassificationThresholds(min_text_characters=1000))
    assert tuned[0]["thresholds"]["min_text_characters"] == 1000


def test_pdf_page_classifier_uses_image_placement_coverage_to_distinguish_scan_and_mixed():
    scan, mixed = classify_pdf_pages(_pdf_with_full_page_image(), PageClassificationThresholds()) + \
        classify_pdf_pages(_pdf_with_full_page_image("A full page image with a readable text layer."),
                           PageClassificationThresholds())
    assert scan["classification"] == "scanned"
    assert scan["metrics"]["image_coverage"] == 1
    assert mixed["classification"] == "mixed-content"
    assert mixed["metrics"]["image_placement_count"] == 1


def test_mixed_pdf_page_routes_are_exposed_in_result_metadata(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    payload = _pdf_pages("digital page", None)
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        response = client.post("/api/ingestions?filename=mixed.pdf", content=payload,
                               headers={"content-type": "application/pdf"})
        assert response.status_code == 201, response.text
        result = client.get(f"/api/ingestions/{response.json()['id']}/result").json()
        assert [page["route"] for page in result["page_model"]["pages"]] == ["digital", "scan"]
        assert result["page_model"]["processing"]["page_routes"] == ["digital", "scan"]
        assert result["page_model"]["processing"]["ocr"]["status"] == "unavailable"
        assert result["page_model"]["processing"]["ocr"]["reason"] == "configured OCR engine is not installed"


def test_configured_ocr_dispatches_only_mixed_scan_pages(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    command = [sys.executable, "-c", "import json; print(json.dumps({'pages':[{'page_number':1,'elements':[{'text':'should be ignored','box':[1,1,20,12]}]},{'page_number':2,'elements':[{'text':'scanned page','box':[2,3,44,16]}]}]}))"]
    settings = Settings(ocr_command=command)
    payload = _pdf_pages("digital page", None)
    with TestClient(create_app(settings=settings, engine=engine,
                               store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        response = client.post("/api/ingestions?filename=mixed.pdf", content=payload,
                               headers={"content-type": "application/pdf"})
        assert response.status_code == 201, response.text
        result = client.get(f"/api/ingestions/{response.json()['id']}/result").json()
        pages = result["page_model"]["pages"]
        assert pages[0]["elements"][0]["text"] == "digital page"
        assert pages[1]["elements"][0]["text"] == "scanned page"
        report = result["page_model"]["processing"]["ocr"]
        assert report["engine"] == "custom"
        assert report["requested_engine"] == "paddleocr"
        assert report["language"] == "eng"
        assert report["status"] == "completed"
        assert report["pages"] == 1
        assert report["requested_pages"] == [2]
        assert report["requested_regions"] == 0
        assert report["adapter"] == "configured-local-command"


def test_ocr_can_target_bounded_pdf_page_regions(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    command = [sys.executable, "-c", "import json; print(json.dumps({'pages':[{'page_number':1,'elements':[{'text':'crop only','box':[2,3,44,16]}]}]}))"]
    settings = Settings(tesseract_command=command)
    payload = _pdf_pages("digital page", None)
    regions = json.dumps({"2": [[50, 50, 200, 120]]})
    with TestClient(create_app(settings=settings, engine=engine,
                               store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        response = client.post("/api/ingestions", params={"filename": "mixed.pdf", "ocr_engine": "tesseract",
                                                           "ocr_regions": regions},
                               content=payload, headers={"content-type": "application/pdf"})
        assert response.status_code == 201, response.text
        result = client.get(f"/api/ingestions/{response.json()['id']}/result").json()["page_model"]
        report = result["processing"]["ocr"]
        assert report["requested_pages"] == [2]
        assert report["requested_regions"] == 1
        assert result["pages"][1]["elements"][0]["text"] == "crop only"
        box = result["pages"][1]["elements"][0]["box"]
        assert box == [50.8, 51.2, 67.6, 56.4]


def test_ocr_retries_alternative_preprocessing_and_reports_low_scores(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    response_json = "{'pages':[{'page_number':1,'elements':[{'text':'uncertain','box':[2,3,44,16],'confidence':0.4}]}]}"
    command = [sys.executable, "-c", f"import json; print(json.dumps({response_json}))"]
    settings = Settings(tesseract_command=command)
    root = Path(__file__).resolve().parents[2]
    payload = (root / "e22-corpus/generated/scan-invoice.pdf").read_bytes()
    with TestClient(create_app(settings=settings, engine=engine,
                               store=LocalStore(tmp_path / "objects", 10_000_000), frontend=tmp_path)) as client:
        response = client.post("/api/ingestions?filename=scan-invoice.pdf&ocr_engine=tesseract",
                               content=payload, headers={"content-type": "application/pdf"})
        assert response.status_code == 201, response.text
        result = client.get(f"/api/ingestions/{response.json()['id']}/result").json()["page_model"]
        recovery = result["processing"]["ocr"]["recovery"]
        assert [attempt["status"] for attempt in recovery["attempts"]] == [
            "completed", "completed", "completed"]
        assert recovery["low_confidence_regions"][0]["confidence"] == 0.4


def test_mixed_page_duplicate_ocr_does_not_replace_native_text(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    text = "Native text that should be preserved"
    response_json = {"pages": [{"page_number": 1, "elements": [
        {"text": text, "box": [150, 125, 750, 200], "confidence": 0.9}]}]}
    command = [sys.executable, "-c", f"import json; print(json.dumps({response_json!r}))"]
    settings = Settings(tesseract_command=command)
    with TestClient(create_app(settings=settings, engine=engine,
                               store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        response = client.post("/api/ingestions?filename=mixed.pdf&ocr_engine=tesseract&ocr_mode=force",
                               content=_pdf_with_full_page_image(text),
                               headers={"content-type": "application/pdf"})
        assert response.status_code == 201, response.text
        page_model = client.get(f"/api/ingestions/{response.json()['id']}/result").json()["page_model"]
        assert page_model["processing"]["page_routes"] == ["mixed"]
        elements = page_model["pages"][0]["elements"]
        assert [element["id"] for element in elements if element["type"] == "text"] == ["p1-text-1"]
        observations = page_model["physical_content"]["pages"][0]["ocr_observations"]
        assert observations[0]["reconciliation"] == "duplicate_candidate"


def test_simple_digital_text_exposes_bounded_layout_roles_and_order(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    payload = _pdf_pages("# REPORT\n\n- first item\n\nName | Quantity | Total\n\nWidget | 2 | 10.00")
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        response = client.post("/api/ingestions?filename=layout.pdf", content=payload,
                               headers={"content-type": "application/pdf"})
        assert response.status_code == 201, response.text
        page = client.get(f"/api/ingestions/{response.json()['id']}/result").json()["page_model"]["pages"][0]
        assert [element["role"] for element in page["elements"]] == [
            "heading", "list_item", "table_row", "table_row"]
        assert page["layout"] == {
            "reading_order": ["p1-text-1", "p1-text-2", "p1-text-3", "p1-text-4"],
            "headings": ["p1-text-1"], "lists": ["p1-text-2"],
            "tables": [{"row_ids": ["p1-text-3", "p1-text-4"]}],
        }


def test_ingestion_rejects_bad_signature_and_size(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with TestClient(create_app(settings=Settings(max_object_bytes=4), engine=engine,
                               store=LocalStore(tmp_path / "objects", 4), frontend=tmp_path)) as client:
        assert client.post("/api/ingestions?filename=x.pdf", content=b"bad",
                           headers={"content-type": "application/pdf"}).status_code == 415
        assert client.post("/api/ingestions?filename=x.png", content=b"\x89PNG\r\n\x1a\n123",
                           headers={"content-type": "image/png"}).status_code == 413


def test_ingestion_rejects_pdf_active_content_before_storage(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    store = LocalStore(tmp_path / "objects", 10_000)
    with TestClient(create_app(engine=engine, store=store, frontend=tmp_path)) as client:
        response = client.post("/api/ingestions?filename=active.pdf",
                               content=b"%PDF-1.7\n<< /OpenAction 1 0 R >>",
                               headers={"content-type": "application/pdf"})
        assert response.status_code == 415
        assert response.json()["detail"] == "PDF contains unsupported active content"
        assert not list((tmp_path / "objects").rglob("*"))


def test_ingestion_accepts_valid_pdf_without_active_content(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    store = LocalStore(tmp_path / "objects", 10_000)
    with TestClient(create_app(engine=engine, store=store, frontend=tmp_path)) as client:
        response = client.post("/api/ingestions?filename=form.pdf",
                               content=_pdf_pages(None),
                               headers={"content-type": "application/pdf"})
        assert response.status_code == 201, response.text
        assert store.get(f"ingestions/{response.json()['id']}/form.pdf").startswith(b"%PDF-")


def test_image_page_model_contains_dimensions_and_bounded_source_box(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    payload = _png_header(640, 480)
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        uploaded = client.post("/api/ingestions?filename=scan.png&ocr_language=tha&ocr_engine=paddleocr", content=payload,
                               headers={"content-type": "image/png"})
        assert uploaded.status_code == 201, uploaded.text
        assert uploaded.json()["processing"]["ocr"] == {"engine": "paddleocr", "language": "tha",
                                                         "status": "unavailable",
                                                         "reason": "configured OCR engine is not installed"}
        result = client.get(f"/api/ingestions/{uploaded.json()['id']}/result").json()
        page = result["page_model"]["pages"][0]
        assert page["width"] == 640 and page["height"] == 480
        assert page["elements"][0]["box"] == [0, 0, 640, 480]
        assert "element:image-1 page:1 box:0,0,640,480" in result["markdown"]


def test_configured_ocr_populates_source_provenance(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    command = [sys.executable, "-c", "import json; print(json.dumps({'pages':[{'page_number':1,'elements':[{'text':'Invoice','box':[2,3,44,16],'confidence':0.88}]}]}))"]
    settings = Settings(ocr_command=command)
    with TestClient(create_app(settings=settings, engine=engine,
                               store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        uploaded = client.post("/api/ingestions?filename=scan.png&ocr_language=eng&ocr_engine=paddleocr",
                               content=_png_header(640, 480), headers={"content-type": "image/png"})
        assert uploaded.status_code == 201, uploaded.text
        assert uploaded.json()["processing"]["ocr"]["status"] == "completed"
        page = client.get(f"/api/ingestions/{uploaded.json()['id']}/result").json()["page_model"]["pages"][0]
        assert page["elements"][0]["text"] == "Invoice"
        assert page["elements"][0]["box"] == [2.0, 3.0, 44.0, 16.0]


def test_digital_ingestion_skips_ocr_and_invalid_language_is_rejected(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        digital = client.post("/api/ingestions?filename=text.pdf&ocr_language=de", content=_pdf_pages("text"),
                              headers={"content-type": "application/pdf"})
        assert digital.status_code == 201
        assert digital.json()["processing"]["ocr"]["status"] == "skipped"
        invalid = client.post("/api/ingestions?filename=scan.png&ocr_language=not_a_language!", content=_png_header(1, 1),
                              headers={"content-type": "image/png"})
        assert invalid.status_code == 422


def test_ingestion_rejects_raster_over_pixel_limit_before_storage(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    payload = _png_header(11, 10)
    with TestClient(create_app(settings=Settings(max_image_pixels=100), engine=engine,
                               store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        response = client.post("/api/ingestions?filename=large-scan.png", content=payload,
                               headers={"content-type": "image/png"})
        assert response.status_code == 413
        assert response.json()["detail"] == "image exceeds the configured pixel limit"
        assert not list((tmp_path / "objects").rglob("*"))


def test_ingestion_rejects_documents_over_page_limit(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    payload = _pdf_pages(None, None)
    with TestClient(create_app(settings=Settings(max_pages_per_document=1), engine=engine,
                               store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        response = client.post("/api/ingestions?filename=long.pdf", content=payload,
                               headers={"content-type": "application/pdf"})
        assert response.status_code == 413
        assert response.json()["detail"]["code"] == "page_limit_exceeded"


def test_local_extraction_reports_bounded_multi_page_progress(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    payload = _pdf_pages("Invoice Number: INV-42\nTotal: $42.00", None)
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        uploaded = client.post("/api/ingestions?filename=multi.pdf", content=payload,
                               headers={"content-type": "application/pdf"})
        assert uploaded.status_code == 201, uploaded.text
        document_id = uploaded.json()["id"]
        assert uploaded.json()["pages_total"] == 2
        result = client.post(f"/api/ingestions/{document_id}/extract", json={"schema_id": "invoice"})
        assert result.status_code == 200, result.text
        progress = client.get(f"/api/ingestions/{document_id}").json()
        assert progress["status"] == "processed"
        assert progress["pages_processed"] == progress["pages_total"] == 2
        assert result.json()["fields"]["invoice_number"]["normalized_value"] == "INV-42"


def test_async_extraction_job_persists_result_and_progress(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    settings = Settings(job_worker_enabled=False)
    payload = _pdf_pages("Invoice Number: INV-99", None)
    with TestClient(create_app(settings=settings, engine=engine,
                               store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        uploaded = client.post("/api/ingestions?filename=async.pdf", content=payload,
                               headers={"content-type": "application/pdf"})
        document_id = uploaded.json()["id"]
        queued = client.post(f"/api/ingestions/{document_id}/extract",
                             json={"schema_id": "invoice", "async": True})
        assert queued.status_code == 202, queued.text
        job_id = queued.json()["id"]
        assert client.get(f"/api/ingestions/{document_id}").json()["status"] == "running"
        done = client.post(f"/api/jobs/{job_id}/run", json={"worker_id": "async-test"})
        assert done.status_code == 200, done.text
        result = done.json()["result"]
        assert result["result_id"] and result["page_model"]["document_id"] == document_id
        progress = client.get(f"/api/ingestions/{document_id}").json()
        assert progress["status"] == "processed"
        assert progress["pages_processed"] == progress["pages_total"] == 2
        persisted = client.get(f"/api/extractions/{result['result_id']}")
        assert persisted.status_code == 200
        assert persisted.json()["revision"] == 1


def test_ingestion_classifies_hexadecimal_pdf_text_as_digital(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    payload = _pdf_pages("Hello")
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        response = client.post("/api/ingestions?filename=hex-text.pdf", content=payload,
                               headers={"content-type": "application/pdf"})
        assert response.status_code == 201, response.text
        assert response.json()["route"] == "digital"
        result = client.get(f"/api/ingestions/{response.json()['id']}/result")
        assert result.status_code == 200
        assert result.json()["page_model"]["pages"][0]["elements"][0]["text"] == "Hello"


def test_ingestion_classifies_bounded_flate_pdf_text_as_digital(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    payload = _pdf_pages("Compressed hello")
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        response = client.post("/api/ingestions?filename=compressed.pdf", content=payload,
                               headers={"content-type": "application/pdf"})
        assert response.status_code == 201, response.text
        assert response.json()["route"] == "digital"
        result = client.get(f"/api/ingestions/{response.json()['id']}/result").json()
        assert result["page_model"]["pages"][0]["elements"][0]["text"] == "Compressed hello"


def test_oversized_flate_stream_is_not_inflated_for_routing():
    content = zlib.compress(b"A" * 4_000_001)
    payload = b"%PDF-1.7\n<< /Length " + str(len(content)).encode() + b" /Filter /FlateDecode >>\nstream\n" + content + b"\nendstream"
    assert _pdf_sources(payload) == [payload]


def test_configured_scanner_rejects_before_ingestion_storage(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    settings = Settings(virus_scan_command=[sys.executable, "-c", "raise SystemExit(3)"])
    with TestClient(create_app(settings=settings, engine=engine,
                               store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        response = client.post("/api/ingestions?filename=blocked.pdf", content=_pdf_pages(None),
                               headers={"content-type": "application/pdf"})
        assert response.status_code == 422
        assert response.json()["detail"] == "upload rejected by virus scanner"
        assert not list((tmp_path / "objects").rglob("*"))
