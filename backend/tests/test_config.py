import pytest

from app.config import ConfigurationError, Settings, load_settings


def test_environment_overrides_file_and_paths_are_relative(clean_env, monkeypatch):
    clean_env.write_text('port = 8123\nlocal_storage_path = "files"\n', encoding="utf-8")
    monkeypatch.setenv("DOCPLATFORM_PORT", "8456")
    settings = load_settings()
    assert settings.port == 8456
    assert settings.local_storage_path == clean_env.parent / "files"


def test_secrets_hidden_in_representation(clean_env, monkeypatch):
    monkeypatch.setenv("DOCPLATFORM_DB_PASSWORD", "secret-database")
    monkeypatch.setenv("DOCPLATFORM_S3_ACCESS_KEY_ID", "secret-access")
    monkeypatch.setenv("DOCPLATFORM_S3_SECRET_ACCESS_KEY", "secret-s3")
    settings = load_settings()
    assert "secret-" not in repr(settings)
    assert "secret-" not in settings.model_dump_json()


@pytest.mark.parametrize("name,value", [("PORT", "secret-invalid-port"), ("DB_PASSWORD", ""),
    ("STORAGE_BACKEND", "unknown"), ("S3_ENDPOINT_URL", "https://secret-user:secret-password@example.com")])
def test_invalid_settings_do_not_expose_inputs(clean_env, monkeypatch, name, value):
    monkeypatch.setenv(f"DOCPLATFORM_{name}", value)
    with pytest.raises(ConfigurationError) as failure:
        load_settings()
    assert "secret" not in str(failure.value)


def test_malformed_toml_is_sanitized(clean_env):
    clean_env.write_text('db_password = "secret-value', encoding="utf-8")
    with pytest.raises(ConfigurationError) as failure:
        load_settings()
    assert "secret-value" not in str(failure.value)


def test_unknown_configuration_fails(clean_env, monkeypatch):
    monkeypatch.setenv("DOCPLATFORM_STORGE_BACKEND", "s3")
    with pytest.raises(ConfigurationError):
        load_settings()


def test_s3_requires_bucket(clean_env, monkeypatch):
    monkeypatch.setenv("DOCPLATFORM_STORAGE_BACKEND", "s3")
    with pytest.raises(ConfigurationError):
        load_settings()


def test_explicit_missing_config_fails(clean_env, monkeypatch):
    monkeypatch.setenv("DOCPLATFORM_CONFIG_FILE", str(clean_env.parent / "missing.toml"))
    with pytest.raises(ConfigurationError):
        load_settings()


def test_confidence_calibration_path_resolves_beside_config(clean_env):
    clean_env.write_text('confidence_calibration_path = "profiles/calibration.json"\n', encoding="utf-8")
    settings = load_settings()
    assert settings.confidence_calibration_path == clean_env.parent / "profiles" / "calibration.json"
    assert Settings(confidence_calibration_path="profile.json").confidence_calibration_path.name == "profile.json"
