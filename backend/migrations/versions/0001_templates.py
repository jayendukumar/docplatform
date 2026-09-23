"""Initial template metadata, stored separately from document objects."""
from alembic import op
import sqlalchemy as sa

revision = "0001_templates"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("templates",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("object_key", sa.String(512), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))


def downgrade():
    op.drop_table("templates")
