"""Record bounded ingestion page totals and progress."""
from alembic import op
import sqlalchemy as sa

revision = "0009_ingestion_progress"
down_revision = "0008_jobs"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ingestion_documents", sa.Column("pages_total", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("ingestion_documents", sa.Column("pages_processed", sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    op.drop_column("ingestion_documents", "pages_processed")
    op.drop_column("ingestion_documents", "pages_total")
