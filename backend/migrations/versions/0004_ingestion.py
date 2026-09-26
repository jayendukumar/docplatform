"""Add durable upload and page-model metadata for the ingestion contract."""
from alembic import op
import sqlalchemy as sa

revision = "0004_ingestion"
down_revision = "0003_governance"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ingestion_documents",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("media_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("route", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="queued"),
        sa.Column("object_key", sa.String(512), nullable=False, unique=True),
        sa.Column("page_model_json", sa.Text(), nullable=False),
        sa.Column("markdown", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("ingestion_documents")
