"""Add durable extraction results and correction history."""
from alembic import op
import sqlalchemy as sa

revision = "0005_extraction_review"
down_revision = "0004_ingestion"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "extraction_results",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("document_id", sa.String(64), nullable=False),
        sa.Column("schema_id", sa.String(100), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="new"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_extraction_results_document_id", "extraction_results", ["document_id"])
    op.create_table(
        "extraction_corrections",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("result_id", sa.String(64), nullable=False),
        sa.Column("field_name", sa.String(200), nullable=False),
        sa.Column("original_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("actor", sa.String(200), nullable=False, server_default="local"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_extraction_corrections_result_id", "extraction_corrections", ["result_id"])


def downgrade():
    op.drop_index("ix_extraction_corrections_result_id", table_name="extraction_corrections")
    op.drop_table("extraction_corrections")
    op.drop_index("ix_extraction_results_document_id", table_name="extraction_results")
    op.drop_table("extraction_results")
