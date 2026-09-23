import os
import pytest
from sqlalchemy import text
from app.config import Settings
from app.database import create_database


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    for key in os.environ:
        if key.startswith("DOCPLATFORM_"):
            monkeypatch.delenv(key)
    config = tmp_path / "config.toml"
    config.write_text("", encoding="utf-8")
    monkeypatch.setenv("DOCPLATFORM_CONFIG_FILE", str(config))
    return config


@pytest.fixture
def postgres_engine():
    # No fallback database: integration tests may only target an explicitly supplied test DB.
    if not os.environ.get("TEST_DB_PORT"):
        pytest.skip("Set TEST_DB_PORT for an isolated PostgreSQL test instance")
    settings = Settings(db_host=os.environ.get("TEST_DB_HOST", "127.0.0.1"),
                        db_port=int(os.environ["TEST_DB_PORT"]), db_name="docplatform_test",
                        db_user="docplatform_test", db_password="docplatform-test-only")
    engine = create_database(settings)
    with engine.begin() as connection:
        assert connection.execute(text("SELECT current_database()")).scalar_one() == "docplatform_test"
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    yield engine
    engine.dispose()
