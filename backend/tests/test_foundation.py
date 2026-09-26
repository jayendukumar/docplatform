from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

from alembic import command
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import text

from app.bootstrap import seed
from app.config import Settings
from app.main import create_app
from app.migrations import expected_revision, migrate, migration_config
from app.storage import LocalStore


def frontend(tmp_path):
    path = tmp_path / "dist"
    path.mkdir()
    (path / "index.html").write_text("<!doctype html><title>Foundation</title>", encoding="utf-8")
    return path


def test_liveness_does_not_require_dependencies_and_readiness_sanitizes(tmp_path):
    engine = Mock()
    engine.connect.side_effect = RuntimeError("secret-password-database")
    store = Mock()
    store.check.side_effect = RuntimeError("secret-access-key-s3")
    with TestClient(create_app(Settings(), engine, store, frontend(tmp_path))) as client:
        assert client.get("/health/live").json() == {"status": "alive"}
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json()["dependencies"] == {"database": "unavailable", "storage": "unavailable", "frontend": "ready"}
        assert "secret" not in response.text
        assert client.get("/").status_code == 200
        response = client.get("/api/templates")
        assert response.status_code == 503
        assert "secret" not in response.text


@pytest.mark.integration
def test_fresh_install_seed_and_api(postgres_engine, tmp_path):
    migrate(postgres_engine)
    store = LocalStore(tmp_path / "objects", 10000)
    seed(postgres_engine, store)
    seed(postgres_engine, store)
    with TestClient(create_app(Settings(), postgres_engine, store, frontend(tmp_path))) as client:
        assert client.get("/health/ready").status_code == 200
        items = client.get("/api/templates").json()["items"]
        assert len(items) == 1
        assert items[0]["id"] == "sample-welcome"
        sample = client.get("/api/templates/sample-welcome").json()
        assert sample["sample_data"]["recipient"]["name"] == "Alex"
        assert sample["blocks"][2]["text"] == "\u0645\u0631\u062d\u0628\u0627 \u00b7 \u4f60\u597d"
        assert client.get("/api/templates/no-such-template").status_code == 404


@pytest.mark.integration
def test_upgrade_preserves_existing_template(postgres_engine):
    with postgres_engine.begin() as connection:
        config = migration_config()
        config.attributes["connection"] = connection
        command.upgrade(config, "0001_templates")
        connection.execute(text("INSERT INTO templates (id, name, object_key) VALUES ('existing', 'Existing', 'templates/existing.json')"))
    migrate(postgres_engine)
    migrate(postgres_engine)
    with postgres_engine.connect() as connection:
        row = connection.execute(text("SELECT name, schema_version FROM templates WHERE id = 'existing'")).one()
        assert tuple(row) == ("Existing", 1)
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == expected_revision()


@pytest.mark.integration
@pytest.mark.parametrize("source_revision", ["0010_review_events", "0011_correction_snapshots"])
def test_upgrade_from_recent_pre_head_revisions_preserves_templates(postgres_engine, source_revision):
    """Exercise the current migration chain from both recent release boundaries."""
    with postgres_engine.begin() as connection:
        config = migration_config()
        config.attributes["connection"] = connection
        command.upgrade(config, source_revision)
        connection.execute(text(
            "INSERT INTO templates (id, name, object_key, schema_version, folder, tags_json) "
            "VALUES ('compat', 'Compatibility template', 'templates/compat.json', 1, 'legacy', '[\"compat\"]')"
        ))
    migrate(postgres_engine)
    with postgres_engine.connect() as connection:
        row = connection.execute(text("SELECT name, folder, tags_json FROM templates WHERE id = 'compat'")).one()
        assert tuple(row) == ("Compatibility template", "legacy", '["compat"]')
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == expected_revision()


@pytest.mark.integration
def test_concurrent_bootstraps_serialize_migrations(postgres_engine):
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(migrate, postgres_engine) for _ in range(2)]
        for future in futures:
            future.result(timeout=30)
    with postgres_engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == expected_revision()


@pytest.mark.integration
def test_readiness_rejects_unmigrated_database(postgres_engine, tmp_path):
    with TestClient(create_app(Settings(), postgres_engine, LocalStore(tmp_path / "objects", 100), frontend(tmp_path))) as client:
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json()["dependencies"]["database"] == "unavailable"
