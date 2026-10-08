import base64
import binascii
import csv
import hashlib
import hmac
import json
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from io import BytesIO, StringIO
from pathlib import Path
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import and_, func, select

from app.auth import (
    LOCKOUT,
    MAX_LOGIN_FAILURES,
    SESSION_TTL,
    hash_password,
    new_api_key,
    new_session,
    verify_password,
)
from app.capabilities import capability_manifest
from app.calibration import CalibrationProfileError, apply_profile, validate_profile
from app.components import ComponentDefinitionError, ComponentExpansionError, expand_definition, validate_component_definition
from app.config import ConfigurationError, load_settings
from app.database import check_database, create_database
from app.engines import ExtractionEngineError, engine_descriptors, extract_with_engine
from app.exports import extraction_xlsx
from app.extraction import (
    BUNDLED_SAMPLES,
    BUNDLED_SCHEMAS,
    ExtractionSchemaError,
    schema_to_json_schema,
    validate_schema,
)
from app.ingestion import (
    IngestionInputError,
    classify_upload,
    count_pages,
    detect_page_routes,
    image_dimensions,
    markdown_for,
    page_model,
    simple_pdf_text_elements,
)
from app.jobs import claim, claim_next, enqueue
from app.migrations import expected_revision
from app.models import (
    ApiKey,
    ExtractionCorrection,
    ExtractionResultRecord,
    ExtractionReviewEvent,
    IngestionDocument,
    Job,
    Session,
    Template,
    TemplateAlias,
    TemplateVersion,
    ReusableComponent,
    User,
    Organization,
    OrganizationMembership,
    Workspace,
)
from app.security import (
    UploadScanError,
    scan_upload,
    validate_pdf_active_content,
    validate_svg_markup,
)
from app.storage import create_store
from app.template_logic import TemplateDataError, TemplateEvaluationLimitError, generate_sample_data
from app.word_convert import (
    WordConversionError,
    WordConversionUnavailable,
    convert_docx_to_pdf,
    encode_pdf,
)
from app.word_merge import WordMergeError, merge_docx
from app.worker import WorkerExecutionError, run_isolated
from app.renderer_adapter import default_command
from app.pdf_background import PdfBackgroundError, merge_pdf_background
from app.pdf_toc import PdfPageNumberError, PdfTocError, add_toc_page_numbers

FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "dist"


STARTER_CATALOG = {
    "letter": {
        "name": "Letter", "category": "General & Communications",
        "languages": {
            "en": {"title": "Welcome letter", "body": "Welcome to our service."},
            "ar": {"title": "رسالة ترحيب", "body": "مرحباً بكم في خدمتنا."},
            "zh": {"title": "欢迎信", "body": "欢迎使用我们的服务。"},
        },
        "sample_data": {"recipient": {"name": "Alex"}},
        "blocks": [{"type": "text", "text": "Welcome letter", "translation_key": "title"},
                   {"type": "text", "text": "Welcome to our service.", "translation_key": "body"}],
    },
    "invoice": {
        "name": "Invoice", "category": "Finance Operations",
        "languages": {
            "en": {"title": "Invoice", "body": "Thank you for your business."},
            "de": {"title": "Rechnung", "body": "Vielen Dank für Ihren Auftrag."},
            "ja": {"title": "請求書", "body": "ご利用ありがとうございます。"},
        },
        "sample_data": {"invoice_number": "INV-001", "rows": [{"description": "Example item", "amount": 12.5}]},
        "blocks": [{"type": "text", "text": "Invoice", "translation_key": "title"},
                   {"type": "table", "items": "rows", "columns": [
                       {"header": "Description", "path": "description", "format": "text"},
                       {"header": "Amount", "path": "amount", "format": "currency"}]},
                   {"type": "text", "text": "Thank you for your business.", "translation_key": "body"}],
    },
    "certificate": {
        "name": "Certificate", "category": "Human Resources",
        "languages": {
            "en": {"title": "Certificate of completion", "body": "This certificate is presented to {{recipient.name}}."},
            "hi": {"title": "पूर्णता प्रमाणपत्र", "body": "यह प्रमाणपत्र {{recipient.name}} को प्रदान किया जाता है।"},
            "fr": {"title": "Certificat de réussite", "body": "Ce certificat est remis à {{recipient.name}}."},
        },
        "sample_data": {"recipient": {"name": "Alex"}},
        "blocks": [{"type": "text", "text": "Certificate of completion", "translation_key": "title"},
                   {"type": "text", "text": "This certificate is presented to {{recipient.name}}.", "translation_key": "body"}],
    },
    "receipt": {
        "name": "Receipt", "category": "Finance Operations",
        "languages": {
            "en": {"title": "Receipt", "body": "Payment received."},
            "th": {"title": "ใบเสร็จรับเงิน", "body": "ได้รับชำระเงินแล้ว"},
            "zh": {"title": "收据", "body": "已收到付款。"},
        },
        "sample_data": {"rows": [{"description": "Example item", "amount": 12.5}]},
        "blocks": [{"type": "text", "text": "Receipt", "translation_key": "title"},
                   {"type": "table", "items": "rows", "columns": [
                       {"header": "Description", "path": "description", "format": "text"},
                       {"header": "Amount", "path": "amount", "format": "currency"}]},
                   {"type": "text", "text": "Payment received.", "translation_key": "body"}],
    },
}


_CATALOG_PROFILES = {
    "Investment Banking": {
        "primary": ("Transaction", "Project Atlas acquisition"),
        "fields": [("Client", "client_name", "Northstar Holdings"), ("Prepared by", "prepared_by", "Alex Morgan"),
                    ("As of", "as_of", "2026-01-15"), ("Status", "status", "Draft for review")],
        "line_items": [("Enterprise value", "1,250,000,000"), ("Net debt", "210,000,000"), ("Equity value", "1,040,000,000")],
        "notes": "Illustrative figures require transaction-team confirmation before circulation.",
        "summary_label": "Transaction summary", "detail_label": "Key figures",
    },
    "Asset Management": {
        "primary": ("Portfolio", "Northstar Global Equity Fund"),
        "fields": [("Client", "client_name", "Northstar Pension Trust"), ("Portfolio", "portfolio_name", "Global Equity Fund"),
                    ("Valuation date", "as_of", "2026-01-15"), ("Prepared by", "prepared_by", "Investment Team")],
        "line_items": [("Opening value", "98,500,000"), ("Net contributions", "1,250,000"), ("Closing value", "103,240,000")],
        "notes": "Past performance is not indicative of future results.",
        "summary_label": "Portfolio overview", "detail_label": "Performance snapshot",
    },
    "Insurance": {
        "primary": ("Insured", "Acme Manufacturing Ltd."),
        "fields": [("Policy number", "policy_number", "POL-2026-00421"), ("Effective date", "effective_date", "2026-02-01"),
                    ("Expiry date", "expiry_date", "2027-01-31"), ("Underwriter", "prepared_by", "Jordan Lee")],
        "line_items": [("Property cover", "2,000,000"), ("Business interruption", "500,000"), ("Annual premium", "18,750")],
        "notes": "Coverage is subject to the policy wording, endorsements and applicable exclusions.",
        "summary_label": "Policy details", "detail_label": "Coverage schedule",
    },
    "Wealth Management": {
        "primary": ("Client", "Jordan and Taylor Morgan"),
        "fields": [("Review date", "review_date", "2026-01-15"), ("Lead adviser", "prepared_by", "Priya Shah"),
                    ("Risk profile", "risk_profile", "Balanced"), ("Review status", "status", "Ready for discussion")],
        "line_items": [("Investable assets", "2,450,000"), ("Annual income", "285,000"), ("Target retirement age", "60")],
        "notes": "Recommendations must be confirmed against the client's current circumstances and suitability record.",
        "summary_label": "Client review", "detail_label": "Planning snapshot",
    },
    "Finance Operations": {
        "primary": ("Supplier", "Harbour Office Supplies"),
        "fields": [("Document number", "document_number", "DOC-2026-0007"), ("Issue date", "issue_date", "2026-01-15"),
                    ("Due date", "due_date", "2026-02-14"), ("Currency", "currency", "USD")],
        "line_items": [("Office equipment", "4,250.00"), ("Software subscription", "1,200.00"), ("Tax", "545.00")],
        "notes": "Amounts are illustrative and should be reconciled to the source transaction before posting.",
        "summary_label": "Document details", "detail_label": "Amount summary",
    },
    "Scheduling & Calendars": {
        "primary": ("Event", "Quarterly operating review"),
        "fields": [("Organizer", "organizer", "Alex Morgan"), ("Start", "start_time", "2026-01-15 10:00"),
                    ("End", "end_time", "2026-01-15 11:00"), ("Location", "location", "Boardroom / video conference")],
        "line_items": [("Agenda item 1", "Operating results"), ("Agenda item 2", "Risk and controls"), ("Agenda item 3", "Actions and owners")],
        "notes": "Please circulate papers at least one business day before the meeting.",
        "summary_label": "Event details", "detail_label": "Agenda",
    },
    "Human Resources": {
        "primary": ("Employee", "Alex Morgan"),
        "fields": [("Department", "department", "Operations"), ("Manager", "manager", "Priya Shah"),
                    ("Effective date", "effective_date", "2026-01-15"), ("Status", "status", "For approval")],
        "line_items": [("Role", "Operations Analyst"), ("Work location", "Singapore"), ("Employment type", "Permanent")],
        "notes": "This sample is not an employment contract and must be reviewed against local requirements.",
        "summary_label": "Employee details", "detail_label": "Role summary",
    },
    "Legal & Compliance": {
        "primary": ("Matter", "Project Atlas"),
        "fields": [("Parties", "parties", "Northstar Holdings and Acme Manufacturing"), ("Effective date", "effective_date", "2026-01-15"),
                    ("Owner", "prepared_by", "Legal Operations"), ("Status", "status", "Draft for review")],
        "line_items": [("Review area", "Confidentiality and permitted use"), ("Review area", "Records retention"), ("Review area", "Approval authority")],
        "notes": "This template is a drafting aid and does not replace legal advice or an approved policy.",
        "summary_label": "Matter details", "detail_label": "Review checklist",
    },
    "Sales & Marketing": {
        "primary": ("Customer", "Northstar Retail Group"),
        "fields": [("Owner", "prepared_by", "Alex Morgan"), ("Date", "issue_date", "2026-01-15"),
                    ("Validity", "valid_until", "2026-02-15"), ("Status", "status", "Draft")],
        "line_items": [("Discovery and design", "12,500"), ("Implementation", "28,000"), ("Support", "6,000")],
        "notes": "Commercial terms, tax treatment and approval limits must be checked before sending externally.",
        "summary_label": "Opportunity details", "detail_label": "Commercial summary",
    },
    "General & Communications": {
        "primary": ("Audience", "Operations leadership team"),
        "fields": [("Author", "prepared_by", "Alex Morgan"), ("Date", "issue_date", "2026-01-15"),
                    ("Subject", "subject", "Quarterly operating update"), ("Status", "status", "For information")],
        "line_items": [("Headline", "Operating plan approved"), ("Owner", "Operations team"), ("Next update", "2026-02-15")],
        "notes": "Confirm recipients, confidentiality classification and approval before distribution.",
        "summary_label": "Communication details", "detail_label": "Key messages",
    },
}


def _catalog_entry(starter_id: str, name: str, category: str) -> dict:
    """Create a bounded, industry-shaped offline starter with complete sample data."""
    profile = _CATALOG_PROFILES[category]
    summary = [{"label": label, "value": value} for label, _path, value in profile["fields"]]
    line_items = [{"label": label, "value": value} for label, value in profile["line_items"]]
    primary_label, primary_value = profile["primary"]
    sample_data = {
        "primary": primary_value, "primary_label": primary_label, "summary": summary,
        "line_items": line_items, "notes": profile["notes"],
        # Kept for compatibility with the original multilingual certificate copy.
        "recipient": {"name": primary_value},
        "prepared_by": next(value for label, path, value in profile["fields"] if path == "prepared_by")
        if any(path == "prepared_by" for _label, path, _value in profile["fields"]) else "Document team",
    }
    for _label, path, value in profile["fields"]:
        sample_data[path] = value
    properties = {key: ({"type": "object", "properties": {"name": {"type": "string"}},
                         "required": ["name"]} if key == "recipient" else {"type": "string"})
                  for key in sample_data if key not in {"summary", "line_items"}}
    properties.update({"summary": {"type": "array", "items": {"type": "object", "properties": {
        "label": {"type": "string"}, "value": {"type": "string"}}, "required": ["label", "value"]}},
        "line_items": {"type": "array", "items": {"type": "object", "properties": {
            "label": {"type": "string"}, "value": {"type": "string"}}, "required": ["label", "value"]}}})
    return {
        "name": name, "category": category,
        "languages": {"en": {"title": name, "body": f"Prepared for {primary_value}."}},
        "sample_data": sample_data, "data_schema": {"type": "object", "properties": properties,
                                                        "required": ["primary", "summary", "line_items", "notes"]},
        "blocks": [
            {"type": "text", "text": name, "translation_key": "title", "bold": True, "font_size": 24},
            {"type": "text", "text": f"{primary_label}: {{{{primary}}}}", "translation_key": "body"},
            {"type": "text", "text": profile["summary_label"], "bold": True, "font_size": 16},
            {"type": "table", "items": "summary", "columns": [
                {"header": "Field", "path": "label", "format": "text"},
                {"header": "Value", "path": "value", "format": "text"}]},
            {"type": "text", "text": profile["detail_label"], "bold": True, "font_size": 16},
            {"type": "table", "items": "line_items", "columns": [
                {"header": "Item", "path": "label", "format": "text"},
                {"header": "Details", "path": "value", "format": "text"}]},
            {"type": "text", "text": "Notes: {{notes}}"},
        ],
        "page": {"size": "A4", "orientation": "portrait", "margin_mm": 20,
                 "header": name, "footer": "Confidential · {{primary}}", "show_page_numbers": True},
        "metadata": {"title": name, "author": "Document Platform starter catalog"},
    }


