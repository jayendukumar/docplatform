"""Persist complete before/after field snapshots for undo."""
import sqlalchemy as sa
from alembic import op

revision = "0011_correction_snapshots"
down_revision = "0010_review_events"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("extraction_corrections", sa.Column("original_field_json", sa.Text(), nullable=True))
    op.add_column("extraction_corrections", sa.Column("new_field_json", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("extraction_corrections", "new_field_json")
    op.drop_column("extraction_corrections", "original_field_json")
