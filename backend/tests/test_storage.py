import boto3
from moto import mock_aws
import pytest
from app.config import Settings
from app.storage import LocalStore, ObjectNotFound, S3Store


@pytest.fixture(params=["local", "s3"])
def store(request, tmp_path):
    if request.param == "local":
        yield LocalStore(tmp_path / "objects", 1024)
    else:
        with mock_aws():
            client = boto3.client("s3", region_name="us-east-1", aws_access_key_id="test", aws_secret_access_key="test")
            client.create_bucket(Bucket="foundation-test")
            yield S3Store(Settings(storage_backend="s3", s3_bucket="foundation-test", max_object_bytes=1024), client)


@pytest.mark.parametrize("namespace", ["templates", "uploads", "outputs"])
def test_roundtrip_and_overwrite(store, namespace):
    key = f"{namespace}/a/document.bin"
    payload = 'hello \u0645\u0631\u062d\u0628\u0627 \u4f60\u597d'.encode("utf-8")
    store.put(key, payload)
    assert store.get(key) == payload
    store.put(key, b"replacement")
    assert store.get(key) == b"replacement"
    store.delete(key)
    store.delete(key)
    with pytest.raises(ObjectNotFound):
        store.get(key)


def test_empty_object_and_health_probe(store):
    store.put("uploads/empty", b"")
    assert store.get("uploads/empty") == b""
    store.check()


@pytest.mark.parametrize("key", ["", "../escape", "/absolute", "a/../../b", "a//b", "a/./b", "a/..", "C:/tmp", "a\\b", "NUL.txt", "a/trailing.", "a%2fb"])
def test_unsafe_keys_are_rejected(store, key):
    for operation in (lambda: store.put(key, b"x"), lambda: store.get(key), lambda: store.delete(key)):
        with pytest.raises(ValueError):
            operation()


def test_oversized_objects_are_rejected_without_overwriting(store):
    store.put("uploads/file", b"original")
    with pytest.raises(ValueError):
        store.put("uploads/file", b"x" * 1025)
    assert store.get("uploads/file") == b"original"


def test_local_symlink_escape_rejected(tmp_path):
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    outside.mkdir()
    store = LocalStore(root, 100)
    try:
        (root / "link").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation requires OS privilege")
    with pytest.raises(ValueError):
        store.put("link/escape", b"x")
    assert not (outside / "escape").exists()
