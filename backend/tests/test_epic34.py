from io import BytesIO
from zipfile import ZipFile

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.exports import extraction_xlsx
from app.main import STARTER_CATALOG, create_app
from app.models import Base
from app.rendering import render_definition
from app.storage import LocalStore


def test_multilingual_render_is_escaped_and_reports_scripts():
    result = render_definition({"locale": "en", "blocks": [{"type": "text", "text":
        "Hello {{person.name}} العربية हिन्दी ไทย 中文 한국어 <unsafe>"}]},
        {"person": {"name": "Ada"}})
    assert "&lt;unsafe&gt;" in result["artifact"]
    assert "{{person.name}}" not in result["artifact"]
    assert {"latin", "arabic", "devanagari", "thai", "cjk", "korean"}.issubset(result["scripts"])
    assert result["missing_glyphs"] == []


def test_openapi_explorer_contract_is_generated_and_has_core_paths(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    frontend = tmp_path / "dist"
    frontend.mkdir()
    (frontend / "index.html").write_text("ok", encoding="utf-8")
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=frontend)) as client:
        explorer = client.get("/docs")
        spec = client.get("/openapi.json")
        assert explorer.status_code == 200
        assert spec.status_code == 200
        paths = spec.json()["paths"]
        assert "/api/templates" in paths
        assert "/api/ingestions" in paths
        assert "/api/jobs/{job_id}" in paths
        assert "/api/extractions/{result_id}/export.csv" in paths
        assert "/api/extractions/{result_id}/export.xlsx" in paths
        engines = client.get("/api/extraction-engines")
        assert engines.status_code == 200
        assert engines.json()["contract"] == "extraction-engine-v1"
        assert any(item["id"] == "local-label-extractor" and item["available"] for item in engines.json()["items"])


def test_ui_action_api_matrix_is_present_in_generated_openapi(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    frontend = tmp_path / "dist"
    frontend.mkdir()
    (frontend / "index.html").write_text("ok", encoding="utf-8")
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=frontend)) as client:
        paths = client.get("/openapi.json").json()["paths"]
        action_matrix = {
            "/api/templates": {"get", "post"},
            "/api/templates/{template_id}": {"get"},
            "/api/templates/{template_id}/versions": {"post"},
            "/api/templates/{template_id}/render": {"post"},
            "/api/starters": {"get"},
            "/api/assets": {"post"},
            "/api/extraction-schemas": {"get"},
            "/api/extraction-schemas/{schema_id}": {"get"},
            "/api/extraction-schemas/validate": {"post"},
            "/api/jobs/{job_id}": {"get"},
            "/api/ingestions": {"post"},
            "/api/ingestions/{document_id}": {"get"},
            "/api/ingestions/{document_id}/result": {"get"},
            "/api/ingestions/{document_id}/source": {"get"},
            "/api/ingestions/{document_id}/extract": {"post"},
            "/api/extractions/{result_id}": {"get"},
            "/api/extractions/{result_id}/fields": {"post"},
            "/api/extractions/{result_id}/fields/{field_name}": {"patch"},
            "/api/extractions/{result_id}/undo": {"post"},
            "/api/extractions/{result_id}/webhook": {"post"},
            "/api/extractions/{result_id}/review": {"post"},
            "/api/templates/{template_id}/render-approved": {"post"},
            "/api/word/merge": {"post"},
    "/api/word/convert": {"post"}, "/api/templates/{template_id}/render-pdf": {"post"},
        }
        for route, methods in action_matrix.items():
            assert route in paths
            assert methods <= set(paths[route])


def test_multilingual_starter_catalog_is_launchable_and_renderable(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    frontend = tmp_path / "dist"
    frontend.mkdir()
    (frontend / "index.html").write_text("ok", encoding="utf-8")
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=frontend)) as client:
        expected_scripts = {"ar": "arabic", "zh": "cjk", "ja": "cjk", "hi": "devanagari",
                            "th": "thai", "en": "latin", "de": "latin", "fr": "latin"}
        catalog = client.get("/api/starters")
        assert catalog.status_code == 200
        items = catalog.json()["items"]
        assert {"letter", "invoice", "certificate", "receipt"} <= {item["id"] for item in items}
        assert {item["id"] for item in items} == set(STARTER_CATALOG)
        multilingual = {"letter", "invoice", "certificate", "receipt"}
        assert all(len(item["languages"]) >= 3 for item in items if item["id"] in multilingual)
        for item in items:
            assert set(item["languages"]) == set(item["definitions"])
            for language, definition in item["definitions"].items():
                assert definition["locale"] == language and definition["blocks"]
                created = client.post("/api/templates", json={"name": definition["name"], "definition": definition})
                assert created.status_code == 201, created.text
                rendered = client.post(f"/api/templates/{created.json()['id']}/render", json={"draft": True,
                                                                                              "data": definition["sample_data"],
                                                                                              "locale": language})
                assert rendered.status_code == 200, rendered.text
                assert rendered.json()["locale"] == language
                assert expected_scripts[language] in rendered.json()["scripts"]
                assert rendered.json()["missing_translations"] == []


