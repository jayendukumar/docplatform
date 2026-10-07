from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.models import Base
from app.storage import LocalStore


def client(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    frontend = tmp_path / "dist"
    frontend.mkdir()
    (frontend / "index.html").write_text("ok", encoding="utf-8")
    return TestClient(create_app(engine=engine, store=LocalStore(tmp_path / "objects", 100_000), frontend=frontend))


def test_setup_login_workspace_ownership_and_paging(tmp_path):
    with client(tmp_path) as api:
        assert api.get("/api/auth/config").json()["setup_required"] is True
        setup = api.post("/api/auth/setup", json={"email": "admin@example.test", "password": "a" * 12})
        assert setup.status_code == 201
        login = api.post("/api/auth/login", json={"email": "admin@example.test", "password": "a" * 12})
        assert login.status_code == 200
        csrf = login.json()["csrf_token"]
        headers = {"x-csrf-token": csrf}
        workspaces = api.get("/api/workspaces")
        assert workspaces.status_code == 200 and workspaces.json()["items"][0]["name"] == "Good docs"
        created = api.post("/api/templates", headers=headers, json={
            "name": "Admin draft", "folder": "My work", "definition": {"name": "Admin draft", "blocks": []},
        })
        assert created.status_code == 201, created.text
        mine = api.get("/api/templates?scope=mine&limit=1")
        assert mine.status_code == 200 and mine.json()["items"][0]["owner_user_id"]
        organization = api.get("/api/templates?scope=organization&limit=1")
        assert organization.status_code == 200 and organization.json()["limit"] == 1
        assert api.get("/api/auth/sso/start").status_code == 501


def test_guest_and_signup_are_restricted(tmp_path):
    with client(tmp_path) as api:
        api.post("/api/auth/setup", json={"email": "admin@example.test", "password": "a" * 12})
        guest = api.post("/api/auth/guest")
        assert guest.status_code == 200 and guest.json()["account_type"] == "guest"
        assert api.get("/api/templates").json()["items"] == []
        assert api.post("/api/templates", json={"name": "blocked", "definition": {"blocks": []}}).status_code == 403
        api.post("/api/auth/logout")
        signup = api.post("/api/auth/signup", json={"email": "new@example.test"})
        assert signup.status_code == 200 and signup.json()["account_type"] == "pending"
