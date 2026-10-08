"""Track template edit actors and timestamps."""
from alembic import op
import sqlalchemy as sa

revision = "0014_template_edit_audit"
down_revision = "0013_organization_workspaces"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("templates", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.add_column("templates", sa.Column("updated_by_user_id", sa.String(64), nullable=True))
    op.create_index("ix_templates_updated_at", "templates", ["updated_at"])
    op.create_index("ix_templates_updated_by_user_id", "templates", ["updated_by_user_id"])
    op.add_column("template_versions", sa.Column("created_by_user_id", sa.String(64), nullable=True))
    op.create_index("ix_template_versions_created_by_user_id", "template_versions", ["created_by_user_id"])
    connection = op.get_bind()
    connection.execute(sa.text("UPDATE templates SET updated_at = created_at WHERE updated_at IS NULL"))
    connection.execute(sa.text(
        "UPDATE templates SET updated_by_user_id = owner_user_id "
        "WHERE updated_by_user_id IS NULL AND owner_user_id IS NOT NULL"))
    connection.execute(sa.text(
        "UPDATE template_versions SET created_by_user_id = templates.owner_user_id "
        "FROM templates WHERE template_versions.template_id = templates.id "
        "AND template_versions.created_by_user_id IS NULL"))


def downgrade():
    op.drop_index("ix_template_versions_created_by_user_id", table_name="template_versions")
    op.drop_column("template_versions", "created_by_user_id")
    op.drop_index("ix_templates_updated_by_user_id", table_name="templates")
    op.drop_index("ix_templates_updated_at", table_name="templates")
    op.drop_column("templates", "updated_by_user_id")
    op.drop_column("templates", "updated_at")
