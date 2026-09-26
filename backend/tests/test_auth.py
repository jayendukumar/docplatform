from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.config import Settings
from app.models import Base
from app.storage import LocalStore


def test_initial_setup_login_session_and_csrf_boundary(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        setup = client.post("/api/auth/setup", json={"email": "Owner@Example.com", "password": "correct horse battery"})
        assert setup.status_code == 201
        assert client.post("/api/auth/setup", json={"email": "other@example.com", "password": "correct horse battery"}).status_code == 409
        login = client.post("/api/auth/login", json={"email": "owner@example.com", "password": "correct horse battery"})
        assert login.status_code == 200
        csrf = login.json()["csrf_token"]
        assert client.get("/api/auth/me").json()["email"] == "owner@example.com"
        # A protected review mutation requires the session's CSRF token.
        assert client.post("/api/extractions/missing/review", json={"status": "approved"}).status_code == 403
        assert client.post("/api/auth/logout").status_code == 200
        assert client.get("/api/auth/me").status_code == 401
        assert csrf


def test_scoped_api_key_is_shown_once_and_revocable(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        client.post("/api/auth/setup", json={"email": "owner@example.com", "password": "correct horse battery"})
        login = client.post("/api/auth/login", json={"email": "owner@example.com", "password": "correct horse battery"})
        csrf = login.json()["csrf_token"]
        created = client.post("/api/auth/api-keys", json={"name": "reader", "scopes": ["read"]},
                              headers={"x-csrf-token": csrf})
        assert created.status_code == 201, created.text
        key = created.json()["key"]
        assert key.startswith("dp_")
        assert "key" not in client.get("/api/auth/api-keys").text
        assert client.get("/api/templates", headers={"x-api-key": key}).status_code == 200
        upload = client.post("/api/ingestions?filename=key-upload.png", content=b"\x89PNG\r\n\x1a\n",
                             headers={"x-api-key": key, "content-type": "image/png"})
        assert upload.status_code == 201
        assert client.post("/api/jobs", headers={"x-api-key": key}, json={
            "kind": "render", "template_id": "sample-welcome", "data": {}}).status_code == 403
        assert client.post("/api/templates/sample-welcome/render-approved", headers={"x-api-key": key},
                           json={"extraction_id": "missing"}).status_code == 403
        render_key_response = client.post("/api/auth/api-keys", json={"name": "renderer", "scopes": ["render"]},
                                          headers={"x-csrf-token": csrf})
        assert render_key_response.status_code == 201
        render_key = render_key_response.json()["key"]
        assert client.post("/api/jobs", headers={"x-api-key": render_key}, json={
            "kind": "render", "template_id": "sample-welcome", "data": {}}).status_code == 202
        assert client.post("/api/templates/sample-welcome/render-approved", headers={"x-api-key": render_key},
                           json={"extraction_id": "missing"}).status_code == 404
        key_id = created.json()["id"]
        assert client.delete(f"/api/auth/api-keys/{key_id}", headers={"x-csrf-token": csrf}).status_code == 200
        assert client.get("/api/templates", headers={"x-api-key": key}).status_code == 401


def test_api_keys_support_read_render_and_admin_scope_rotation(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        client.post("/api/auth/setup", json={"email": "scopes@example.com", "password": "correct horse battery"})
        csrf = client.post("/api/auth/login", json={"email": "scopes@example.com", "password": "correct horse battery"}).json()["csrf_token"]
        keys = {}
        for scope in ("read", "render", "admin"):
            response = client.post("/api/auth/api-keys", json={"name": scope, "scopes": [scope]},
                                   headers={"x-csrf-token": csrf})
            assert response.status_code == 201
            keys[scope] = response.json()
            assert response.json()["scopes"] == [scope]
            assert response.json()["key"].startswith("dp_")
        assert client.get("/api/templates", headers={"x-api-key": keys["read"]["key"]}).status_code == 200
        assert client.post("/api/jobs", headers={"x-api-key": keys["read"]["key"]},
                           json={"kind": "render", "template_id": "sample-welcome", "data": {}}).status_code == 403
        assert client.post("/api/jobs", headers={"x-api-key": keys["render"]["key"]},
                           json={"kind": "render", "template_id": "sample-welcome", "data": {}}).status_code == 202
        assert client.get("/api/templates", headers={"x-api-key": keys["admin"]["key"]}).status_code == 200
        assert client.delete(f"/api/auth/api-keys/{keys['render']['id']}", headers={"x-csrf-token": csrf}).status_code == 200
        replacement = client.post("/api/auth/api-keys", json={"name": "replacement", "scopes": ["render"]},
                                  headers={"x-csrf-token": csrf})
        assert replacement.status_code == 201
        assert client.get("/api/templates", headers={"x-api-key": keys["render"]["key"]}).status_code == 401


def test_secure_cookie_mode_marks_session_cookie_for_tls_proxy(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with TestClient(create_app(settings=Settings(secure_cookies=True), engine=engine,
                               store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        assert client.post("/api/auth/setup", json={"email": "tls@example.com", "password": "correct horse battery"}).status_code == 201
        login = client.post("/api/auth/login", json={"email": "tls@example.com", "password": "correct horse battery"})
        assert login.status_code == 200
        assert "docplatform_session=" in login.headers["set-cookie"]
        assert "HttpOnly" in login.headers["set-cookie"] and "Secure" in login.headers["set-cookie"]


def test_login_rate_limit_locks_account_after_repeated_failures(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 10_000), frontend=tmp_path)) as client:
        assert client.post("/api/auth/setup", json={"email": "locked@example.com", "password": "correct horse battery"}).status_code == 201
        for _ in range(5):
            assert client.post("/api/auth/login", json={"email": "locked@example.com", "password": "wrong password"}).status_code == 401
        assert client.post("/api/auth/login", json={"email": "locked@example.com", "password": "correct horse battery"}).status_code == 429
