from contextlib import asynccontextmanager
import json
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import and_, func, select

from app.config import load_settings
from app.database import check_database, create_database
from app.migrations import expected_revision
from app.models import Template, TemplateVersion
from app.rendering import render_definition
from app.template_logic import TemplateDataError
from app.storage import create_store

FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def create_app(settings=None, engine=None, store=None, frontend=FRONTEND):
    settings = settings or load_settings()
    owns_engine = engine is None
    engine = engine or create_database(settings)
    store = store or create_store(settings)
    revision = expected_revision()

    @asynccontextmanager
    async def lifespan(app):
        yield
        if owns_engine:
            engine.dispose()

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    def version_payload(row):
        return {"id": row["id"], "template_id": row["template_id"], "version": row["version"],
                "status": row["status"], "change_summary": row["change_summary"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None}

    def template_definition(connection, template_id, version_id=None, include_draft=False):
        template = connection.execute(select(Template.id, Template.name, Template.object_key,
                                             Template.published_version_id, Template.tags_json,
                                             Template.folder).where(Template.id == template_id)).mappings().one_or_none()
        if template is None:
            raise HTTPException(status_code=404, detail="Template not found")
        if version_id:
            version = connection.execute(select(TemplateVersion.id, TemplateVersion.template_id,
                                                TemplateVersion.version, TemplateVersion.status,
                                                TemplateVersion.change_summary, TemplateVersion.definition_json,
                                                TemplateVersion.created_at).where(and_(
                TemplateVersion.id == version_id, TemplateVersion.template_id == template_id))).mappings().one_or_none()
            if version is None:
                raise HTTPException(status_code=404, detail="Version not found")
        elif include_draft:
            version = connection.execute(select(TemplateVersion.id, TemplateVersion.template_id,
                                                TemplateVersion.version, TemplateVersion.status,
                                                TemplateVersion.change_summary, TemplateVersion.definition_json,
                                                TemplateVersion.created_at).where(
                TemplateVersion.template_id == template_id).order_by(TemplateVersion.version.desc())).mappings().first()
        else:
            version = connection.execute(select(TemplateVersion.id, TemplateVersion.template_id,
                                                TemplateVersion.version, TemplateVersion.status,
                                                TemplateVersion.change_summary, TemplateVersion.definition_json,
                                                TemplateVersion.created_at).where(
                TemplateVersion.id == template["published_version_id"])).mappings().one_or_none()
        if version is None:
            # Foundation rows predate governance; retain their object as a safe read path.
            return template, None, json.loads(store.get(template["object_key"]))
        definition = json.loads(version["definition_json"])
        if not definition.get("name") and template["object_key"]:
            try:
                definition = json.loads(store.get(template["object_key"]))
            except Exception:
                pass
        return template, version, definition

    @app.middleware("http")
    async def contain_errors(request, call_next):
        try:
            return await call_next(request)
        except Exception:
            # Do not log SQL, driver, S3 errors or request bodies: they can contain secrets.
            return JSONResponse({"detail": "Service unavailable; check service readiness"}, status_code=503)

    @app.get("/health/live", tags=["health"])
    def live():
        return {"status": "alive"}

    @app.get("/health/ready", tags=["health"])
    def ready():
        dependencies = {}
        try:
            check_database(engine, revision)
            dependencies["database"] = "ready"
        except Exception:
            dependencies["database"] = "unavailable"
        try:
            store.check()
            dependencies["storage"] = "ready"
        except Exception:
            dependencies["storage"] = "unavailable"
        dependencies["frontend"] = "ready" if (frontend / "index.html").is_file() else "unavailable"
        healthy = all(value == "ready" for value in dependencies.values())
        return JSONResponse({"status": "ready" if healthy else "not_ready", "dependencies": dependencies},
                            status_code=200 if healthy else 503)

    @app.get("/api/templates", tags=["templates"])
    def templates(q: str | None = None, folder: str | None = None, tag: str | None = None):
        with engine.connect() as connection:
            rows = connection.execute(select(Template.id, Template.name, Template.schema_version,
                                             Template.folder, Template.tags_json,
                                             Template.published_version_id).order_by(Template.name)).mappings().all()
            items = []
            for row in rows:
                tags = json.loads(row["tags_json"] or "[]")
                if folder is not None and row["folder"] != folder:
                    continue
                if tag is not None and tag not in tags:
                    continue
                searchable = f"{row['name']} {row['folder']} {' '.join(tags)}".lower()
                if q and q.lower() not in searchable:
                    continue
                published = connection.execute(select(TemplateVersion.version).where(
                    TemplateVersion.id == row["published_version_id"])).scalar_one_or_none()
                items.append({"id": row["id"], "name": row["name"], "schema_version": row["schema_version"],
                              "folder": row["folder"], "tags": tags,
                              "published_version": published,
                              "published_version_id": row["published_version_id"]})
            return {"items": items}

    @app.get("/api/templates/{template_id}", tags=["templates"])
    def template(template_id: str, version: str | None = None, draft: bool = False):
        with engine.connect() as connection:
            _, version_row, definition = template_definition(connection, template_id, version, draft)
            definition = dict(definition)
            definition["version"] = version_row["version"] if version_row else 1
            definition["version_id"] = version_row["id"] if version_row else None
            definition["status"] = version_row["status"] if version_row else "published"
            return definition

    @app.post("/api/templates", status_code=201, tags=["templates"])
    def create_template(payload: dict):
        definition = payload.get("definition") or payload
        name = str(payload.get("name") or definition.get("name") or "Untitled template").strip()
        if not name or len(name) > 200:
            raise HTTPException(status_code=422, detail="Template name is required")
        template_id = str(payload.get("id") or uuid4().hex)
        version_id = f"{template_id}-v1"
        folder = str(payload.get("folder", ""))[:200]
        tags = sorted({str(tag) for tag in payload.get("tags", [])})
        definition = dict(definition); definition["name"] = name; definition.setdefault("schema_version", 1)
        encoded = json.dumps(definition, ensure_ascii=False, sort_keys=True).encode("utf-8")
        key = f"templates/{template_id}/v1.json"
        store.put(key, encoded)
        with engine.begin() as connection:
            if connection.execute(select(Template.id).where(Template.id == template_id)).first():
                raise HTTPException(status_code=409, detail="Template id already exists")
            connection.execute(Template.__table__.insert().values(
                id=template_id, name=name, object_key=key, schema_version=1, folder=folder,
                tags_json=json.dumps(tags), published_version_id=None))
            connection.execute(TemplateVersion.__table__.insert().values(
                id=version_id, template_id=template_id, version=1, status="draft",
                change_summary="Initial draft", definition_json=encoded.decode("utf-8")))
        return {"id": template_id, "version_id": version_id, "status": "draft"}

    @app.get("/api/templates/{template_id}/versions", tags=["templates"])
    def versions(template_id: str):
        with engine.connect() as connection:
            if not connection.execute(select(Template.id).where(Template.id == template_id)).first():
                raise HTTPException(status_code=404, detail="Template not found")
            rows = connection.execute(select(TemplateVersion.id, TemplateVersion.template_id,
                                             TemplateVersion.version, TemplateVersion.status,
                                             TemplateVersion.change_summary, TemplateVersion.created_at).where(
                TemplateVersion.template_id == template_id).order_by(TemplateVersion.version.desc())).mappings().all()
            return {"items": [version_payload(row) for row in rows]}

    @app.post("/api/templates/{template_id}/versions", status_code=201, tags=["templates"])
    def create_version(template_id: str, payload: dict):
        definition = payload.get("definition")
        if not isinstance(definition, dict):
            raise HTTPException(status_code=422, detail="definition must be an object")
        with engine.begin() as connection:
            if not connection.execute(select(Template.id).where(Template.id == template_id)).first():
                raise HTTPException(status_code=404, detail="Template not found")
            latest = connection.execute(select(func.max(TemplateVersion.version)).where(
                TemplateVersion.template_id == template_id)).scalar() or 0
            number = latest + 1
            version_id = f"{template_id}-v{number}"
            definition = dict(definition); definition.setdefault("schema_version", 1)
            encoded = json.dumps(definition, ensure_ascii=False, sort_keys=True)
            key = f"templates/{template_id}/v{number}.json"
            store.put(key, encoded.encode("utf-8"))
            connection.execute(TemplateVersion.__table__.insert().values(
                id=version_id, template_id=template_id, version=number, status="draft",
                change_summary=str(payload.get("change_summary", "Updated draft"))[:500], definition_json=encoded))
            connection.execute(Template.__table__.update().where(Template.id == template_id).values(object_key=key))
        return {"id": version_id, "version": number, "status": "draft"}

    @app.post("/api/templates/{template_id}/publish/{version_id}", tags=["templates"])
    def publish(template_id: str, version_id: str):
        with engine.begin() as connection:
            version = connection.execute(select(TemplateVersion.id, TemplateVersion.template_id,
                                                TemplateVersion.version, TemplateVersion.status,
                                                TemplateVersion.change_summary, TemplateVersion.definition_json,
                                                TemplateVersion.created_at).where(and_(
                TemplateVersion.id == version_id, TemplateVersion.template_id == template_id))).mappings().one_or_none()
            if version is None:
                raise HTTPException(status_code=404, detail="Version not found")
            connection.execute(Template.__table__.update().where(Template.id == template_id).values(
                published_version_id=version_id))
            connection.execute(TemplateVersion.__table__.update().where(TemplateVersion.id == version_id).values(
                status="published"))
        return {"template_id": template_id, "published_version_id": version_id}

    @app.post("/api/templates/{template_id}/restore/{version_id}", status_code=201, tags=["templates"])
    def restore(template_id: str, version_id: str):
        with engine.connect() as connection:
            version = connection.execute(select(TemplateVersion.version, TemplateVersion.definition_json).where(and_(
                TemplateVersion.id == version_id, TemplateVersion.template_id == template_id))).mappings().one_or_none()
            if version is None:
                raise HTTPException(status_code=404, detail="Version not found")
            definition = json.loads(version["definition_json"])
        return create_version(template_id, {"definition": definition, "change_summary": f"Restored from v{version['version']}"})

    @app.post("/api/templates/{template_id}/duplicate", status_code=201, tags=["templates"])
    def duplicate(template_id: str, payload: dict | None = None):
        with engine.connect() as connection:
            source, _, definition = template_definition(connection, template_id)
            source_tags = json.loads(source["tags_json"] or "[]")
        body = {"name": (payload or {}).get("name") or f"{source['name']} copy", "folder": source["folder"],
                "tags": source_tags, "definition": definition}
        return create_template(body)

    @app.get("/api/templates/{template_id}/export", tags=["templates"])
    def export_template(template_id: str):
        with engine.connect() as connection:
            template, version, definition = template_definition(connection, template_id)
            manifest = {"format": "docplatform-template", "format_version": 1,
                        "template_id": template_id, "version_id": version["id"] if version else None}
        output = BytesIO()
        with ZipFile(output, "w", ZIP_DEFLATED) as bundle:
            bundle.writestr("manifest.json", json.dumps(manifest, indent=2))
            bundle.writestr("definition.json", json.dumps(definition, ensure_ascii=False, indent=2))
        return Response(output.getvalue(), media_type="application/zip",
                        headers={"Content-Disposition": f'attachment; filename="{template_id}.zip"'})

    @app.post("/api/templates/import", status_code=201, tags=["templates"])
    async def import_template(request: Request):
        raw = await request.body()
        if request.headers.get("content-type", "").split(";", 1)[0] == "application/zip":
            try:
                with ZipFile(BytesIO(raw)) as bundle:
                    names = set(bundle.namelist())
                    if {"manifest.json", "definition.json"} - names:
                        raise ValueError("bundle manifest is incomplete")
                    manifest = json.loads(bundle.read("manifest.json"))
                    if manifest.get("format") != "docplatform-template":
                        raise ValueError("unsupported bundle format")
                    definition = json.loads(bundle.read("definition.json"))
                    payload = {"name": definition.get("name"), "definition": definition}
            except (ValueError, KeyError, json.JSONDecodeError, OSError) as exc:
                raise HTTPException(status_code=422, detail=f"Invalid template bundle: {exc}") from None
        else:
            try:
                payload = json.loads(raw or b"{}")
            except json.JSONDecodeError:
                raise HTTPException(status_code=422, detail="Expected JSON or application/zip") from None
        definition = payload.get("definition")
        if not isinstance(definition, dict):
            raise HTTPException(status_code=422, detail="definition must be an object")
        return create_template({"name": payload.get("name") or definition.get("name"),
                                "tags": payload.get("tags", []), "definition": definition})

    @app.get("/api/starters", tags=["templates"])
    def starters():
        return {"items": [
            {"id": "letter", "name": "Letter", "languages": ["en", "ar", "zh"]},
            {"id": "invoice", "name": "Invoice", "languages": ["en", "de", "ja"]},
            {"id": "certificate", "name": "Certificate", "languages": ["en", "hi", "fr"]},
            {"id": "receipt", "name": "Receipt", "languages": ["en", "th", "zh"]},
        ]}

    @app.get("/api/templates/{template_id}/schema", tags=["templates"])
    def schema(template_id: str):
        with engine.connect() as connection:
            _, _, definition = template_definition(connection, template_id)
        fields = sorted(set(match.group(1) for block in definition.get("blocks", [])
                             for match in __import__("re").finditer(r"\{\{\s*([A-Za-z0-9_.]+)",
                                                                        str(block.get("text", "")))))
        root: dict = {"type": "object", "properties": {}, "additionalProperties": True}
        for path in fields:
            cursor = root["properties"]
            parts = path.split(".")
            for part in parts[:-1]:
                child = cursor.setdefault(part, {"type": "object", "properties": {}})
                cursor = child["properties"]
            cursor.setdefault(parts[-1], {"type": "string"})
        return {"schema": root, "fields": fields}

    @app.post("/api/templates/{template_id}/render", tags=["rendering"])
    def render(template_id: str, payload: dict | None = None):
        payload = payload or {}
        with engine.connect() as connection:
            _, version, definition = template_definition(connection, template_id,
                                                        payload.get("version_id"), bool(payload.get("draft")))
        try:
            result = render_definition(definition, payload.get("data"), payload.get("locale"),
                                       payload.get("missing_policy"))
        except TemplateDataError as exc:
            raise HTTPException(status_code=422, detail={"message": str(exc), "path": exc.path}) from None
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        result.update({"template_id": template_id, "version_id": version["id"] if version else None})
        return result

    @app.get("/", include_in_schema=False)
    def index():
        if not (frontend / "index.html").is_file():
            return JSONResponse({"detail": "Build the frontend before serving the application"}, status_code=503)
        return FileResponse(frontend / "index.html")

    if (frontend / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="assets")
    return app
