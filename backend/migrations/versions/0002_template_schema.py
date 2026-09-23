"""Give existing template metadata an explicit document schema version."""
from alembic import op
import sqlalchemy as sa

revision = "0002_template_schema"
down_revision = "0001_templates"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("templates", sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"))


def downgrade():
    op.drop_column("templates", "schema_version")