def test_extraction_xlsx_is_a_valid_offline_workbook_with_provenance_columns():
    workbook = extraction_xlsx({"fields": {"total": {
        "original_value": "12,50 €", "normalized_value": 12.5, "confidence": 0.91,
        "review_status": "new", "source": {"page_number": 1, "box": [1, 2, 3, 4]},
        "validation": [],
    }}}, "approved")
    with ZipFile(BytesIO(workbook)) as bundle:
        assert {"[Content_Types].xml", "xl/workbook.xml", "xl/worksheets/sheet1.xml"}.issubset(bundle.namelist())
        sheet = bundle.read("xl/worksheets/sheet1.xml").decode("utf-8")
        assert "normalized_value" in sheet and "12,50 €" in sheet and "approved" in sheet


def test_template_governance_lifecycle_and_bundle(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    frontend = tmp_path / "dist"
    frontend.mkdir()
    (frontend / "index.html").write_text("ok", encoding="utf-8")
    store = LocalStore(tmp_path / "objects", 1_000_000)
    with TestClient(create_app(engine=engine, store=store, frontend=frontend)) as client:
        created = client.post("/api/templates", json={
            "name": "Invoice", "folder": "Finance", "tags": ["finance"],
            "definition": {"name": "Invoice", "blocks": [{"type": "text", "text": "Hi {{customer.name}}"}]},
        })
        assert created.status_code == 201
        template_id = created.json()["id"]
        listed = client.get("/api/templates", params={"tag": "finance"})
        assert listed.status_code == 200, listed.text
        assert listed.json()["items"][0]["id"] == template_id
        version = client.post(f"/api/templates/{template_id}/versions", json={
            "definition": {"name": "Invoice", "blocks": [{"type": "text", "text": "Hello {{customer.name}}"}]},
            "change_summary": "Greeting",
        }).json()
        assert client.post(f"/api/templates/{template_id}/publish/{version['id']}").status_code == 200
        rendered = client.post(f"/api/templates/{template_id}/render", json={
            "data": {"customer": {"name": "Sam"}}, "locale": "en",
        })
        assert rendered.status_code == 200 and "Hello Sam" in rendered.json()["artifact"]
        assert client.get(f"/api/templates/{template_id}/schema").json()["fields"] == ["customer.name"]
        bundle = client.get(f"/api/templates/{template_id}/export")
        assert bundle.status_code == 200 and bundle.headers["content-type"] == "application/zip"
        duplicate = client.post("/api/templates/import", content=bundle.content,
                                headers={"content-type": "application/zip"})
        assert duplicate.status_code == 201
        history = client.get(f"/api/templates/{template_id}/versions").json()["items"]
        assert len(history) == 2


def test_extraction_webhook_requires_allowlist_and_signs_payload(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    captured = {}

    class FakeResponse:
        status = 202
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("app.main.urllib.request.urlopen", fake_urlopen)
    with TestClient(create_app(settings=Settings(webhook_allowed_hosts=["hooks.example.test"],
                                                 webhook_timeout_seconds=3),
                              engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        uploaded = client.post("/api/ingestions?filename=hook.png", content=b"\x89PNG\r\n\x1a\n",
                               headers={"content-type": "image/png"}).json()
        result = client.post(f"/api/ingestions/{uploaded['id']}/extract", json={"schema_id": "invoice"}).json()
        denied = client.post(f"/api/extractions/{result['result_id']}/webhook",
                             json={"url": "https://not-allowed.example.test/hook"})
        assert denied.status_code == 403
        delivered = client.post(f"/api/extractions/{result['result_id']}/webhook",
                                json={"url": "https://hooks.example.test/hook", "secret": "secret"})
        assert delivered.status_code == 200 and delivered.json()["status_code"] == 202
        assert captured["timeout"] == 3
        assert captured["request"].get_header("X-docplatform-signature").startswith("sha256=")
        body = __import__("json").loads(captured["request"].data)
        field = body["result"]["fields"]["invoice_number"]
        assert field["confidence"] is not None and field["review_status"]
