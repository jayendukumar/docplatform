"""Bounded byte-object storage shared by templates, uploads and outputs."""
from abc import ABC, abstractmethod
from pathlib import Path
import os
import re
import tempfile
from uuid import uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config import Settings


class ObjectNotFound(FileNotFoundError):
    pass


class StorageError(RuntimeError):
    pass


def validate_key(key: str) -> str:
    # One portable namespace: reject Windows aliases, traversal and empty segments on every OS.
    if not isinstance(key, str) or len(key) > 512:
        raise ValueError("Invalid object key")
    parts = key.split("/")
    for part in parts:
        if not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*", part) or part.endswith("."):
            raise ValueError("Invalid object key")
        if part.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(10)], *[f"LPT{i}" for i in range(10)]}:
            raise ValueError("Invalid object key")
    return key


class ObjectStore(ABC):
    def __init__(self, max_bytes: int):
        self.max_bytes = max_bytes

    def check_payload(self, data: bytes):
        if not isinstance(data, bytes) or len(data) > self.max_bytes:
            raise ValueError("Object exceeds configured limit or is not bytes")

    @abstractmethod
    def put(self, key: str, data: bytes) -> None: ...

    @abstractmethod
    def get(self, key: str) -> bytes: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    def check(self) -> None:
        key = f"health/{uuid4().hex}.probe"
        try:
            self.put(key, b"ready")
            if self.get(key) != b"ready":
                raise StorageError("Storage probe failed")
        finally:
            self.delete(key)


class LocalStore(ObjectStore):
    def __init__(self, root: Path, max_bytes: int):
        super().__init__(max_bytes)
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, key: str) -> Path:
        candidate = self.root.joinpath(*validate_key(key).split("/"))
        # Reject symlinks/junctions, including ones which point back inside the root.
        cursor = candidate
        while cursor != self.root:
            if cursor.is_symlink() or (hasattr(cursor, "is_junction") and cursor.is_junction()):
                raise ValueError("Symbolic links are not permitted in object storage")
            cursor = cursor.parent
        if not candidate.resolve().is_relative_to(self.root):
            raise ValueError("Object key escapes storage root")
        return candidate

    def put(self, key: str, data: bytes) -> None:
        self.check_payload(data)
        path = self.path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".write-", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def get(self, key: str) -> bytes:
        try:
            with self.path(key).open("rb") as stream:
                data = stream.read(self.max_bytes + 1)
            self.check_payload(data)
            return data
        except FileNotFoundError:
            raise ObjectNotFound("Object not found") from None

    def delete(self, key: str) -> None:
        self.path(key).unlink(missing_ok=True)


class S3Store(ObjectStore):
    def __init__(self, settings: Settings, client=None):
        super().__init__(settings.max_object_bytes)
        self.bucket = settings.s3_bucket
        self.prefix = settings.s3_prefix
        def secret(value):
            return value.get_secret_value() if value else None
        self.client = client or boto3.client(
            "s3", endpoint_url=secret(settings.s3_endpoint_url), region_name=settings.s3_region,
            aws_access_key_id=secret(settings.s3_access_key_id),
            aws_secret_access_key=secret(settings.s3_secret_access_key),
            aws_session_token=secret(settings.s3_session_token),
            config=Config(connect_timeout=settings.s3_timeout_seconds,
                          read_timeout=settings.s3_timeout_seconds,
                          retries={"total_max_attempts": settings.s3_max_attempts, "mode": "standard"},
                          s3={"addressing_style": settings.s3_addressing_style}),
        )

    def key(self, key: str) -> str:
        value = validate_key(key)
        return f"{self.prefix}/{value}" if self.prefix else value

    def put(self, key: str, data: bytes) -> None:
        self.check_payload(data)
        self.client.put_object(Bucket=self.bucket, Key=self.key(key), Body=data)

    def get(self, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=self.key(key))
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("NoSuchKey", "404", "NotFound"):
                raise ObjectNotFound("Object not found") from None
            raise
        body = response["Body"]
        try:
            data = body.read(self.max_bytes + 1)
            self.check_payload(data)
            return data
        finally:
            body.close()

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=self.key(key))


def create_store(settings: Settings) -> ObjectStore:
    if settings.storage_backend == "s3":
        return S3Store(settings)
    return LocalStore(settings.local_storage_path, settings.max_object_bytes)
