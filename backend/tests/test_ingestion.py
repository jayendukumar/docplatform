import sys
import zlib

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.ingestion import _pdf_sources, detect_page_routes
from app.main import create_app
from app.models import Base
from app.storage import LocalStore


def _png_header(width: int, height: int) -> bytes:
    return (b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" +
            width.to_bytes(4, "big") + height.to_bytes(4, "big") + b"\x08\x02\x00\x00\x00")


def test_ingestion_classifies_and_persists_digital_pdf(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        payload = b"%PDF-1.7\nBT (hello) Tj ET"
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
        assert elements[0]["text"] == "hello" and elements[0]["box"] == [72, 72, 540, 86]
        assert elements[0]["role"] == "text"
        assert result.json()["page_model"]["pages"][0]["layout"]["reading_order"] == ["text-1"]
        assert "element:text-1 page:1 box:72,72,540,86" in result.json()["markdown"]
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


def test_mixed_pdf_page_routes_are_recorded_conservatively():
    payload = (b"%PDF-1.7\n/Type /Page\nBT (digital page) Tj ET\n"
               b"/Type /Page\nq 1 0 0 1 0 0 cm\n")
    assert detect_page_routes(payload, 2, "scan") == ["digital", "scan"]


def test_mixed_pdf_page_routes_are_exposed_in_result_metadata(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    payload = (b"%PDF-1.7\n/Type /Page\nBT (digital page) Tj ET\n"
               b"/Type /Page\nq 1 0 0 1 0 0 cm\n")
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        response = client.post("/api/ingestions?filename=mixed.pdf", content=payload,
                               headers={"content-type": "application/pdf"})
        assert response.status_code == 201, response.text
        result = client.get(f"/api/ingestions/{response.json()['id']}/result").json()
        assert [page["route"] for page in result["page_model"]["pages"]] == ["digital", "scan"]
        assert result["page_model"]["processing"]["page_routes"] == ["digital", "scan"]
        assert result["page_model"]["processing"]["ocr"]["status"] == "unavailable"
        assert result["page_model"]["processing"]["ocr"]["reason"] == "mixed documents require page-aware OCR dispatch"


def test_configured_ocr_dispatches_only_mixed_scan_pages(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    command = [sys.executable, "-c", "import json; print(json.dumps({'pages':[{'page_number':1,'elements':[{'text':'should be ignored','box':[1,1,20,12]}]},{'page_number':2,'elements':[{'text':'scanned page','box':[2,3,44,16]}]}]}))"]
    settings = Settings(ocr_command=command)
    payload = (b"%PDF-1.7\n/Type /Page\nBT (digital page) Tj ET\n"
               b"/Type /Page\nq 1 0 0 1 0 0 cm\n")
    with TestClient(create_app(settings=settings, engine=engine,
                               store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        response = client.post("/api/ingestions?filename=mixed.pdf", content=payload,
                               headers={"content-type": "application/pdf"})
        assert response.status_code == 201, response.text
        result = client.get(f"/api/ingestions/{response.json()['id']}/result").json()
        pages = result["page_model"]["pages"]
        assert pages[0]["elements"][0]["text"] == "digital page"
        assert pages[1]["elements"][0]["text"] == "scanned page"
        assert result["page_model"]["processing"]["ocr"] == {
            "engine": "paddleocr", "language": "eng", "status": "completed",
            "pages": 1, "requested_pages": [2], "adapter": "configured-local-command",
        }


def test_simple_digital_text_exposes_bounded_layout_roles_and_order(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    payload = (b"%PDF-1.7\nBT (# REPORT) Tj (- first item) Tj "
               b"(Name | Quantity | Total) Tj (Widget | 2 | 10.00) Tj ET")
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        response = client.post("/api/ingestions?filename=layout.pdf", content=payload,
                               headers={"content-type": "application/pdf"})
        assert response.status_code == 201, response.text
        page = client.get(f"/api/ingestions/{response.json()['id']}/result").json()["page_model"]["pages"][0]
        assert [element["role"] for element in page["elements"]] == [
            "heading", "list_item", "table_row", "table_row"]
        assert page["layout"] == {
            "reading_order": ["text-1", "text-2", "text-3", "text-4"],
            "headings": ["text-1"], "lists": ["text-2"],
            "tables": [{"row_ids": ["text-3", "text-4"]}],
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
        digital = client.post("/api/ingestions?filename=text.pdf&ocr_language=de", content=b"%PDF-1.7\nBT (text) Tj ET",
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
    payload = b"%PDF-1.7\n/Type /Page\n/Type /Page\n"
    with TestClient(create_app(settings=Settings(max_pages_per_document=1), engine=engine,
                               store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        response = client.post("/api/ingestions?filename=long.pdf", content=payload,
                               headers={"content-type": "application/pdf"})
        assert response.status_code == 413
        assert response.json()["detail"] == "upload exceeds the configured page limit"


def test_local_extraction_reports_bounded_multi_page_progress(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    payload = b"%PDF-1.7\n/Type /Page\n/Type /Page\nBT (Invoice Number: INV-42) Tj (Total: $42.00) Tj ET"
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
    payload = b"%PDF-1.7\n/Type /Page\n/Type /Page\nBT (Invoice Number: INV-99) Tj ET"
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
    payload = b"%PDF-1.7\nBT <48656c6c6f> Tj ET"
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
    content = zlib.compress(b"BT (Compressed hello) Tj ET")
    payload = b"%PDF-1.7\n<< /Length " + str(len(content)).encode() + b" /Filter /FlateDecode >>\nstream\n" + content + b"\nendstream"
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
        response = client.post("/api/ingestions?filename=blocked.pdf", content=b"%PDF-1.7\n",
                               headers={"content-type": "application/pdf"})
        assert response.status_code == 422
        assert response.json()["detail"] == "upload rejected by virus scanner"
        assert not list((tmp_path / "objects").rglob("*"))
