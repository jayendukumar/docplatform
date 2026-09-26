"""Persist reusable editor components."""
from alembic import op
import sqlalchemy as sa

revision = "0012_reusable_components"
down_revision = "0011_correction_snapshots"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reusable_components",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("definition_json", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("reusable_components")
