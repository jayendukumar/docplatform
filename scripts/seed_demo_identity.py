"""Seed repeatable fictitious organizations and demo login accounts."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.auth import hash_password  # noqa: E402
from app.config import load_settings  # noqa: E402
from app.database import create_database  # noqa: E402
from app.migrations import migrate  # noqa: E402
from app.models import Organization, OrganizationMembership, User, Workspace  # noqa: E402


ADMIN_PASSWORD = "OrgAdmin-2026!"
USER_PASSWORD = "DemoUser-2026!"

DEMO_ORGS = (
    ("demo-01-northstar-capital", "Northstar Capital"),
    ("demo-02-harbour-asset-management", "Harbour Asset Management"),
    ("demo-03-summit-insurance", "Summit Insurance"),
    ("demo-04-cedar-wealth", "Cedar Wealth Partners"),
    ("demo-05-pioneer-payments", "Pioneer Payments"),
    ("demo-06-atlas-healthcare", "Atlas Healthcare"),
    ("demo-07-orchard-retail", "Orchard Retail Group"),
    ("demo-08-blueprint-logistics", "Blueprint Logistics"),
    ("demo-09-lighthouse-energy", "Lighthouse Energy"),
    ("demo-10-meridian-public-sector", "Meridian Public Sector"),
)


def _id(prefix: str, key: str) -> str:
    return f"{prefix}-{uuid.uuid5(uuid.NAMESPACE_URL, 'good-docs-demo:' + key)}"


def _user(session: Session, email: str, role: str, account_type: str, password: str, features: list[str]) -> User:
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            id=_id("user", email), email=email, password_hash=hash_password(password),
            role=role, account_type=account_type, status="active",
            entitlements_json=json.dumps({"version": 1, "features": features}),
        )
        session.add(user)
    return user


def _membership(session: Session, user: User, organization: Organization, workspace_id: str | None,
                role: str, features: list[str]) -> None:
    statement = select(OrganizationMembership).where(
        OrganizationMembership.user_id == user.id,
        OrganizationMembership.organization_id == organization.id,
    )
    statement = statement.where(
        OrganizationMembership.workspace_id.is_(None)
        if workspace_id is None else OrganizationMembership.workspace_id == workspace_id
    )
    existing = session.scalar(statement)
    if existing is None:
        session.add(OrganizationMembership(
            id=_id("membership", f"{user.id}:{organization.id}:{workspace_id or 'all'}"),
            user_id=user.id, organization_id=organization.id, workspace_id=workspace_id,
            role=role, entitlements_json=json.dumps({"version": 1, "features": features}),
        ))


def seed_demo_identities(engine, *, apply: bool = True, admin_password: str = ADMIN_PASSWORD,
                         user_password: str = USER_PASSWORD) -> dict:
    """Create the demo identities and return a credential/count report.

    Existing users, organizations, workspaces and memberships are preserved. Passwords
    are only generated for newly created users.
    """
    session = Session(engine)
    report = {"organizations": [], "individuals": []}
    try:
        for index, (slug, name) in enumerate(DEMO_ORGS, start=1):
            organization = session.scalar(select(Organization).where(Organization.slug == slug))
            if organization is None:
                organization = Organization(
                    id=_id("org", slug), name=name, slug=slug,
                    entitlements_json=json.dumps({"version": 1, "features": ["catalog", "guest", "workspace.admin"]}),
                )
                session.add(organization)
                session.flush()

            workspace = session.scalar(select(Workspace).where(
                Workspace.organization_id == organization.id, Workspace.slug == "default"))
            if workspace is None:
                workspace = Workspace(
                    id=_id("workspace", slug), organization_id=organization.id,
                    name=f"{name} Workspace", slug="default",
                    entitlements_json=json.dumps({"version": 1, "features": ["templates.read", "templates.write"]}),
                )
                session.add(workspace)
                session.flush()

            admin_email = f"admin{index:02d}@gooddocs-demo.test"
            admin = _user(session, admin_email, "admin", "member", admin_password,
                          ["templates.read", "templates.write", "workspace.admin"])
            _membership(session, admin, organization, None, "admin", ["workspace.admin"])
            member_emails = []
            for member_index in range(1, 10):
                email = f"org{index:02d}-user{member_index:02d}@gooddocs-demo.test"
                member = _user(session, email, "editor", "member", user_password,
                               ["templates.read", "templates.write"])
                _membership(session, member, organization, workspace.id, "member",
                            ["templates.read", "templates.write"])
                member_emails.append(email)
            report["organizations"].append({"name": name, "slug": slug, "admin": admin_email,
                                             "members": member_emails})

        for index in range(1, 11):
            email = f"individual{index:02d}@gooddocs-demo.test"
            _user(session, email, "viewer", "individual", user_password,
                  ["templates.read", "templates.write"])
            report["individuals"].append(email)

        if apply:
            session.commit()
        else:
            session.rollback()
        return report
    finally:
        session.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="commit the seed; default is a dry run")
    parser.add_argument("--credentials-report", type=Path, help="write the explicit demo credential manifest")
    args = parser.parse_args()
    settings = load_settings()
    engine = create_database(settings)
    migrate(engine)
    report = seed_demo_identities(engine, apply=args.apply)
    if args.credentials_report:
        args.credentials_report.parent.mkdir(parents=True, exist_ok=True)
        args.credentials_report.write_text(json.dumps({
            **report, "admin_password": ADMIN_PASSWORD, "user_password": USER_PASSWORD,
        }, indent=2) + "\n", encoding="utf-8")
    action = "Applied" if args.apply else "Dry run"
    print(f"{action}: {len(report['organizations'])} organizations, "
          f"{sum(len(item['members']) + 1 for item in report['organizations'])} organization users, "
          f"{len(report['individuals'])} individual accounts")
    print("Organization admin login IDs: " + ", ".join(item["admin"] for item in report["organizations"]))
    print("Individual login IDs: " + ", ".join(report["individuals"]))
    print("Passwords: admins=OrgAdmin-2026!, members/individuals=DemoUser-2026!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
