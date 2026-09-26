"""Add hashed scoped API keys."""
from alembic import op
import sqlalchemy as sa

revision = "0007_api_keys"
down_revision = "0006_identity"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("prefix", sa.String(20), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("scopes_json", sa.Text(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_api_keys_prefix", "api_keys", ["prefix"])


def downgrade():
    op.drop_index("ix_api_keys_prefix", table_name="api_keys")
    op.drop_table("api_keys")