_CATALOG_GROUPS = {
    "Investment Banking": [
        ("deal-summary", "Deal summary"), ("term-sheet", "Term sheet"),
        ("credit-approval", "Credit approval memo"), ("cashflow-forecast", "Cash-flow forecast"),
        ("covenant-compliance", "Covenant compliance report"),
    ],
    "Asset Management": [
        ("investment-fact-sheet", "Investment fact sheet"), ("portfolio-review", "Portfolio review"),
        ("fund-quarterly-report", "Fund quarterly report"), ("kpi-dashboard", "Investment KPI dashboard"),
        ("client-performance", "Client performance report"),
    ],
    "Insurance": [
        ("insurance-quote", "Insurance quote"), ("policy-schedule", "Policy schedule"),
        ("claims-summary", "Claims summary"), ("renewal-notice", "Renewal notice"),
        ("underwriting-review", "Underwriting review"),
    ],
    "Wealth Management": [
        ("client-review", "Client review pack"), ("suitability-assessment", "Suitability assessment"),
        ("wealth-plan", "Wealth plan"), ("beneficiary-review", "Beneficiary review"),
        ("family-office-brief", "Family office brief"),
    ],
    "Finance Operations": [
        ("purchase-order", "Purchase order"), ("expense-report", "Expense report"),
        ("accounts-payable", "Accounts payable approval"),
    ],
    "Scheduling & Calendars": [
        ("calendar-invite", "Calendar invitation"), ("meeting-agenda", "Meeting agenda"),
        ("room-booking", "Room booking"), ("event-runbook", "Event runbook"),
        ("appointment-reminder", "Appointment reminder"),
    ],
    "Human Resources": [
        ("offer-letter", "Offer letter"), ("payslip", "Payslip"),
        ("performance-review", "Performance review"), ("onboarding-checklist", "Onboarding checklist"),
    ],
    "Legal & Compliance": [
        ("nda", "Non-disclosure agreement"), ("compliance-attestation", "Compliance attestation"),
        ("board-resolution", "Board resolution"), ("audit-request", "Audit request"),
        ("kyc-review", "KYC review"),
    ],
    "Sales & Marketing": [
        ("proposal", "Client proposal"), ("sales-quote", "Sales quote"),
        ("campaign-brief", "Campaign brief"), ("sales-order", "Sales order"),
        ("case-study", "Customer case study"),
    ],
    "General & Communications": [
        ("memo", "Business memo"), ("executive-brief", "Executive brief"),
        ("newsletter", "Newsletter"), ("announcement", "Company announcement"),
    ],
}
for _category, _entries in _CATALOG_GROUPS.items():
    for _starter_id, _name in _entries:
        STARTER_CATALOG.setdefault(_starter_id, _catalog_entry(_starter_id, _name, _category))

# The four original multilingual starters keep their language coverage, while sharing the
# reviewed document structures above so every homepage demo has the same complete-data contract.
for _starter_id, _name, _category in (("letter", "Letter", "General & Communications"),
                                       ("invoice", "Invoice", "Finance Operations"),
                                       ("certificate", "Certificate", "Human Resources"),
                                       ("receipt", "Receipt", "Finance Operations")):
    _languages = STARTER_CATALOG[_starter_id]["languages"]
    STARTER_CATALOG[_starter_id] = _catalog_entry(_starter_id, _name, _category)
    STARTER_CATALOG[_starter_id]["languages"] = _languages


def starter_definition(starter_id: str, language: str) -> dict:
    starter = STARTER_CATALOG.get(starter_id)
    if starter is None or language not in starter["languages"]:
        raise HTTPException(status_code=404, detail="Starter language not found")
    translations = {language: starter["languages"][language]}
    definition = {"name": f"{starter['name']} ({language})", "locale": language,
                  "sample_data": starter["sample_data"], "blocks": starter["blocks"],
                  "translations": translations, "schema_version": 1}
    return json.loads(json.dumps(definition, ensure_ascii=False))


