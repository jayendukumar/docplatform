"""Add immutable template versions and management metadata."""
from alembic import op
import sqlalchemy as sa

revision = "0003_governance"
down_revision = "0002_template_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("templates", sa.Column("folder", sa.String(200), nullable=False, server_default=""))
    op.add_column("templates", sa.Column("tags_json", sa.Text(), nullable=False, server_default="[]"))
    op.add_column("templates", sa.Column("published_version_id", sa.String(80), nullable=True))
    op.create_table(
        "template_versions",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("template_id", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("change_summary", sa.String(500), nullable=False, server_default=""),
        sa.Column("definition_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("template_id", "version", name="uq_template_version_number"),
    )
    op.create_index("ix_template_versions_template_id", "template_versions", ["template_id"])
    connection = op.get_bind()
    connection.execute(sa.text("""
        INSERT INTO template_versions
          (id, template_id, version, status, change_summary, definition_json)
        SELECT 'legacy-' || id || '-v1', id, 1, 'published', 'Imported foundation template',
               '{}' FROM templates
    """))
    connection.execute(sa.text("""
        UPDATE templates SET published_version_id = 'legacy-' || id || '-v1'
    """))


def downgrade():
    op.drop_index("ix_template_versions_template_id", table_name="template_versions")
    op.drop_table("template_versions")
    op.drop_column("templates", "published_version_id")
    op.drop_column("templates", "tags_json")
    op.drop_column("templates", "folder")
