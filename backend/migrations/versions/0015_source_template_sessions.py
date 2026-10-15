"""Add approval-gated source-to-template sessions (E21)."""
import sqlalchemy as sa
from alembic import op

revision = "0015_source_template_sessions"
down_revision = "0014_template_edit_audit"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "source_template_sessions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("document_id", sa.String(64), nullable=True),
        sa.Column("owner_user_id", sa.String(64), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="disclosure"),
        sa.Column("disclosure_acknowledged", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("external_ai_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("interpretation_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("approved_snapshot_json", sa.Text(), nullable=True),
        sa.Column("template_id", sa.String(64), nullable=True),
        sa.Column("template_version_id", sa.String(80), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_source_template_sessions_document_id", "source_template_sessions", ["document_id"])
    op.create_index("ix_source_template_sessions_owner_user_id", "source_template_sessions", ["owner_user_id"])
    op.create_index("ix_source_template_sessions_template_id", "source_template_sessions", ["template_id"])
    op.create_table(
        "source_template_corrections",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("item_id", sa.String(100), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("before_json", sa.Text(), nullable=False),
        sa.Column("after_json", sa.Text(), nullable=False),
        sa.Column("actor", sa.String(200), nullable=False, server_default="local"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_source_template_corrections_session_id", "source_template_corrections", ["session_id"])


def downgrade():
    op.drop_index("ix_source_template_corrections_session_id", table_name="source_template_corrections")
    op.drop_table("source_template_corrections")
    op.drop_index("ix_source_template_sessions_template_id", table_name="source_template_sessions")
    op.drop_index("ix_source_template_sessions_owner_user_id", table_name="source_template_sessions")
    op.drop_index("ix_source_template_sessions_document_id", table_name="source_template_sessions")
    op.drop_table("source_template_sessions")
