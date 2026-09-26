"""Add durable extraction review-state events."""
from alembic import op
import sqlalchemy as sa

revision = "0010_review_events"
down_revision = "0009_ingestion_progress"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "extraction_review_events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("result_id", sa.String(64), nullable=False),
        sa.Column("from_status", sa.String(30), nullable=True),
        sa.Column("to_status", sa.String(30), nullable=False),
        sa.Column("actor", sa.String(200), nullable=False, server_default="local"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_extraction_review_events_result_id", "extraction_review_events", ["result_id"])


def downgrade():
    op.drop_index("ix_extraction_review_events_result_id", table_name="extraction_review_events")
    op.drop_table("extraction_review_events")