def create_app(settings=None, engine=None, store=None, frontend=FRONTEND):
    settings = settings or load_settings()
    configured_calibration_profile = None
    if settings.confidence_calibration_path is not None:
        try:
            configured_calibration_profile = validate_profile(json.loads(
                settings.confidence_calibration_path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, CalibrationProfileError):
            raise ConfigurationError("Invalid confidence calibration profile") from None
    owns_engine = engine is None
    engine = engine or create_database(settings)
    store = store or create_store(settings)
    revision = expected_revision()

    def render_definition_for_worker(definition: dict) -> dict:
        bounded = dict(definition)
        bounded["allowed_image_hosts"] = list(settings.image_allowed_hosts)
        return bounded

    def pdf_renderer_configuration() -> tuple[str, list[str], str | None]:
        """Select a renderer without changing the legacy command setting."""
        if settings.pdf_renderer == "prince":
            command = settings.prince_renderer_command or settings.pdf_renderer_command
            license_file = str(settings.prince_license_file) if settings.prince_license_file else None
        else:
            command = settings.chromium_renderer_command or settings.pdf_renderer_command or default_command("chromium")
            license_file = None
        return settings.pdf_renderer, command, license_file

    def inline_stored_assets(html: str) -> str:
        """Stage local object-store images into the network-disabled PDF input."""
        media_types = {"png": "image/png", "jpg": "image/jpeg", "gif": "image/gif",
                       "webp": "image/webp", "svg": "image/svg+xml"}

        def replace(match: re.Match[str]) -> str:
            asset_name = match.group(1)
            extension = match.group(2)
            try:
                raw = store.get(f"assets/{asset_name}.{extension}")
            except FileNotFoundError:
                raise ValueError(f"stored image asset not found: {asset_name}.{extension}") from None
            if extension == "svg":
                validate_svg_markup(raw)
            return f"data:{media_types[extension]};base64,{base64.b64encode(raw).decode('ascii')}"

        return re.sub(r"/api/assets/([0-9a-f]{32})\.(png|jpg|gif|webp|svg)", replace, html)

    def merge_page_background(definition: dict, output: bytes) -> bytes:
        page = definition.get("page") if isinstance(definition.get("page"), dict) else {}
        source = page.get("background_pdf") if isinstance(page, dict) else ""
        if not source:
            return output
        prefix = "data:application/pdf;base64,"
        if not isinstance(source, str) or not source.startswith(prefix):
            raise PdfBackgroundError("page.background_pdf must be a base64 PDF data URI")
        try:
            background = base64.b64decode(source[len(prefix):], validate=True)
        except (ValueError, binascii.Error):
            raise PdfBackgroundError("page.background_pdf is not valid base64") from None
        return merge_pdf_background(output, background, max_bytes=settings.max_object_bytes)

    def expand_components(connection, definition: dict) -> dict:
        """Resolve component blocks at render time; editor definitions retain references."""
        rows = connection.execute(select(ReusableComponent.id, ReusableComponent.definition_json)).mappings().all()
        registry = {row["id"]: json.loads(row["definition_json"]) for row in rows}
        try:
            return expand_definition(definition, registry)
        except ComponentExpansionError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None

    def calibration_for(payload: dict) -> dict | None:
        """Use a request profile when supplied, otherwise the configured profile."""
        return payload.get("calibration_profile", configured_calibration_profile)

    @asynccontextmanager
    async def lifespan(app):
        stop_worker = threading.Event()
        worker_threads = []
        if settings.job_worker_enabled:
            def supervise_jobs(kind: str, index: int):
                worker_id = f"supervisor-{kind}-{index}-{uuid4().hex[:8]}"
                while not stop_worker.wait(settings.job_worker_poll_seconds):
                    try:
                        with engine.begin() as connection:
                            job = claim_next(connection, worker_id, kind)
                        if job is not None:
                            execute_job(job, worker_id)
                    except Exception:
                        # The job executor records terminal failures; a transient
                        # database error must not terminate the supervisor loop.
                        continue
            for kind, count in (("render", settings.job_worker_render_count),
                                ("extraction", settings.job_worker_extraction_count)):
                for index in range(count):
                    worker_thread = threading.Thread(target=supervise_jobs, args=(kind, index + 1),
                                                     name=f"docplatform-{kind}-worker-{index + 1}", daemon=True)
                    worker_threads.append(worker_thread)
                    worker_thread.start()
        yield
        stop_worker.set()
        for worker_thread in worker_threads:
            worker_thread.join(timeout=max(1.0, settings.job_worker_poll_seconds * 4))
        if owns_engine:
            engine.dispose()

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    def authenticated_user(request: Request, csrf: bool = False, scope: str | None = None,
                           allow_api_key: bool = True):
        """Require a server-side session once the initial local account exists."""
        with engine.connect() as connection:
            has_users = connection.execute(select(func.count()).select_from(User)).scalar_one() > 0
            if not has_users:
                return {"id": "local", "email": "local", "role": "admin"}
            supplied_key = request.headers.get("x-api-key")
            if supplied_key and allow_api_key:
                prefix = supplied_key[:11]
                row = connection.execute(select(ApiKey.id, ApiKey.key_hash, ApiKey.scopes_json).where(
                    ApiKey.prefix == prefix, ApiKey.revoked_at.is_(None))).mappings().one_or_none()
                if row is None or not hmac.compare_digest(hashlib.sha256(supplied_key.encode()).hexdigest(), row["key_hash"]):
                    raise HTTPException(status_code=401, detail="Invalid API key")
                scopes = json.loads(row["scopes_json"])
                if scope and scope not in scopes and "admin" not in scopes:
                    raise HTTPException(status_code=403, detail="API key scope does not allow this operation")
                return {"id": row["id"], "email": f"api-key:{row['id']}", "role": "api-key", "scopes": scopes}
            session_id = request.cookies.get("docplatform_session")
            if not session_id:
                raise HTTPException(status_code=401, detail="Authentication required")
            row = connection.execute(select(Session.user_id, Session.csrf_token, Session.expires_at,
                                            User.email, User.role, User.account_type, User.status,
                                            User.entitlements_json).join(User, User.id == Session.user_id).where(
                                                Session.id == session_id)).mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        expires = row["expires_at"]
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires <= datetime.now(UTC):
            raise HTTPException(status_code=401, detail="Authentication required")
        if csrf and not hmac.compare_digest(request.headers.get("x-csrf-token", ""), row["csrf_token"]):
            raise HTTPException(status_code=403, detail="CSRF token required")
        if row["status"] != "active":
            raise HTTPException(status_code=403, detail="Account is not active")
        return {"id": row["user_id"], "email": row["email"], "role": row["role"],
                "account_type": row["account_type"],
                "entitlements": json.loads(row["entitlements_json"] or "{}")}

    def workspace_access(connection, user: dict) -> dict:
        """Resolve workspace visibility centrally; the UI never performs authorization."""
        if user.get("id") in {"local"} or user.get("role") == "api-key":
            return {"workspace_ids": None, "organization_ids": None, "guest": False, "admin": True}
        memberships = connection.execute(select(OrganizationMembership.organization_id,
                                                  OrganizationMembership.workspace_id,
                                                  OrganizationMembership.role,
                                                  OrganizationMembership.entitlements_json).where(
                                                      OrganizationMembership.user_id == user["id"])).mappings().all()
        workspace_ids: set[str] = set()
        organization_ids: set[str] = set()
        admin_orgs: set[str] = set()
        for membership in memberships:
            organization_ids.add(membership["organization_id"])
            if membership["workspace_id"]:
                workspace_ids.add(membership["workspace_id"])
            if membership["role"] in {"admin", "super_admin"} or user.get("role") in {"admin", "super_admin"}:
                admin_orgs.add(membership["organization_id"])
        if user.get("role") == "super_admin":
            admin_orgs.update(connection.execute(select(Organization.id)).scalars().all())
        else:
            org_rows = connection.execute(select(Organization.id, Organization.parent_id)).mappings().all()
            changed = True
            while changed:
                changed = False
                for org in org_rows:
                    if org["parent_id"] in admin_orgs and org["id"] not in admin_orgs:
                        admin_orgs.add(org["id"]); changed = True
        if admin_orgs:
            workspace_ids.update(connection.execute(select(Workspace.id).where(
                Workspace.organization_id.in_(admin_orgs))).scalars().all())
        return {"workspace_ids": workspace_ids, "organization_ids": organization_ids,
                "guest": user.get("account_type") == "guest", "admin": bool(admin_orgs)}

    def template_is_accessible(connection, template_id: str, user: dict, *, write: bool = False) -> dict:
        row = connection.execute(select(Template.id, Template.owner_user_id, Template.workspace_id,
                                        Template.visibility).where(Template.id == template_id)).mappings().one_or_none()
        if row is None:
            alias = connection.execute(select(TemplateAlias.canonical_template_id).where(
                TemplateAlias.duplicate_template_id == template_id)).scalar_one_or_none()
            if alias:
                row = connection.execute(select(Template.id, Template.owner_user_id, Template.workspace_id,
                                               Template.visibility).where(Template.id == alias)).mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Template not found")
        access = workspace_access(connection, user)
        allowed = (row["visibility"] == "public" and not write) or row["owner_user_id"] == user.get("id") or (
            access["workspace_ids"] is None or row["workspace_id"] in access["workspace_ids"])
        if access["guest"] and (row["visibility"] != "public" or write):
            allowed = False
        if not allowed:
            raise HTTPException(status_code=404, detail="Template not found")
        return row

    def version_payload(row):
        return {"id": row["id"], "template_id": row["template_id"], "version": row["version"],
                "status": row["status"], "change_summary": row["change_summary"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "created_by_user_id": row.get("created_by_user_id"),
                "created_by_email": row.get("created_by_email")}

    def record_review_event(connection, result_id: str, from_status: str | None,
                            to_status: str, actor: str):
        if from_status == to_status:
            return
        connection.execute(ExtractionReviewEvent.__table__.insert().values(
            id=uuid4().hex, result_id=result_id, from_status=from_status,
            to_status=to_status, actor=actor, created_at=datetime.now(UTC)))

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
            if settings.template_publish_requires_approval and version["status"] != "approved":
                raise HTTPException(status_code=409, detail="Template version requires reviewer approval before publishing")
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

    def mark_ingestion_progress(document_id: str, processed: int, *, status: str = "running") -> None:
        """Publish bounded local extraction progress without claiming OCR/layout work."""
        with engine.begin() as connection:
            connection.execute(IngestionDocument.__table__.update().where(
                IngestionDocument.id == document_id).values(
                    status=status, pages_processed=processed))

    def mark_ingestion_processed(document_id: str) -> None:
        """Publish bounded local extraction completion to the ingestion progress row."""
        with engine.begin() as connection:
            connection.execute(IngestionDocument.__table__.update().where(
                IngestionDocument.id == document_id).values(
                    status="processed", pages_processed=IngestionDocument.pages_total))

    def persist_extraction_result(document_id: str, schema: dict, result: dict,
                                  page_model_payload: dict, result_id: str | None = None) -> dict:
        """Persist one extraction snapshot and return the review-shaped result."""
        result_id = result_id or uuid4().hex
        result["result_id"] = result_id
        result["page_model"] = page_model_payload
        with engine.begin() as connection:
            connection.execute(ExtractionResultRecord.__table__.insert().values(
                id=result_id, document_id=document_id,
                schema_id=str(schema.get("id") or "inline"),
                result_json=json.dumps(result), status=result["status"], revision=1))
        return result

    def extract_with_progress(document_id: str, page_model_payload: dict, schema: dict,
                              locale: str, engine_id: str,
                              calibration_profile: dict | None = None) -> dict:
        """Run the local/page-model contract one page at a time and merge its result.

        This deliberately applies only to the bounded page-model extractor. OCR and
        layout engines remain separate and must publish their own progress semantics.
        """
        pages = page_model_payload.get("pages")
        if not isinstance(pages, list) or not pages:
            pages = [{}]
        merged: dict | None = None
        for index, page in enumerate(pages):
            single_page_model = dict(page_model_payload)
            single_page_model["pages"] = [page]
            page_result = run_isolated(
                "extraction", {"page_model": single_page_model, "schema": schema,
                               "locale": locale, "engine_id": engine_id},
                timeout_seconds=settings.job_timeout_seconds,
                cpu_seconds=settings.job_cpu_seconds,
                memory_bytes=settings.job_memory_bytes,
                max_output_bytes=settings.job_max_output_bytes)
            if merged is None:
                merged = page_result
            else:
                for name, field in page_result.get("fields", {}).items():
                    existing = merged.setdefault("fields", {}).get(name)
                    if existing is None or existing.get("normalized_value") is None:
                        merged["fields"][name] = field
                for name, table in page_result.get("tables", {}).items():
                    target = merged.setdefault("tables", {}).setdefault(name, {
                        "columns": table.get("columns", []), "rows": [], "row_count": 0,
                        "engine": table.get("engine", "local-delimited-row-extractor")})
                    target.setdefault("rows", []).extend(table.get("rows", []))
                    target["row_count"] = len(target["rows"])
            mark_ingestion_progress(document_id, index + 1)
        assert merged is not None
        merged["document_id"] = page_model_payload.get("document_id")
        merged["status"] = "needs_review" if (
            any(field.get("review_status") == "needs_review" for field in merged.get("fields", {}).values())
            or any(field.get("review_status") == "needs_review"
                   for table in merged.get("tables", {}).values()
                   for row in table.get("rows", [])
                   for field in row.get("fields", {}).values())
        ) else "new"
        if calibration_profile is not None:
            merged = apply_profile(merged, calibration_profile, str(schema.get("id") or "inline"))
        return merged

    def execute_job(job: dict, worker_id: str):
        """Execute one claimed bounded job and publish only a terminal result."""
        try:
            payload = job["payload"]
            if job["kind"] == "render":
                with engine.connect() as connection:
                    _, version, definition = template_definition(
                        connection, payload["template_id"], payload.get("version_id"),
                        bool(payload.get("draft")))
                    definition = expand_components(connection, definition)
                result = run_isolated("render", {"definition": render_definition_for_worker(definition), "data": payload.get("data"),
                                                  "locale": payload.get("locale"),
                                                  "missing_policy": payload.get("missing_policy")},
                                      timeout_seconds=settings.job_timeout_seconds,
                                      cpu_seconds=settings.job_cpu_seconds,
                                      memory_bytes=settings.job_memory_bytes,
                                      max_output_bytes=settings.job_max_output_bytes)
                result.update({"template_id": payload["template_id"],
                               "version_id": version["id"] if version else None})
            elif job["kind"] == "extraction":
                with engine.connect() as connection:
                    row = connection.execute(select(IngestionDocument.page_model_json).where(
                        IngestionDocument.id == payload["document_id"])).mappings().one_or_none()
                if row is None:
                    raise ValueError("Ingestion not found")
                schema = payload.get("schema") or BUNDLED_SCHEMAS.get(payload.get("schema_id"))
                if not isinstance(schema, dict):
                    raise ValueError("schema or schema_id is required")
                result = extract_with_progress(str(payload["document_id"]), json.loads(row["page_model_json"]),
                                               schema, str(payload.get("locale", "en")),
                                               str(payload.get("engine_id", "local-label-extractor")),
                                               calibration_for(payload))
                result = persist_extraction_result(str(payload["document_id"]), schema, result,
                                                   json.loads(row["page_model_json"]),
                                                   str(payload.get("result_id") or uuid4().hex))
                mark_ingestion_processed(str(payload["document_id"]))
            else:
                raise ValueError("unsupported job kind")
            with engine.begin() as connection:
                connection.execute(Job.__table__.update().where(Job.id == job["id"]).values(
                    status="done", result_json=json.dumps(result), error=None,
                    lease_owner=None, lease_expires_at=None, updated_at=func.now()))
            return result
        except Exception as exc:
            with engine.begin() as connection:
                connection.execute(Job.__table__.update().where(Job.id == job["id"]).values(
                    status="failed", error=str(exc)[:500], lease_owner=None,
                    lease_expires_at=None, updated_at=func.now()))
            raise

    # The standalone worker service reuses the exact same executor and lease
    # contract as the API's synchronous/durable-job paths. Keeping this as an
    # application state hook avoids a second implementation of job semantics.
    app.state.execute_job = execute_job

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

    @app.post("/api/jobs", status_code=202, tags=["jobs"])
    def create_job(payload: dict, request: Request):
        kind = str(payload.get("kind", ""))
        if request.headers.get("x-api-key"):
            authenticated_user(request, scope="render" if kind == "render" else "read")
        job_id = uuid4().hex
        job_payload = dict(payload)
        sync = bool(job_payload.pop("sync", False))
        try:
            with engine.begin() as connection:
                enqueue(connection, kind, job_payload, job_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        if sync:
            try:
                result = execute_job({"id": job_id, "kind": kind, "payload": job_payload}, "api-sync")
            except Exception:
                return JSONResponse({"id": job_id, "status": "failed"}, status_code=422)
            return {"id": job_id, "status": "done", "result": result}
        return JSONResponse({"id": job_id, "status": "queued", "status_url": f"/api/jobs/{job_id}"},
                            status_code=202)

    @app.get("/api/jobs/{job_id}", tags=["jobs"])
    def get_job(job_id: str):
        with engine.connect() as connection:
            row = connection.execute(select(Job.id, Job.kind, Job.status, Job.result_json,
                                             Job.error, Job.attempts, Job.created_at,
                                             Job.updated_at).where(Job.id == job_id)).mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"id": row["id"], "kind": row["kind"], "status": row["status"],
                "result": json.loads(row["result_json"]) if row["result_json"] else None,
                "error": row["error"], "attempts": row["attempts"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None}

    @app.post("/api/jobs/{job_id}/run", tags=["jobs"])
    def run_job(job_id: str, request: Request, payload: dict | None = None):
        worker_id = str((payload or {}).get("worker_id") or "api-worker")
        with engine.connect() as connection:
            kind_row = connection.execute(select(Job.kind).where(Job.id == job_id)).first()
        if kind_row is None:
            raise HTTPException(status_code=404, detail="Job not found")
        authenticated_user(request, scope="render" if kind_row[0] == "render" else "read")
        with engine.begin() as connection:
            job = claim(connection, job_id, worker_id)
        if job is None:
            raise HTTPException(status_code=409, detail="Job is not queued or its lease is still active")
        try:
            result = execute_job(job, worker_id)
        except Exception:
            return JSONResponse({"id": job_id, "status": "failed"}, status_code=422)
        return {"id": job_id, "status": "done", "result": result}

    @app.post("/api/auth/setup", status_code=201, tags=["auth"])
    def auth_setup(payload: dict):
        email = str(payload.get("email", "")).strip().casefold()
        password = payload.get("password")
        if "@" not in email or not isinstance(password, str):
            raise HTTPException(status_code=422, detail="A valid email and password are required")
        try:
            password_hash = hash_password(password)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        user_id = uuid4().hex
        try:
            with engine.begin() as connection:
                if connection.execute(select(func.count()).select_from(User)).scalar_one():
                    raise HTTPException(status_code=409, detail="Initial account already exists")
                connection.execute(User.__table__.insert().values(
                    id=user_id, email=email, password_hash=password_hash, role="admin",
                    account_type="member", status="active",
                    entitlements_json=json.dumps({"version": 1, "features": {"workspace.admin": True}})))
                if connection.execute(select(Organization.id).where(Organization.id == "org-good-docs")).first() is None:
                    connection.execute(Organization.__table__.insert().values(
                        id="org-good-docs", name="Good docs", slug="good-docs",
                        entitlements_json=json.dumps({"version": 1, "features": {"catalog": True, "guest": True}})))
                if connection.execute(select(Workspace.id).where(Workspace.id == "workspace-good-docs")).first() is None:
                    connection.execute(Workspace.__table__.insert().values(
                        id="workspace-good-docs", organization_id="org-good-docs", name="Good docs", slug="good-docs",
                        entitlements_json=json.dumps({"version": 1, "features": {"templates.read": True}})))
                connection.execute(OrganizationMembership.__table__.insert().values(
                    id=f"membership-{user_id}", user_id=user_id, organization_id="org-good-docs",
                    workspace_id=None, role="super_admin", entitlements_json=json.dumps({"version": 1})))
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=409, detail="Initial account already exists") from None
        return {"id": user_id, "email": email, "role": "admin"}

    @app.get("/api/auth/config", tags=["auth"])
    def auth_config():
        with engine.connect() as connection:
            users = connection.execute(select(func.count()).select_from(User)).scalar_one()
        return {"setup_required": users == 0, "password_login": True, "guest_login": True,
                "signup": True, "sso": {"enabled": False, "provider": None,
                                          "start_url": "/api/auth/sso/start"}}

    def create_restricted_session(connection, user_id: str, *, response_payload: dict):
        session_id, csrf_token, expires = new_session()
        connection.execute(Session.__table__.insert().values(
            id=session_id, user_id=user_id, csrf_token=csrf_token, expires_at=expires))
        response = JSONResponse({**response_payload, "csrf_token": csrf_token, "expires_at": expires.isoformat()})
        response.set_cookie("docplatform_session", session_id, httponly=True, samesite="lax",
                            secure=settings.secure_cookies, max_age=int(SESSION_TTL.total_seconds()))
        return response

    @app.post("/api/auth/guest", tags=["auth"])
    def auth_guest():
        user_id = f"guest-{uuid4().hex}"
        email = f"{user_id}@guest.invalid"
        password_hash = hash_password(uuid4().hex + uuid4().hex)
        with engine.begin() as connection:
            connection.execute(User.__table__.insert().values(
                id=user_id, email=email, password_hash=password_hash, role="viewer",
                account_type="guest", status="active",
                entitlements_json=json.dumps({"version": 1, "features": {"catalog.read": True}})))
            connection.execute(OrganizationMembership.__table__.insert().values(
                id=f"membership-{user_id}", user_id=user_id, organization_id="org-good-docs",
                workspace_id="workspace-good-docs", role="guest",
                entitlements_json=json.dumps({"version": 1, "features": {"catalog.read": True}})))
            return create_restricted_session(connection, user_id,
                                            response_payload={"id": user_id, "email": email,
                                                              "role": "viewer", "account_type": "guest"})

    @app.post("/api/auth/signup", tags=["auth"])
    def auth_signup(payload: dict):
        email = str(payload.get("email", "")).strip().casefold()
        if "@" not in email or len(email) > 320:
            raise HTTPException(status_code=422, detail="A valid email address is required")
        user_id = uuid4().hex
        password_hash = hash_password(uuid4().hex + uuid4().hex)
        with engine.begin() as connection:
            if connection.execute(select(User.id).where(User.email == email)).first():
                raise HTTPException(status_code=409, detail="An account already exists for this email")
            connection.execute(User.__table__.insert().values(
                id=user_id, email=email, password_hash=password_hash, role="viewer",
                account_type="pending", status="active",
                entitlements_json=json.dumps({"version": 1, "features": {"catalog.read": True}})))
            connection.execute(OrganizationMembership.__table__.insert().values(
                id=f"membership-{user_id}", user_id=user_id, organization_id="org-good-docs",
                workspace_id="workspace-good-docs", role="guest",
                entitlements_json=json.dumps({"version": 1, "features": {"catalog.read": True}})))
            return create_restricted_session(connection, user_id,
                                            response_payload={"id": user_id, "email": email,
                                                              "role": "viewer", "account_type": "pending"})

    @app.get("/api/auth/sso/start", tags=["auth"])
    def auth_sso_start():
        raise HTTPException(status_code=501, detail="SSO is not configured; use password, guest, or sign-up")

    @app.get("/api/workspaces", tags=["workspaces"])
    def workspaces(request: Request):
        user = authenticated_user(request, scope="read")
        with engine.connect() as connection:
            access = workspace_access(connection, user)
            query = select(Workspace.id, Workspace.organization_id, Workspace.name, Workspace.slug,
                           Organization.name.label("organization_name"), Organization.parent_id).join(
                               Organization, Organization.id == Workspace.organization_id).order_by(
                                   Organization.name, Workspace.name)
            if access["workspace_ids"] is not None:
                query = query.where(Workspace.id.in_(access["workspace_ids"]))
            rows = connection.execute(query).mappings().all()
            return {"items": [{"id": row["id"], "organization_id": row["organization_id"],
                               "organization_name": row["organization_name"], "name": row["name"],
                               "slug": row["slug"], "parent_organization_id": row["parent_id"]}
                              for row in rows]}

    @app.post("/api/auth/login", tags=["auth"])
    def auth_login(payload: dict):
        email = str(payload.get("email", "")).strip().casefold()
        password = payload.get("password")
        now = datetime.now(UTC)
        failure: str | None = None
        with engine.begin() as connection:
            row = connection.execute(select(User.id, User.email, User.password_hash, User.role,
                                             User.account_type, User.status,
                                             User.failed_attempts, User.locked_until).where(
                                                 User.email == email)).mappings().one_or_none()
            if row is None:
                failure = "invalid"
            else:
                locked = row["locked_until"]
                if locked is not None:
                    if locked.tzinfo is None:
                        locked = locked.replace(tzinfo=UTC)
                    if locked > now:
                        failure = "locked"
                if failure is None and (not isinstance(password, str) or not verify_password(password, row["password_hash"])):
                    failures = row["failed_attempts"] + 1
                    values = {"failed_attempts": failures}
                    if failures >= MAX_LOGIN_FAILURES:
                        values["locked_until"] = now + LOCKOUT
                    connection.execute(User.__table__.update().where(User.id == row["id"]).values(**values))
                    failure = "invalid"
            if failure is None:
                session_id, csrf_token, expires = new_session()
                connection.execute(User.__table__.update().where(User.id == row["id"]).values(
                    failed_attempts=0, locked_until=None))
                connection.execute(Session.__table__.insert().values(
                    id=session_id, user_id=row["id"], csrf_token=csrf_token, expires_at=expires))
        if failure == "locked":
            raise HTTPException(status_code=429, detail="Account temporarily locked")
        if failure == "invalid":
            raise HTTPException(status_code=401, detail="Invalid credentials")
        response = JSONResponse({"id": row["id"], "email": row["email"], "role": row["role"],
                                 "account_type": row["account_type"],
                                 "csrf_token": csrf_token, "expires_at": expires.isoformat()})
        response.set_cookie("docplatform_session", session_id, httponly=True, samesite="lax",
                            secure=settings.secure_cookies, max_age=int(SESSION_TTL.total_seconds()))
        return response

    @app.get("/api/auth/me", tags=["auth"])
    def auth_me(request: Request):
        return authenticated_user(request)

    @app.post("/api/auth/logout", tags=["auth"])
    def auth_logout(request: Request):
        session_id = request.cookies.get("docplatform_session")
        if session_id:
            with engine.begin() as connection:
                connection.execute(Session.__table__.delete().where(Session.id == session_id))
        response = JSONResponse({"status": "logged_out"})
        response.delete_cookie("docplatform_session", secure=settings.secure_cookies, httponly=True, samesite="lax")
        return response

    @app.post("/api/auth/api-keys", status_code=201, tags=["auth"])
    def create_api_key(request: Request, payload: dict):
        authenticated_user(request, csrf=True, allow_api_key=False)
        name = str(payload.get("name", "")).strip()
        scopes = sorted({str(scope) for scope in payload.get("scopes", [])})
        if not name or len(name) > 200:
            raise HTTPException(status_code=422, detail="name is required and must be at most 200 characters")
        if not scopes or not set(scopes).issubset({"read", "render", "admin"}):
            raise HTTPException(status_code=422, detail="scopes must contain read, render, or admin")
        secret, prefix, key_hash = new_api_key()
        key_id = uuid4().hex
        with engine.begin() as connection:
            connection.execute(ApiKey.__table__.insert().values(
                id=key_id, name=name, prefix=prefix, key_hash=key_hash,
                scopes_json=json.dumps(scopes)))
        return {"id": key_id, "name": name, "scopes": scopes, "key": secret,
                "warning": "Store this key now; it will not be shown again"}

    @app.get("/api/auth/api-keys", tags=["auth"])
    def list_api_keys(request: Request):
        authenticated_user(request, csrf=False, allow_api_key=False)
        with engine.connect() as connection:
            rows = connection.execute(select(ApiKey.id, ApiKey.name, ApiKey.prefix,
                                             ApiKey.scopes_json, ApiKey.revoked_at,
                                             ApiKey.created_at).order_by(ApiKey.created_at.desc())).mappings().all()
        return {"items": [{"id": row["id"], "name": row["name"], "prefix": row["prefix"],
                           "scopes": json.loads(row["scopes_json"]),
                           "revoked": row["revoked_at"] is not None,
                           "created_at": row["created_at"].isoformat() if row["created_at"] else None}
                          for row in rows]}

    @app.delete("/api/auth/api-keys/{key_id}", tags=["auth"])
    def revoke_api_key(key_id: str, request: Request):
        authenticated_user(request, csrf=True, allow_api_key=False)
        with engine.begin() as connection:
            updated = connection.execute(ApiKey.__table__.update().where(ApiKey.id == key_id,
                                                                          ApiKey.revoked_at.is_(None)).values(
                                                                              revoked_at=func.now()))
            if updated.rowcount == 0:
                raise HTTPException(status_code=404, detail="API key not found")
        return {"id": key_id, "revoked": True}

    @app.get("/api/templates", tags=["templates"])
    def templates(q: str | None = None, folder: str | None = None, tag: str | None = None,
                  scope: str = "all", limit: int = 24, offset: int = 0,
                  edited_by: str | None = None, edited_from: str | None = None,
                  edited_to: str | None = None,
                  request: Request = None):
        user = authenticated_user(request, scope="read")
        limit = min(100, max(1, limit)); offset = max(0, offset)
        with engine.connect() as connection:
            access = workspace_access(connection, user)
            edited_from_dt = None
            edited_to_dt = None
            try:
                if edited_from:
                    edited_from_dt = datetime.fromisoformat(edited_from).replace(tzinfo=UTC)
                if edited_to:
                    edited_to_dt = datetime.fromisoformat(edited_to).replace(tzinfo=UTC) + timedelta(days=1)
            except ValueError:
                raise HTTPException(status_code=422, detail="edited_from and edited_to must be ISO dates") from None
            rows = connection.execute(select(Template.id, Template.name, Template.schema_version,
                                             Template.folder, Template.tags_json,
                                             Template.published_version_id, Template.owner_user_id,
                                             Template.workspace_id, Template.visibility,
                                             Template.created_at, Template.updated_at,
                                             Template.updated_by_user_id,
                                             User.email.label("updated_by_email")).select_from(Template).outerjoin(
                                                 User, User.id == Template.updated_by_user_id
                                             ).order_by(Template.updated_at.desc(), Template.name)).mappings().all()
            items = []
            for row in rows:
                mine = row["owner_user_id"] == user.get("id")
                in_workspace = access["workspace_ids"] is None or row["workspace_id"] in access["workspace_ids"]
                visible = row["visibility"] == "public" or mine or in_workspace
                if access["guest"]:
                    visible = row["visibility"] == "public"
                if scope == "mine" and not mine:
                    visible = False
                if scope == "organization" and not in_workspace:
                    visible = False
                if not visible:
                    continue
                tags = json.loads(row["tags_json"] or "[]")
                if folder is not None and row["folder"] != folder:
                    continue
                if tag is not None and tag not in tags:
                    continue
                searchable = f"{row['name']} {row['folder']} {' '.join(tags)}".lower()
                if q and q.lower() not in searchable:
                    continue
                updated_at = row["updated_at"] or row["created_at"]
                editor_search = f"{row['updated_by_email'] or ''} {row['updated_by_user_id'] or ''}".lower()
                if edited_by and edited_by.lower() not in editor_search:
                    continue
                if edited_from_dt and (updated_at is None or updated_at.replace(tzinfo=UTC) < edited_from_dt):
                    continue
                if edited_to_dt and (updated_at is None or updated_at.replace(tzinfo=UTC) >= edited_to_dt):
                    continue
                published = connection.execute(select(TemplateVersion.version).where(
                    TemplateVersion.id == row["published_version_id"])).scalar_one_or_none()
                items.append({"id": row["id"], "name": row["name"], "schema_version": row["schema_version"],
                              "folder": row["folder"], "tags": tags,
                              "owner_user_id": row["owner_user_id"], "workspace_id": row["workspace_id"],
                              "visibility": row["visibility"],
                              "edited_at": updated_at.isoformat() if updated_at else None,
                              "edited_by_user_id": row["updated_by_user_id"],
                              "edited_by": row["updated_by_email"] or row["updated_by_user_id"] or "System",
                              "published_version": published,
                              "published_version_id": row["published_version_id"]})
            return {"items": items[offset:offset + limit], "offset": offset,
                    "limit": limit, "total": len(items), "has_more": offset + limit < len(items),
                    "next_offset": offset + limit if offset + limit < len(items) else None}

    @app.get("/api/templates/{template_id}", tags=["templates"])
    def template(template_id: str, version: str | None = None, draft: bool = False,
                 request: Request = None):
        user = authenticated_user(request, scope="read")
        with engine.connect() as connection:
            resolved = template_is_accessible(connection, template_id, user, write=False)
            template_id = resolved["id"]
            _, version_row, definition = template_definition(connection, template_id, version, draft)
            definition = dict(definition)
            definition["version"] = version_row["version"] if version_row else 1
            definition["version_id"] = version_row["id"] if version_row else None
            definition["status"] = version_row["status"] if version_row else "published"
            return definition

    @app.get("/api/components", tags=["templates"])
    def components():
        with engine.connect() as connection:
            rows = connection.execute(select(ReusableComponent.id, ReusableComponent.name,
                                             ReusableComponent.version, ReusableComponent.updated_at)
                                      .order_by(ReusableComponent.name)).mappings().all()
            return {"items": [{"id": row["id"], "name": row["name"], "version": row["version"],
                               "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None}
                              for row in rows]}

    @app.get("/api/components/{component_id}", tags=["templates"])
    def component(component_id: str):
        with engine.connect() as connection:
            row = connection.execute(select(ReusableComponent).where(ReusableComponent.id == component_id)).mappings().one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Component not found")
            return {"id": row["id"], "name": row["name"], "version": row["version"],
                    "definition": json.loads(row["definition_json"])}

    @app.post("/api/components", status_code=201, tags=["templates"])
    def create_component(payload: dict):
        name = str(payload.get("name", "")).strip()
        definition = payload.get("definition")
        if not name or len(name) > 200 or not isinstance(definition, dict) or not isinstance(definition.get("blocks"), list):
            raise HTTPException(status_code=422, detail="name and definition.blocks are required")
        try:
            validate_component_definition(definition)
        except ComponentDefinitionError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        component_id = str(payload.get("id") or uuid4().hex)
        with engine.begin() as connection:
            if connection.execute(select(ReusableComponent.id).where(
                    (ReusableComponent.id == component_id) | (ReusableComponent.name == name))).first():
                raise HTTPException(status_code=409, detail="Component already exists")
            connection.execute(ReusableComponent.__table__.insert().values(
                id=component_id, name=name, definition_json=json.dumps(definition, ensure_ascii=False), version=1))
        return {"id": component_id, "name": name, "version": 1}

    @app.put("/api/components/{component_id}", tags=["templates"])
    def update_component(component_id: str, payload: dict):
        definition = payload.get("definition")
        if not isinstance(definition, dict) or not isinstance(definition.get("blocks"), list):
            raise HTTPException(status_code=422, detail="definition.blocks is required")
        try:
            validate_component_definition(definition)
        except ComponentDefinitionError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        with engine.begin() as connection:
            current = connection.execute(select(ReusableComponent.version).where(
                ReusableComponent.id == component_id)).scalar_one_or_none()
            if current is None:
                raise HTTPException(status_code=404, detail="Component not found")
            connection.execute(ReusableComponent.__table__.update().where(
                ReusableComponent.id == component_id).values(
                    definition_json=json.dumps(definition, ensure_ascii=False), version=current + 1,
                    updated_at=func.now()))
        return {"id": component_id, "version": current + 1}

    @app.post("/api/templates", status_code=201, tags=["templates"])
    def create_template(payload: dict, request: Request):
        user = authenticated_user(request, csrf=True, scope="write")
        definition = payload.get("definition") or payload
        name = str(payload.get("name") or definition.get("name") or "Untitled template").strip()
        if not name or len(name) > 200:
            raise HTTPException(status_code=422, detail="Template name is required")
        template_id = str(payload.get("id") or uuid4().hex)
        version_id = f"{template_id}-v1"
        folder = str(payload.get("folder", ""))[:200]
        visibility = str(payload.get("visibility", "workspace"))
        if visibility not in {"private", "workspace", "public"}:
            raise HTTPException(status_code=422, detail="visibility must be private, workspace, or public")
        tags = sorted({str(tag) for tag in payload.get("tags", [])})
        definition = dict(definition); definition["name"] = name; definition.setdefault("schema_version", 1)
        encoded = json.dumps(definition, ensure_ascii=False, sort_keys=True).encode("utf-8")
        key = f"templates/{template_id}/v1.json"
        store.put(key, encoded)
        with engine.begin() as connection:
            if connection.execute(select(Template.id).where(Template.id == template_id)).first():
                raise HTTPException(status_code=409, detail="Template id already exists")
            access = workspace_access(connection, user)
            workspace_id = str(payload.get("workspace_id") or "").strip() or None
            if user.get("id") == "local":
                workspace_id = workspace_id or "workspace-good-docs"
            else:
                workspace_id = workspace_id or next(iter(access["workspace_ids"] or set()), None)
            if user.get("id") != "local" and workspace_id not in (access["workspace_ids"] or set()):
                raise HTTPException(status_code=403, detail="You do not have access to this workspace")
            if user.get("account_type") in {"guest", "pending"}:
                raise HTTPException(status_code=403, detail="Guest accounts cannot create templates")
            editor_id = None if user.get("id") == "local" else user.get("id")
            connection.execute(Template.__table__.insert().values(
                id=template_id, name=name, object_key=key, schema_version=1, folder=folder,
                tags_json=json.dumps(tags), published_version_id=None, owner_user_id=None if user.get("id") == "local" else user.get("id"),
                workspace_id=workspace_id, visibility=visibility, updated_by_user_id=editor_id))
            connection.execute(TemplateVersion.__table__.insert().values(
                id=version_id, template_id=template_id, version=1, status="draft",
                change_summary="Initial draft", definition_json=encoded.decode("utf-8"), created_by_user_id=editor_id))
        return {"id": template_id, "version_id": version_id, "status": "draft", "workspace_id": workspace_id}

    @app.get("/api/templates/{template_id}/versions", tags=["templates"])
    def versions(template_id: str):
        with engine.connect() as connection:
            if not connection.execute(select(Template.id).where(Template.id == template_id)).first():
                raise HTTPException(status_code=404, detail="Template not found")
            rows = connection.execute(select(TemplateVersion.id, TemplateVersion.template_id,
                                             TemplateVersion.version, TemplateVersion.status,
                                             TemplateVersion.change_summary, TemplateVersion.created_at,
                                             TemplateVersion.created_by_user_id,
                                             User.email.label("created_by_email")).select_from(TemplateVersion).outerjoin(
                                                 User, User.id == TemplateVersion.created_by_user_id
                                             ).where(TemplateVersion.template_id == template_id).order_by(TemplateVersion.version.desc())).mappings().all()
            return {"items": [version_payload(row) for row in rows]}

    @app.post("/api/templates/{template_id}/versions", status_code=201, tags=["templates"])
    def create_version(template_id: str, payload: dict, request: Request):
        user = authenticated_user(request, csrf=True, scope="write")
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
                change_summary=str(payload.get("change_summary", "Updated draft"))[:500], definition_json=encoded,
                created_by_user_id=None if user.get("id") == "local" else user.get("id")))
            connection.execute(Template.__table__.update().where(Template.id == template_id).values(
                object_key=key, updated_at=func.now(), updated_by_user_id=None if user.get("id") == "local" else user.get("id")))
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

    @app.post("/api/templates/{template_id}/review/{version_id}", tags=["templates"])
    def review_template_version(template_id: str, version_id: str, payload: dict):
        state = payload.get("status")
        if state not in {"approved", "rejected"}:
            raise HTTPException(status_code=422, detail="status must be approved or rejected")
        with engine.begin() as connection:
            row = connection.execute(select(TemplateVersion.id).where(
                TemplateVersion.id == version_id, TemplateVersion.template_id == template_id)).one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Version not found")
            connection.execute(TemplateVersion.__table__.update().where(
                TemplateVersion.id == version_id).values(status=state))
        return {"template_id": template_id, "version_id": version_id, "status": state}

    @app.post("/api/templates/{template_id}/restore/{version_id}", status_code=201, tags=["templates"])
    def restore(template_id: str, version_id: str, request: Request):
        with engine.connect() as connection:
            version = connection.execute(select(TemplateVersion.version, TemplateVersion.definition_json).where(and_(
                TemplateVersion.id == version_id, TemplateVersion.template_id == template_id))).mappings().one_or_none()
            if version is None:
                raise HTTPException(status_code=404, detail="Version not found")
            definition = json.loads(version["definition_json"])
        return create_version(template_id, {"definition": definition, "change_summary": f"Restored from v{version['version']}"}, request)

    @app.post("/api/templates/{template_id}/duplicate", status_code=201, tags=["templates"])
    def duplicate(template_id: str, payload: dict | None = None, request: Request = None):
        with engine.connect() as connection:
            source, _, definition = template_definition(connection, template_id)
            source_tags = json.loads(source["tags_json"] or "[]")
        body = {"name": (payload or {}).get("name") or f"{source['name']} copy", "folder": source["folder"],
                "tags": source_tags, "definition": definition}
        return create_template(body, request)

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
                                "tags": payload.get("tags", []), "definition": definition}, request)

    @app.post("/api/word/merge", tags=["output"])
    async def merge_word(request: Request):
        authenticated_user(request, scope="render")
        try:
            payload = await request.json()
        except ValueError:
            raise HTTPException(status_code=422, detail="Expected JSON merge payload") from None
        if not isinstance(payload, dict) or not isinstance(payload.get("template_base64"), str):
            raise HTTPException(status_code=422, detail="template_base64 is required")
        encoded = payload["template_base64"]
        if len(encoded) > ((settings.max_object_bytes + 2) // 3) * 4:
            raise HTTPException(status_code=413, detail="Word template exceeds the configured size limit")
        try:
            template = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError):
            raise HTTPException(status_code=422, detail="template_base64 is invalid") from None
        if len(template) > settings.max_object_bytes:
            raise HTTPException(status_code=413, detail="Word template exceeds the configured size limit")
        data = payload.get("data", {})
        try:
            merged, report = merge_docx(template, data)
        except WordMergeError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        return {"document_base64": base64.b64encode(merged).decode("ascii"), "report": report}

    @app.post("/api/word/convert", tags=["output"])
    async def convert_word(request: Request):
        authenticated_user(request, scope="render")
        if not settings.word_converter_command:
            raise HTTPException(status_code=503, detail="Word-to-PDF converter is not configured")
        try:
            payload = await request.json()
        except ValueError:
            raise HTTPException(status_code=422, detail="Expected JSON conversion payload") from None
        if not isinstance(payload, dict) or not isinstance(payload.get("document_base64"), str):
            raise HTTPException(status_code=422, detail="document_base64 is required")
        try:
            docx = base64.b64decode(payload["document_base64"], validate=True)
        except (ValueError, TypeError):
            raise HTTPException(status_code=422, detail="document_base64 is invalid") from None
        if len(docx) > settings.max_object_bytes:
            raise HTTPException(status_code=413, detail="Word document exceeds the configured size limit")
        try:
            metadata = payload.get("metadata")
            if metadata is not None and (not isinstance(metadata, dict) or
                                         any(not isinstance(value, str) for value in metadata.values())):
                raise HTTPException(status_code=422, detail="metadata must be an object of strings")
            output, report = convert_docx_to_pdf(docx, settings.word_converter_command,
                                                 settings.word_converter_timeout_seconds,
                                                 settings.max_object_bytes, metadata)
        except WordConversionUnavailable:
            raise HTTPException(status_code=503, detail="Word-to-PDF converter is not configured") from None
        except WordConversionError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        return {"document_base64": encode_pdf(output), "report": report}

    @app.get("/api/editor/capabilities", tags=["templates"])
    def editor_capabilities():
        """Return the editor capability manifest used by the E16 fidelity harness."""
        return capability_manifest()

    @app.get("/api/starters", tags=["templates"])
    def starters():
        return {"items": [{"id": starter_id, "name": starter["name"],
                           "category": starter["category"],
                           "languages": list(starter["languages"]),
                           "definitions": {language: starter_definition(starter_id, language)
                                           for language in starter["languages"]}}
                          for starter_id, starter in STARTER_CATALOG.items()]}

    @app.post("/api/ingestions", status_code=201, tags=["ingestion"])
    async def ingest(request: Request, filename: str,
                     ocr_language: str = Query("eng", min_length=2, max_length=20),
                     ocr_engine: str = Query("paddleocr", min_length=2, max_length=40)):
        authenticated_user(request, scope="read")
        raw = await request.body()
        if not filename or len(filename) > 255:
            raise HTTPException(status_code=422, detail="filename is required and must be at most 255 characters")
        if not raw:
            raise HTTPException(status_code=422, detail="upload cannot be empty")
        if len(raw) > settings.max_object_bytes:
            raise HTTPException(status_code=413, detail="upload exceeds the configured size limit")
        try:
            classification = classify_upload(filename, request.headers.get("content-type", ""), raw)
        except IngestionInputError as exc:
            raise HTTPException(status_code=415, detail=str(exc)) from None
        if classification.media_type == "application/pdf":
            try:
                validate_pdf_active_content(raw)
            except ValueError as exc:
                raise HTTPException(status_code=415, detail=str(exc)) from None
        normalized_language = ocr_language.replace("_", "-").casefold()
        if not re.fullmatch(r"[a-z]{2,8}(?:-[a-z0-9]{2,8})?", normalized_language):
            raise HTTPException(status_code=422, detail="ocr_language must be a language code")
        if ocr_engine.casefold() not in {"paddleocr", "tesseract"}:
            raise HTTPException(status_code=422, detail="ocr_engine must be paddleocr or tesseract")
        document_id = uuid4().hex
        pages_total = count_pages(filename, raw)
        if pages_total > settings.max_pages_per_document:
            raise HTTPException(status_code=413, detail="upload exceeds the configured page limit")
        page_routes = detect_page_routes(raw, pages_total, classification.route)
        try:
            scan_upload(raw, settings.virus_scan_command, settings.virus_scan_timeout_seconds)
        except UploadScanError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        dimensions = image_dimensions(raw, classification.media_type) if classification.route == "scan" else None
        if dimensions and dimensions[0] * dimensions[1] > settings.max_image_pixels:
            raise HTTPException(status_code=413, detail="image exceeds the configured pixel limit")
        elements = simple_pdf_text_elements(raw) if classification.route == "digital" else []
        ocr_page_elements: dict[int, list[dict]] = {}
        ocr_report: dict[str, object]
        ocr_target_pages = {index + 1 for index, route in enumerate(page_routes) if route == "scan"}
        if ocr_target_pages and settings.ocr_command:
            try:
                worker_output = run_isolated(
                    "ocr", {"data_base64": base64.b64encode(raw).decode("ascii"),
                            "command": settings.ocr_command, "language": normalized_language,
                            "timeout_seconds": settings.ocr_timeout_seconds},
                    timeout_seconds=settings.ocr_timeout_seconds,
                    cpu_seconds=settings.job_cpu_seconds,
                    memory_bytes=settings.job_memory_bytes,
                    max_output_bytes=settings.job_max_output_bytes)
                ocr_output = worker_output
            except (WorkerExecutionError, KeyError) as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from None
            returned_page_elements = {page["page_number"]: page["elements"] for page in ocr_output["pages"]}
            if any(page_number > pages_total for page_number in returned_page_elements):
                raise HTTPException(status_code=422, detail="OCR output contains a page beyond the upload page limit")
            ocr_page_elements = {page_number: elements for page_number, elements in returned_page_elements.items()
                                 if page_number in ocr_target_pages}
            ocr_report = {"engine": ocr_engine.casefold(), "language": normalized_language,
                          "status": "completed", "pages": len(ocr_page_elements),
                          "requested_pages": sorted(ocr_target_pages),
                          "adapter": "configured-local-command"}
        elif classification.route == "scan":
            ocr_report = {"engine": ocr_engine.casefold(), "language": normalized_language,
                          "status": "unavailable", "reason": "configured OCR engine is not installed"}
        elif "scan" in page_routes:
            ocr_report = {"engine": ocr_engine.casefold(), "language": normalized_language,
                          "status": "unavailable",
                          "reason": "mixed documents require page-aware OCR dispatch"}
        else:
            ocr_report = {"status": "skipped", "reason": "digital text route"}
        if dimensions and not ocr_page_elements:
            width, height = dimensions
            elements = [{"id": "image-1", "type": "image", "text": "",
                         "box": [0, 0, width, height]}]
        model_page_elements = ocr_page_elements or None
        model_elements = elements
        if ocr_target_pages and elements and any(route == "digital" for route in page_routes):
            # The bounded digital extractor has no page-aware operator mapping yet.
            # Preserve its text on the first digital page while keeping OCR output
            # restricted to the pages classified as scans.
            model_page_elements = dict(ocr_page_elements)
            digital_pages = [index + 1 for index, route in enumerate(page_routes) if route == "digital"]
            if digital_pages:
                model_page_elements[digital_pages[0]] = elements
            model_elements = []
        model = page_model(document_id, filename, classification, len(raw), pages_total,
                           model_elements, dimensions, model_page_elements, page_routes)
        model["processing"] = {
            "route": classification.route,
            "page_routes": page_routes,
            "ocr": ocr_report,
        }
        object_key = f"ingestions/{document_id}/{filename.replace('\\', '/') .split('/')[-1]}"
        store.put(object_key, raw)
        with engine.begin() as connection:
            connection.execute(IngestionDocument.__table__.insert().values(
                id=document_id, filename=filename, media_type=classification.media_type,
                size_bytes=len(raw), pages_total=pages_total, pages_processed=0,
                route=classification.route, status="queued",
                object_key=object_key, page_model_json=json.dumps(model), markdown=markdown_for(model)))
        return {"id": document_id, "filename": filename, "route": classification.route,
                "status": "queued", "pages_total": pages_total, "pages_processed": 0,
                "processing": model["processing"],
                "result_url": f"/api/ingestions/{document_id}/result"}

    @app.post("/api/assets", status_code=201, tags=["templates"])
    async def upload_asset(request: Request, filename: str):
        authenticated_user(request, scope="render")
        raw = await request.body()
        if not filename or len(filename) > 255 or not raw:
            raise HTTPException(status_code=422, detail="image filename and non-empty body are required")
        media_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
        signatures = {
            "image/png": raw.startswith(b"\x89PNG\r\n\x1a\n"),
            "image/jpeg": raw.startswith(b"\xff\xd8\xff"),
            "image/gif": raw.startswith((b"GIF87a", b"GIF89a")),
            "image/webp": raw.startswith(b"RIFF") and raw[8:12] == b"WEBP",
            "image/svg+xml": b"<svg" in raw[:2048].lower(),
        }
        if media_type not in signatures or not signatures[media_type]:
            raise HTTPException(status_code=415, detail="supported image bytes and image content type are required")
        if media_type == "image/svg+xml":
            try:
                validate_svg_markup(raw)
            except ValueError as exc:
                raise HTTPException(status_code=415, detail=str(exc)) from None
        if len(raw) > settings.max_object_bytes:
            raise HTTPException(status_code=413, detail="asset exceeds the configured size limit")
        dimensions = image_dimensions(raw, media_type)
        if dimensions and dimensions[0] * dimensions[1] > settings.max_image_pixels:
            raise HTTPException(status_code=413, detail="asset exceeds the configured pixel limit")
        try:
            scan_upload(raw, settings.virus_scan_command, settings.virus_scan_timeout_seconds)
        except UploadScanError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        extension = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif",
                     "image/webp": "webp", "image/svg+xml": "svg"}[media_type]
        asset_id = uuid4().hex
        object_key = f"assets/{asset_id}.{extension}"
        store.put(object_key, raw)
        return {"id": asset_id, "media_type": media_type, "url": f"/api/assets/{asset_id}.{extension}"}

    @app.get("/api/assets/{asset_name}", tags=["templates"])
    def asset(asset_name: str, request: Request):
        authenticated_user(request, scope="read")
        if "/" in asset_name or not asset_name.startswith(tuple("0123456789abcdef")):
            raise HTTPException(status_code=404, detail="Asset not found")
        suffixes = {".png": "image/png", ".jpg": "image/jpeg", ".gif": "image/gif",
                    ".webp": "image/webp", ".svg": "image/svg+xml"}
        media_type = next((value for suffix, value in suffixes.items() if asset_name.endswith(suffix)), None)
        if media_type is None:
            raise HTTPException(status_code=404, detail="Asset not found")
        try:
            raw = store.get(f"assets/{asset_name}")
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Asset not found") from None
        return Response(content=raw, media_type=media_type, headers={"Content-Disposition": "inline"})

    @app.get("/api/ingestions", tags=["ingestion"])
    def ingestions():
        with engine.connect() as connection:
            rows = connection.execute(select(IngestionDocument.id, IngestionDocument.filename,
                                             IngestionDocument.media_type, IngestionDocument.size_bytes,
                                             IngestionDocument.pages_total, IngestionDocument.pages_processed,
                                             IngestionDocument.route, IngestionDocument.status,
                                             IngestionDocument.created_at).order_by(
                                                 IngestionDocument.created_at.desc())).mappings().all()
            return {"items": [{"id": row["id"], "filename": row["filename"], "media_type": row["media_type"],
                               "size_bytes": row["size_bytes"], "pages_total": row["pages_total"],
                               "pages_processed": row["pages_processed"], "route": row["route"], "status": row["status"],
                               "created_at": row["created_at"].isoformat() if row["created_at"] else None} for row in rows]}

    @app.get("/api/ingestions/{document_id}", tags=["ingestion"])
    def ingestion(document_id: str):
        with engine.connect() as connection:
            row = connection.execute(select(IngestionDocument.id, IngestionDocument.filename,
                                           IngestionDocument.media_type, IngestionDocument.size_bytes,
                                           IngestionDocument.pages_total, IngestionDocument.pages_processed,
                                           IngestionDocument.route, IngestionDocument.status).where(
                                               IngestionDocument.id == document_id)).mappings().one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Ingestion not found")
            return {"id": row["id"], "filename": row["filename"], "media_type": row["media_type"],
                    "size_bytes": row["size_bytes"], "pages_total": row["pages_total"],
                    "pages_processed": row["pages_processed"], "route": row["route"], "status": row["status"]}

    @app.get("/api/ingestions/{document_id}/source", tags=["ingestion"])
    def ingestion_source(document_id: str, request: Request):
        authenticated_user(request, scope="read")
        with engine.connect() as connection:
            row = connection.execute(select(IngestionDocument.object_key,
                                            IngestionDocument.media_type).where(
                                                IngestionDocument.id == document_id)).mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Ingestion not found")
        try:
            raw = store.get(row["object_key"])
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Source object not found") from None
        return Response(content=raw, media_type=row["media_type"],
                        headers={"Content-Disposition": "inline"})

    @app.get("/api/ingestions/{document_id}/result", tags=["ingestion"])
    def ingestion_result(document_id: str):
        with engine.connect() as connection:
            row = connection.execute(select(IngestionDocument.id, IngestionDocument.status,
                                           IngestionDocument.page_model_json, IngestionDocument.markdown).where(
                                               IngestionDocument.id == document_id)).mappings().one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Ingestion not found")
            return {"id": row["id"], "status": row["status"], "page_model": json.loads(row["page_model_json"]),
                    "markdown": row["markdown"], "extraction": None,
                    "pending": "OCR/layout extraction worker is not implemented"}

    @app.post("/api/ingestions/{document_id}/extract", tags=["extraction"])
    def extract_ingestion(document_id: str, payload: dict, request: Request):
        authenticated_user(request, scope="read")
        with engine.connect() as connection:
            row = connection.execute(select(IngestionDocument.page_model_json).where(
                IngestionDocument.id == document_id)).mappings().one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Ingestion not found")
        schema_id = payload.get("schema_id")
        schema_payload = payload.get("schema") or BUNDLED_SCHEMAS.get(schema_id)
        if not isinstance(schema_payload, dict):
            raise HTTPException(status_code=422, detail="schema or schema_id is required")
        if payload.get("async") is True:
            job_id = uuid4().hex
            job_payload = {"document_id": document_id, "schema": schema_payload,
                           "locale": str(payload.get("locale", "en")),
                           "engine_id": str(payload.get("engine_id", "local-label-extractor")),
                           "calibration_profile": calibration_for(payload),
                           "result_id": uuid4().hex}
            with engine.begin() as connection:
                connection.execute(IngestionDocument.__table__.update().where(
                    IngestionDocument.id == document_id).values(status="running", pages_processed=0))
                enqueue(connection, "extraction", job_payload, job_id)
            return JSONResponse({"id": job_id, "status": "queued", "status_url": f"/api/jobs/{job_id}",
                                 "document_id": document_id}, status_code=202)
        try:
            page_model_payload = json.loads(row["page_model_json"])
            result = extract_with_progress(document_id, page_model_payload, schema_payload,
                                           str(payload.get("locale", "en")),
                                           str(payload.get("engine_id", "local-label-extractor")),
                                           calibration_for(payload))
        except (ExtractionSchemaError, ExtractionEngineError, CalibrationProfileError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        result = persist_extraction_result(document_id, schema_payload, result, page_model_payload)
        mark_ingestion_processed(document_id)
        return result

    @app.get("/api/extractions/{result_id}", tags=["extraction"])
    def extraction_result(result_id: str):
        with engine.connect() as connection:
            row = connection.execute(select(ExtractionResultRecord.id, ExtractionResultRecord.result_json,
                                            ExtractionResultRecord.status, ExtractionResultRecord.revision).where(
                                                ExtractionResultRecord.id == result_id)).mappings().one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Extraction result not found")
            corrections = connection.execute(select(ExtractionCorrection.field_name,
                                                    ExtractionCorrection.original_value,
                                                    ExtractionCorrection.new_value,
                                                    ExtractionCorrection.actor,
                                                    ExtractionCorrection.created_at).where(
                                                        ExtractionCorrection.result_id == result_id).order_by(
                                                        ExtractionCorrection.created_at)).mappings().all()
            review_events = connection.execute(select(ExtractionReviewEvent.from_status,
                                                       ExtractionReviewEvent.to_status,
                                                       ExtractionReviewEvent.actor,
                                                       ExtractionReviewEvent.created_at).where(
                                                           ExtractionReviewEvent.result_id == result_id).order_by(
                                                               ExtractionReviewEvent.created_at)).mappings().all()
        result = json.loads(row["result_json"])
        result.update({"result_id": row["id"], "status": row["status"], "revision": row["revision"],
                      "corrections": [{"field": item["field_name"], "original_value": item["original_value"],
                                       "new_value": item["new_value"], "actor": item["actor"],
                                       "created_at": item["created_at"].isoformat() if item["created_at"] else None}
                                      for item in corrections],
                      "review_events": [{"from_status": item["from_status"], "to_status": item["to_status"],
                                         "actor": item["actor"],
                                         "created_at": item["created_at"].isoformat() if item["created_at"] else None}
                                        for item in review_events]})
        return result

    @app.patch("/api/extractions/{result_id}/fields/{field_name}", tags=["review"])
    def correct_extraction(result_id: str, field_name: str, payload: dict, request: Request):
        user = authenticated_user(request, csrf=True)
        expected_revision = payload.get("expected_revision")
        if not isinstance(expected_revision, int):
            raise HTTPException(status_code=422, detail="expected_revision is required")
        with engine.begin() as connection:
            row = connection.execute(select(ExtractionResultRecord.result_json,
                                            ExtractionResultRecord.status,
                                            ExtractionResultRecord.revision).where(
                                                ExtractionResultRecord.id == result_id)).mappings().one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Extraction result not found")
            if row["revision"] != expected_revision:
                raise HTTPException(status_code=409, detail="Extraction result revision changed")
            result = json.loads(row["result_json"])
            field = result.get("fields", {}).get(field_name)
            if not isinstance(field, dict):
                raise HTTPException(status_code=404, detail="Extraction field not found")
            original_field_json = json.dumps(field)
            old_value = field.get("normalized_value")
            new_value = payload.get("value")
            if "source" in payload:
                source = payload.get("source")
                if source is not None:
                    if not isinstance(source, dict):
                        raise HTTPException(status_code=422, detail="source must be an object")
                    box = source.get("box")
                    if box is not None and (not isinstance(box, list) or len(box) != 4 or
                                            any(not isinstance(value, (int, float)) for value in box)):
                        raise HTTPException(status_code=422, detail="source.box must contain four numeric coordinates")
                field["source"] = source
            field["normalized_value"] = new_value
            field["absent"] = bool(payload.get("absent", False))
            field["validation"] = []
            field["review_status"] = "corrected"
            result["status"] = "in_review"
            new_field_json = json.dumps(field)
            revision = expected_revision + 1
            connection.execute(ExtractionResultRecord.__table__.update().where(
                ExtractionResultRecord.id == result_id).values(
                    result_json=json.dumps(result), status="in_review", revision=revision,
                    updated_at=func.now()))
            record_review_event(connection, result_id, row["status"], "in_review", str(user["email"]))
            connection.execute(ExtractionCorrection.__table__.insert().values(
                id=uuid4().hex, result_id=result_id, field_name=field_name,
                original_value=json.dumps(old_value), new_value=json.dumps(new_value),
                original_field_json=original_field_json, new_field_json=new_field_json,
                actor=str(user["email"]), created_at=datetime.now(UTC)))
        return {"result_id": result_id, "field": field_name, "revision": revision, "status": "in_review"}

    @app.post("/api/extractions/{result_id}/fields", tags=["review"])
    def add_extraction_field(result_id: str, payload: dict, request: Request):
        user = authenticated_user(request, csrf=True)
        expected_revision = payload.get("expected_revision")
        field_name = str(payload.get("field") or payload.get("field_name") or "").strip()
        if not isinstance(expected_revision, int) or not field_name:
            raise HTTPException(status_code=422, detail="field and expected_revision are required")
        source = payload.get("source")
        if source is not None:
            if not isinstance(source, dict):
                raise HTTPException(status_code=422, detail="source must be an object")
            box = source.get("box")
            if box is not None and (not isinstance(box, list) or len(box) != 4 or
                                    any(not isinstance(value, (int, float)) for value in box)):
                raise HTTPException(status_code=422, detail="source.box must contain four numeric coordinates")
        with engine.begin() as connection:
            row = connection.execute(select(ExtractionResultRecord.result_json,
                                            ExtractionResultRecord.status,
                                            ExtractionResultRecord.revision).where(
                                                ExtractionResultRecord.id == result_id)).mappings().one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Extraction result not found")
            if row["revision"] != expected_revision:
                raise HTTPException(status_code=409, detail="Extraction result revision changed")
            result = json.loads(row["result_json"])
            fields = result.setdefault("fields", {})
            if field_name in fields:
                raise HTTPException(status_code=409, detail="Extraction field already exists")
            value = payload.get("value")
            new_field = {"original_value": None, "normalized_value": value,
                         "confidence": 1.0, "source": source, "validation": [],
                         "review_status": "corrected", "absent": bool(payload.get("absent", False))}
            fields[field_name] = new_field
            result["status"] = "in_review"
            revision = expected_revision + 1
            connection.execute(ExtractionResultRecord.__table__.update().where(
                ExtractionResultRecord.id == result_id).values(
                    result_json=json.dumps(result), status="in_review", revision=revision,
                    updated_at=func.now()))
            record_review_event(connection, result_id, row["status"], "in_review", str(user["email"]))
            connection.execute(ExtractionCorrection.__table__.insert().values(
                id=uuid4().hex, result_id=result_id, field_name=field_name,
                original_value=json.dumps(None), new_value=json.dumps(value), actor=str(user["email"]),
                original_field_json=None, new_field_json=json.dumps(new_field),
                created_at=datetime.now(UTC)))
        return {"result_id": result_id, "field": field_name, "revision": revision, "status": "in_review"}

    @app.post("/api/extractions/{result_id}/undo", tags=["review"])
    def undo_extraction_correction(result_id: str, payload: dict, request: Request):
        user = authenticated_user(request, csrf=True)
        expected_revision = payload.get("expected_revision")
        if not isinstance(expected_revision, int):
            raise HTTPException(status_code=422, detail="expected_revision is required")
        with engine.begin() as connection:
            row = connection.execute(select(ExtractionResultRecord.result_json,
                                            ExtractionResultRecord.status,
                                            ExtractionResultRecord.revision).where(
                                                ExtractionResultRecord.id == result_id)).mappings().one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="Extraction result not found")
            if row["revision"] != expected_revision:
                raise HTTPException(status_code=409, detail="Extraction result revision changed")
            correction = connection.execute(select(ExtractionCorrection.field_name,
                                                    ExtractionCorrection.original_value,
                                                    ExtractionCorrection.new_value,
                                                    ExtractionCorrection.original_field_json,
                                                    ExtractionCorrection.new_field_json).where(
                                                        ExtractionCorrection.result_id == result_id).order_by(
                                                            ExtractionCorrection.created_at.desc())).mappings().first()
            if correction is None:
                raise HTTPException(status_code=409, detail="No correction is available to undo")
            result = json.loads(row["result_json"])
            field = result.get("fields", {}).get(correction["field_name"])
            if not isinstance(field, dict):
                raise HTTPException(status_code=409, detail="Correction field is no longer present")
            current_value = field.get("normalized_value")
            restored = json.loads(correction["original_value"]) if correction["original_value"] is not None else None
            current_field_json = json.dumps(field)
            if correction["original_field_json"] is not None:
                restored_field = json.loads(correction["original_field_json"])
                if not isinstance(restored_field, dict):
                    raise HTTPException(status_code=409, detail="Correction snapshot is invalid")
                field.clear()
                field.update(restored_field)
            else:
                field["normalized_value"] = restored
                field["absent"] = False
                field["review_status"] = "corrected"
                field["validation"] = []
            restored_field_json = json.dumps(field)
            result["status"] = "in_review"
            revision = expected_revision + 1
            connection.execute(ExtractionResultRecord.__table__.update().where(
                ExtractionResultRecord.id == result_id).values(
                    result_json=json.dumps(result), status="in_review", revision=revision,
                    updated_at=func.now()))
            record_review_event(connection, result_id, row["status"], "in_review", str(user["email"]))
            connection.execute(ExtractionCorrection.__table__.insert().values(
                id=uuid4().hex, result_id=result_id, field_name=correction["field_name"],
                original_value=json.dumps(current_value), new_value=json.dumps(restored), actor=str(user["email"]),
                original_field_json=current_field_json, new_field_json=restored_field_json,
                created_at=datetime.now(UTC)))
        return {"result_id": result_id, "field": correction["field_name"], "revision": revision, "status": "in_review"}

    @app.post("/api/extractions/{result_id}/review", tags=["review"])
    def review_extraction(result_id: str, payload: dict, request: Request):
        user = authenticated_user(request, csrf=True)
        state = payload.get("status")
        if state not in {"new", "in_review", "approved", "rejected"}:
            raise HTTPException(status_code=422, detail="status must be new, in_review, approved, or rejected")
        with engine.begin() as connection:
            row = connection.execute(select(ExtractionResultRecord.id, ExtractionResultRecord.status).where(
                ExtractionResultRecord.id == result_id)).first()
            if row is None:
                raise HTTPException(status_code=404, detail="Extraction result not found")
            connection.execute(ExtractionResultRecord.__table__.update().where(
                ExtractionResultRecord.id == result_id).values(status=state, updated_at=func.now()))
            record_review_event(connection, result_id, row.status, state, str(user["email"]))
        return {"result_id": result_id, "status": state}

    @app.get("/api/extractions/{result_id}/corrections.csv", tags=["review"])
    def extraction_corrections_csv(result_id: str):
        with engine.connect() as connection:
            if not connection.execute(select(ExtractionResultRecord.id).where(
                    ExtractionResultRecord.id == result_id)).first():
                raise HTTPException(status_code=404, detail="Extraction result not found")
            rows = connection.execute(select(ExtractionCorrection.field_name,
                                             ExtractionCorrection.original_value,
                                             ExtractionCorrection.new_value,
                                             ExtractionCorrection.actor,
                                             ExtractionCorrection.created_at).where(
                                                 ExtractionCorrection.result_id == result_id).order_by(
                                                     ExtractionCorrection.created_at)).mappings().all()
        lines = ["field,original_value,new_value,actor,created_at"]
        for row in rows:
            values = [row["field_name"], row["original_value"], row["new_value"], row["actor"],
                      row["created_at"].isoformat() if row["created_at"] else ""]
            lines.append(",".join('"' + str(value or "").replace('"', '""') + '"' for value in values))
        return Response("\n".join(lines) + "\n", media_type="text/csv")

    @app.get("/api/extractions/{result_id}/export.json", tags=["extraction"])
    def extraction_export_json(result_id: str):
        with engine.connect() as connection:
            row = connection.execute(select(ExtractionResultRecord.id, ExtractionResultRecord.result_json,
                                            ExtractionResultRecord.status, ExtractionResultRecord.revision).where(
                                                ExtractionResultRecord.id == result_id)).mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Extraction result not found")
        result = json.loads(row["result_json"])
        result.update({"result_id": row["id"], "status": row["status"], "revision": row["revision"]})
        return result

    @app.get("/api/extractions/{result_id}/export.csv", tags=["extraction"])
    def extraction_export_csv(result_id: str):
        with engine.connect() as connection:
            row = connection.execute(select(ExtractionResultRecord.result_json, ExtractionResultRecord.status).where(
                ExtractionResultRecord.id == result_id)).mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Extraction result not found")
        result = json.loads(row["result_json"])
        output = StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["field", "original_value", "normalized_value", "confidence", "review_status",
                         "source_page", "source_box", "validation", "result_status"])
        for name, field in result.get("fields", {}).items():
            source = field.get("source") or {}
            writer.writerow([name, field.get("original_value"), field.get("normalized_value"),
                             field.get("confidence"), field.get("review_status"), source.get("page_number"),
                             json.dumps(source.get("box")) if source.get("box") is not None else "",
                             json.dumps(field.get("validation", []), ensure_ascii=False), row["status"]])
        return Response(output.getvalue(), media_type="text/csv")

    @app.get("/api/extractions/{result_id}/export.xlsx", tags=["extraction"])
    def extraction_export_xlsx(result_id: str):
        with engine.connect() as connection:
            row = connection.execute(select(ExtractionResultRecord.result_json,
                                            ExtractionResultRecord.status).where(
                                                ExtractionResultRecord.id == result_id)).mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Extraction result not found")
        workbook = extraction_xlsx(json.loads(row["result_json"]), row["status"])
        return Response(workbook,
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition": f'attachment; filename="{result_id}.xlsx"'})

    @app.post("/api/extractions/{result_id}/webhook", tags=["extraction"])
    def extraction_webhook(result_id: str, payload: dict, request: Request):
        authenticated_user(request, scope="read")
        target = payload.get("url")
        if not isinstance(target, str) or len(target) > 2048:
            raise HTTPException(status_code=422, detail="url is required and must be at most 2048 characters")
        parsed = urllib.parse.urlsplit(target)
        allowed_hosts = {str(host).casefold() for host in settings.webhook_allowed_hosts}
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise HTTPException(status_code=422, detail="url must be an HTTP(S) URL without credentials")
        if parsed.hostname.casefold() not in allowed_hosts:
            raise HTTPException(status_code=403, detail="webhook host is not allow-listed")
        with engine.connect() as connection:
            row = connection.execute(select(ExtractionResultRecord.id,
                                            ExtractionResultRecord.result_json,
                                            ExtractionResultRecord.status,
                                            ExtractionResultRecord.revision).where(
                                                ExtractionResultRecord.id == result_id)).mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Extraction result not found")
        body = json.dumps({"result_id": row["id"], "status": row["status"],
                           "revision": row["revision"], "result": json.loads(row["result_json"])},
                          ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        secret = payload.get("secret")
        if secret is not None:
            if not isinstance(secret, str) or len(secret) > 512:
                raise HTTPException(status_code=422, detail="secret must be a string of at most 512 characters")
            signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
            headers["X-DocPlatform-Signature"] = f"sha256={signature}"
        try:
            response = urllib.request.urlopen(urllib.request.Request(target, data=body, headers=headers,
                                                                      method="POST"),
                                              timeout=settings.webhook_timeout_seconds)
            with response:
                status_code = int(response.status)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
            raise HTTPException(status_code=502, detail=f"webhook delivery failed: {str(exc)[:200]}") from None
        return {"result_id": result_id, "delivered": 200 <= status_code < 300, "status_code": status_code}

    @app.post("/api/templates/{template_id}/render-approved", tags=["rendering"])
    def render_approved(template_id: str, payload: dict, request: Request):
        authenticated_user(request, scope="render")
        result_id = payload.get("extraction_id")
        if not isinstance(result_id, str):
            raise HTTPException(status_code=422, detail="extraction_id is required")
        with engine.connect() as connection:
            extraction = connection.execute(select(ExtractionResultRecord.status,
                                                   ExtractionResultRecord.result_json).where(
                                                       ExtractionResultRecord.id == result_id)).mappings().one_or_none()
            if extraction is None:
                raise HTTPException(status_code=404, detail="Extraction result not found")
            if extraction["status"] != "approved":
                raise HTTPException(status_code=409, detail="Only approved extraction results can feed generation")
            _, version, definition = template_definition(connection, template_id,
                                                        payload.get("version_id"), bool(payload.get("draft")))
            definition = expand_components(connection, definition)
        extracted = json.loads(extraction["result_json"])
        data = {name: field.get("normalized_value") for name, field in extracted.get("fields", {}).items()}
        try:
            result = run_isolated("render", {"definition": render_definition_for_worker(definition), "data": data,
                                              "locale": payload.get("locale"),
                                              "missing_policy": payload.get("missing_policy")},
                                  timeout_seconds=settings.job_timeout_seconds,
                                  cpu_seconds=settings.job_cpu_seconds,
                                  memory_bytes=settings.job_memory_bytes,
                                  max_output_bytes=settings.job_max_output_bytes)
        except (TemplateDataError, TemplateEvaluationLimitError, ValueError, WorkerExecutionError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        result.update({"template_id": template_id, "version_id": version["id"] if version else None,
                      "extraction_id": result_id, "data": data})
        return result

    @app.get("/api/extraction-schemas", tags=["extraction"])
    def extraction_schemas():
        return {"items": [{"id": schema["id"], "name": schema["name"],
                           "schema_version": schema["schema_version"],
                           "sample_url": f"/api/extraction-schemas/{schema['id']}/sample"}
                          for schema in BUNDLED_SCHEMAS.values()]}

    @app.get("/api/extraction-schemas/{schema_id}/sample", tags=["extraction"])
    def extraction_schema_sample(schema_id: str):
        schema_payload = BUNDLED_SCHEMAS.get(schema_id)
        sample = BUNDLED_SAMPLES.get(schema_id)
        if schema_payload is None or sample is None:
            raise HTTPException(status_code=404, detail="Extraction schema sample not found")
        return {"schema": schema_payload, "sample": sample}

    @app.get("/api/extraction-schemas/{schema_id}", tags=["extraction"])
    def extraction_schema(schema_id: str):
        schema_payload = BUNDLED_SCHEMAS.get(schema_id)
        if schema_payload is None:
            raise HTTPException(status_code=404, detail="Extraction schema not found")
        return schema_payload

    @app.get("/api/extraction-schemas/{schema_id}/json-schema", tags=["extraction"])
    def extraction_json_schema(schema_id: str):
        schema_payload = BUNDLED_SCHEMAS.get(schema_id)
        if schema_payload is None:
            raise HTTPException(status_code=404, detail="Extraction schema not found")
        return schema_to_json_schema(schema_payload)

    @app.post("/api/extraction-schemas/validate", tags=["extraction"])
    def validate_extraction_schema(payload: dict):
        schema_payload = payload.get("schema")
        if not isinstance(schema_payload, dict):
            raise HTTPException(status_code=422, detail="schema is required")
        try:
            validate_schema(schema_payload)
        except ExtractionSchemaError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        return {"valid": True, "schema_id": schema_payload.get("id"),
                "schema_version": schema_payload.get("schema_version", 1),
                "json_schema": schema_to_json_schema(schema_payload)}

    @app.get("/api/extraction-engines", tags=["extraction"])
    def extraction_engines():
        return {"contract": "extraction-engine-v1", "items": [descriptor.as_dict()
                                                                for descriptor in engine_descriptors()]}

    @app.post("/api/extractions/local", tags=["extraction"])
    def local_extraction(payload: dict, request: Request):
        authenticated_user(request, scope="read")
        page_model_payload = payload.get("page_model")
        schema_id = payload.get("schema_id")
        schema_payload = payload.get("schema") or BUNDLED_SCHEMAS.get(schema_id)
        if not isinstance(page_model_payload, dict) or not isinstance(schema_payload, dict):
            raise HTTPException(status_code=422, detail="page_model and schema or schema_id are required")
        try:
            result = extract_with_engine(str(payload.get("engine_id", "local-label-extractor")),
                                         page_model_payload, schema_payload, str(payload.get("locale", "en")))
            if calibration_for(payload) is not None:
                result = apply_profile(result, calibration_for(payload),
                                       str(schema_payload.get("id") or "inline"))
            result["page_model"] = page_model_payload
            return result
        except (ExtractionSchemaError, ExtractionEngineError, CalibrationProfileError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None

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

    @app.post("/api/templates/{template_id}/sample-data", tags=["templates"])
    def sample_data(template_id: str, payload: dict | None = None):
        with engine.connect() as connection:
            _, _, definition = template_definition(connection, template_id,
                                                    (payload or {}).get("version_id"),
                                                    bool((payload or {}).get("draft")))
        locale = str((payload or {}).get("locale") or definition.get("locale", "en"))
        return {"template_id": template_id, "locale": locale,
                "sample_data": generate_sample_data(definition, locale)}

    @app.post("/api/templates/{template_id}/render", tags=["rendering"])
    def render(template_id: str, payload: dict | None = None, request: Request = None):
        if request.headers.get("x-api-key"):
            authenticated_user(request, scope="render")
        payload = payload or {}
        with engine.connect() as connection:
            _, version, definition = template_definition(connection, template_id,
                                                        payload.get("version_id"), bool(payload.get("draft")))
            definition = expand_components(connection, definition)
        block_count = len(definition.get("blocks", [])) if isinstance(definition.get("blocks", []), list) else 0
        if payload.get("async") is True or block_count > settings.sync_render_max_blocks:
            job_id = uuid4().hex
            job_payload = {"template_id": template_id, "data": payload.get("data"),
                           "locale": payload.get("locale"), "missing_policy": payload.get("missing_policy"),
                           "version_id": payload.get("version_id"), "draft": bool(payload.get("draft"))}
            with engine.begin() as connection:
                enqueue(connection, "render", job_payload, job_id)
            return JSONResponse({"id": job_id, "status": "queued", "status_url": f"/api/jobs/{job_id}",
                                 "reason": "template exceeds synchronous block limit"}, status_code=202)
        try:
            result = run_isolated("render", {"definition": render_definition_for_worker(definition), "data": payload.get("data"),
                                              "locale": payload.get("locale"),
                                              "missing_policy": payload.get("missing_policy")},
                                  timeout_seconds=settings.job_timeout_seconds,
                                  cpu_seconds=settings.job_cpu_seconds,
                                  memory_bytes=settings.job_memory_bytes,
                                  max_output_bytes=settings.job_max_output_bytes)
        except TemplateDataError as exc:
            raise HTTPException(status_code=422, detail={"message": str(exc), "path": exc.path}) from None
        except TemplateEvaluationLimitError as exc:
            raise HTTPException(status_code=422, detail={"message": str(exc), "code": "evaluation_limit"}) from None
        except (ValueError, WorkerExecutionError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        result.update({"template_id": template_id, "version_id": version["id"] if version else None})
        return result

    @app.post("/api/templates/{template_id}/render-pdf", tags=["rendering"])
    def render_pdf(template_id: str, payload: dict | None = None, request: Request = None):
        if request.headers.get("x-api-key"):
            authenticated_user(request, scope="render")
        renderer, renderer_command, license_file = pdf_renderer_configuration()
        if not renderer_command:
            raise HTTPException(status_code=503, detail=f"designer PDF renderer '{renderer}' is not configured")
        payload = payload or {}
        with engine.connect() as connection:
            _, version, definition = template_definition(connection, template_id,
                                                        payload.get("version_id"), bool(payload.get("draft")))
            definition = expand_components(connection, definition)
        block_count = len(definition.get("blocks", [])) if isinstance(definition.get("blocks", []), list) else 0
        if block_count > settings.sync_pdf_render_max_blocks:
            raise HTTPException(status_code=413, detail="template exceeds the synchronous PDF render block limit")
        try:
            rendered = run_isolated("render", {"definition": render_definition_for_worker(definition),
                                                "data": payload.get("data"),
                                                "locale": payload.get("locale"),
                                                "missing_policy": payload.get("missing_policy")},
                                    timeout_seconds=settings.job_timeout_seconds,
                                    cpu_seconds=settings.job_cpu_seconds,
                                    memory_bytes=settings.job_memory_bytes,
                                    max_output_bytes=settings.job_max_output_bytes)
            pdf_result = run_isolated(
                "pdf-render", {"html": inline_stored_assets(rendered["artifact"]), "command": renderer_command,
                                "renderer": renderer, "license_file": license_file,
                                "timeout_seconds": settings.pdf_renderer_timeout_seconds,
                                "max_output_bytes": settings.max_object_bytes, "metadata": rendered["metadata"]},
                timeout_seconds=settings.pdf_renderer_timeout_seconds,
                cpu_seconds=settings.job_cpu_seconds,
                memory_bytes=settings.job_memory_bytes,
                max_output_bytes=settings.job_max_output_bytes)
            output = base64.b64decode(pdf_result["pdf_base64"], validate=True)
            editable_only = payload.get("comparison_mode") == "editable-only"
            if not editable_only:
                output = merge_page_background(definition, output)
            # Page numbers come from @page margin boxes in the rendered HTML (DD-429); no PDF overlay is added.
            output = add_toc_page_numbers(output, settings.max_object_bytes)
            has_locked_background = isinstance(definition.get("page"), dict) and bool(definition["page"].get("background_pdf"))
            report = {**pdf_result["report"], "output_bytes": len(output),
                      "locked_background": "omitted" if editable_only or not has_locked_background else "included"}
        except (TemplateDataError, TemplateEvaluationLimitError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        except (WorkerExecutionError, ValueError, PdfBackgroundError, PdfPageNumberError, PdfTocError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        report = {**report, "render_locale": rendered.get("locale")}
        return {"template_id": template_id, "version_id": version["id"] if version else None,
                "document_base64": encode_pdf(output), "report": report}

    @app.get("/", include_in_schema=False)
    def index():
        if not (frontend / "index.html").is_file():
            return JSONResponse({"detail": "Build the frontend before serving the application"}, status_code=503)
        return FileResponse(frontend / "index.html")

    if (frontend / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="assets")
    return app
