import sys
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from seed_demo_identity import seed_demo_identities  # noqa: E402
from app.models import Base, Organization, OrganizationMembership, User, Workspace  # noqa: E402


def test_demo_identity_seed_is_complete_and_idempotent(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'identity.db'}")
    Base.metadata.create_all(engine)

    first = seed_demo_identities(engine)
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Organization)) == 10
        assert session.scalar(select(func.count()).select_from(Workspace)) == 10
        assert session.scalar(select(func.count()).select_from(User)) == 110
        assert session.scalar(select(func.count()).select_from(OrganizationMembership)) == 100
        assert session.scalar(select(func.count()).select_from(User).where(User.account_type == "individual")) == 10
        assert session.scalar(select(func.count()).select_from(OrganizationMembership).where(
            OrganizationMembership.role == "admin")) == 10
        admin = session.scalar(select(User).where(User.email == "admin01@gooddocs-demo.test"))
        original_hash = admin.password_hash

    second = seed_demo_identities(engine)
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(User)) == 110
        assert session.scalar(select(func.count()).select_from(OrganizationMembership)) == 100
        admin = session.scalar(select(User).where(User.email == "admin01@gooddocs-demo.test"))
        assert admin.password_hash == original_hash

    assert first == second
    engine.dispose()
