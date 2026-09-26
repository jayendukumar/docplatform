"""One TOML file plus explicit environment overrides; never echo secret inputs."""
import json
import os
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, model_validator

ROOT = Path(__file__).resolve().parents[2]


class ConfigurationError(RuntimeError):
    pass


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    app_name: str = "Document Platform"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: Literal["critical", "error", "warning", "info"] = "info"
    db_host: str = "localhost"
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_name: str = "docplatform"
    db_user: str = "docplatform"
    db_password: SecretStr = Field(default=SecretStr("docplatform-local"), repr=False, min_length=1)
    db_connect_timeout_seconds: int = Field(default=5, ge=1, le=60)
    storage_backend: Literal["local", "s3"] = "local"
    local_storage_path: Path = ROOT / "data/objects"
    s3_bucket: str | None = None
    s3_endpoint_url: SecretStr | None = Field(default=None, repr=False)
    s3_region: str = "us-east-1"
    s3_prefix: str = "docplatform"
    s3_addressing_style: Literal["path", "virtual", "auto"] = "path"
    s3_access_key_id: SecretStr | None = Field(default=None, repr=False)
    s3_secret_access_key: SecretStr | None = Field(default=None, repr=False)
    s3_session_token: SecretStr | None = Field(default=None, repr=False)
    s3_timeout_seconds: int = Field(default=5, ge=1, le=60)
    s3_max_attempts: int = Field(default=2, ge=1, le=5)
    max_object_bytes: int = Field(default=10485760, ge=1, le=1073741824)
    max_image_pixels: int = Field(default=100_000_000, ge=1, le=10_000_000_000)
    max_pages_per_document: int = Field(default=100, ge=1, le=10000)
    job_timeout_seconds: int = Field(default=30, ge=1, le=3600)
    sync_render_max_blocks: int = Field(default=100, ge=1, le=100000)
    job_cpu_seconds: int = Field(default=20, ge=1, le=3600)
    job_memory_bytes: int = Field(default=536870912, ge=16 * 1024 * 1024, le=8 * 1024 * 1024 * 1024)
    job_max_output_bytes: int = Field(default=5242880, ge=1024, le=1073741824)
    job_worker_enabled: bool = False
    job_worker_poll_seconds: float = Field(default=0.5, gt=0.05, le=60)
    job_worker_render_count: int = Field(default=1, ge=0, le=32)
    job_worker_extraction_count: int = Field(default=1, ge=0, le=32)
    secure_cookies: bool = False
    virus_scan_command: list[str] = Field(default_factory=list)
    virus_scan_timeout_seconds: int = Field(default=15, ge=1, le=300)
    webhook_allowed_hosts: list[str] = Field(default_factory=list)
    image_allowed_hosts: list[str] = Field(default_factory=list)
    webhook_timeout_seconds: int = Field(default=5, ge=1, le=60)
    confidence_calibration_path: Path | None = None
    word_converter_command: list[str] = Field(default_factory=list)
    word_converter_timeout_seconds: int = Field(default=60, ge=1, le=3600)
    pdf_renderer_command: list[str] = Field(default_factory=list)
    pdf_renderer: Literal["chromium", "prince"] = "chromium"
    chromium_renderer_command: list[str] = Field(default_factory=list)
    prince_renderer_command: list[str] = Field(default_factory=list)
    prince_license_file: Path | None = None
    pdf_renderer_timeout_seconds: int = Field(default=60, ge=1, le=3600)
    ocr_command: list[str] = Field(default_factory=list)
    ocr_timeout_seconds: int = Field(default=120, ge=1, le=3600)
    seed_sample: bool = True
    template_publish_requires_approval: bool = False

    @model_validator(mode="after")
    def validate_s3(self):
        if self.storage_backend == "s3" and not self.s3_bucket:
            raise ValueError("s3_bucket is required for S3 storage")
        if bool(self.s3_access_key_id) != bool(self.s3_secret_access_key):
            raise ValueError("S3 access key and secret must be configured together")
        if self.s3_session_token and not self.s3_access_key_id:
            raise ValueError("S3 session token requires explicit credentials")
        if self.s3_endpoint_url:
            from urllib.parse import urlsplit
            parsed = urlsplit(self.s3_endpoint_url.get_secret_value())
            if parsed.scheme not in ("http", "https") or not parsed.hostname:
                raise ValueError("S3 endpoint must be an HTTP(S) URL")
            if parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError("S3 endpoint cannot contain credentials, query or fragment")
        if self.s3_prefix and any(p in ("", ".", "..") for p in self.s3_prefix.split("/")):
            raise ValueError("S3 prefix must contain nonempty safe path segments")
        return self


def load_settings() -> Settings:
    explicit = os.environ.get("DOCPLATFORM_CONFIG_FILE")
    path = Path(explicit) if explicit else ROOT / "config.toml"
    try:
        if explicit and not path.is_file():
            raise ConfigurationError("Configured TOML file is missing")
        values = tomllib.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        for name, value in os.environ.items():
            if name.startswith("DOCPLATFORM_") and name != "DOCPLATFORM_CONFIG_FILE":
                field = name.removeprefix("DOCPLATFORM_").lower()
                if field not in Settings.model_fields:
                    raise ConfigurationError("Unknown DOCPLATFORM setting")
                if field in {"virus_scan_command", "word_converter_command", "pdf_renderer_command", "chromium_renderer_command", "prince_renderer_command", "ocr_command"}:
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        raise ConfigurationError("Invalid configuration; check the documented settings") from None
                values[field] = value
        settings = Settings.model_validate(values)
        local = settings.local_storage_path
        updates = {}
        if not local.is_absolute():
            updates["local_storage_path"] = (path.parent / local).resolve()
        calibration_path = settings.confidence_calibration_path
        if calibration_path is not None and not calibration_path.is_absolute():
            updates["confidence_calibration_path"] = (path.parent / calibration_path).resolve()
        license_path = settings.prince_license_file
        if license_path is not None and not license_path.is_absolute():
            updates["prince_license_file"] = (path.parent / license_path).resolve()
        if updates:
            settings = settings.model_copy(update=updates)
        return settings
    except ConfigurationError:
        raise
    except (OSError, ValueError, ValidationError):
        # TOML/parser/validation exceptions can include the original secret-bearing input.
        raise ConfigurationError("Invalid configuration; check the documented settings") from None
