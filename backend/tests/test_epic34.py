from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.models import Base
from app.rendering import render_definition
from app.storage import LocalStore


def test_multilingual_render_is_escaped_and_reports_scripts():
    result = render_definition({"locale": "en", "blocks": [{"type": "text", "text":
        "Hello {{person.name}} العربية हिन्दी ไทย 中文 <unsafe>"}]},
        {"person": {"name": "Ada"}})
    assert "&lt;unsafe&gt;" in result["artifact"]
    assert "{{person.name}}" not in result["artifact"]
    assert {"latin", "arabic", "devanagari", "thai", "cjk"}.issubset(result["scripts"])
    assert result["missing_glyphs"] == []


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
