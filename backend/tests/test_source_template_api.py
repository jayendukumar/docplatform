import json

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.models import Base, IngestionDocument, SourceTemplateSession, Template, TemplateVersion
from app.storage import LocalStore


def test_each_acknowledged_source_workflow_gets_a_distinct_session(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 100_000), frontend=tmp_path)) as client:
        assert client.post("/api/auth/setup", json={
            "email": "source-owner@example.test", "password": "correct horse battery"
        }).status_code == 201
        login = client.post("/api/auth/login", json={
            "email": "source-owner@example.test", "password": "correct horse battery"
        })
        csrf = login.json()["csrf_token"]
        headers = {"x-csrf-token": csrf}
        first = client.post("/api/source-template-sessions", headers=headers,
                            json={"disclosure_acknowledged": True})
        second = client.post("/api/source-template-sessions", headers=headers,
                             json={"disclosure_acknowledged": True})

    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    assert first.json()["status"] == second.json()["status"] == "awaiting_source"


def test_source_upload_response_keeps_the_session_id_for_followup_actions(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 100_000), frontend=tmp_path)) as client:
        created = client.post("/api/source-template-sessions", json={"disclosure_acknowledged": True})
        session_id = created.json()["id"]
        uploaded = client.post(
            f"/api/source-template-sessions/{session_id}/source?filename=sample.pdf",
            content=b"%PDF-1.7\nBT (Sample text) Tj ET",
            headers={"content-type": "application/pdf"},
        )

    assert uploaded.status_code == 201, uploaded.text
    assert uploaded.json()["id"] == session_id
    assert uploaded.json()["session_id"] == session_id


def test_comparison_metadata_selects_the_latest_saved_draft_version(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 100_000), frontend=tmp_path)) as client:
        client.post("/api/auth/setup", json={
            "email": "compare-owner@example.test", "password": "correct horse battery"
        })
        login = client.post("/api/auth/login", json={
            "email": "compare-owner@example.test", "password": "correct horse battery"
        })
        owner_id = login.json()["id"]
        with engine.begin() as connection:
            connection.execute(IngestionDocument.__table__.insert().values(
                id="source-1", filename="original.pdf", media_type="application/pdf", size_bytes=10,
                pages_total=2, pages_processed=2, route="digital", status="processed",
                object_key="ingestions/source-1/original.pdf", page_model_json="{}", markdown=""))
            connection.execute(Template.__table__.insert().values(
                id="template-1", name="Source draft", object_key="templates/template-1/v1.json",
                schema_version=1, folder="", tags_json="[]", owner_user_id=owner_id,
                workspace_id="workspace-1", visibility="workspace", updated_by_user_id=owner_id))
            for version in (1, 2):
                connection.execute(TemplateVersion.__table__.insert().values(
                    id=f"template-1-v{version}", template_id="template-1", version=version,
                    status="draft", definition_json=json.dumps({"sample_data": {}})))
            connection.execute(SourceTemplateSession.__table__.insert().values(
                id="source-session-1", document_id="source-1", owner_user_id=owner_id,
                status="draft_generated", disclosure_acknowledged=True, template_id="template-1",
                template_version_id="template-1-v1", revision=3))

        comparison = client.post("/api/source-template-sessions/source-session-1/compare")

    assert comparison.status_code == 200, comparison.text
    assert comparison.json()["source_version_id"] == "template-1-v2"
    assert comparison.json()["source_filename"] == "original.pdf"
    assert comparison.json()["source_media_type"] == "application/pdf"
