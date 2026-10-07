"""Add organization workspaces, memberships and template ownership."""
from alembic import op
import sqlalchemy as sa

revision = "0013_organization_workspaces"
down_revision = "0012_reusable_components"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("account_type", sa.String(20), nullable=False, server_default="member"))
    op.add_column("users", sa.Column("status", sa.String(20), nullable=False, server_default="active"))
    op.add_column("users", sa.Column("entitlements_json", sa.Text(), nullable=False, server_default="{}"))
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("parent_id", sa.String(64), nullable=True),
        sa.Column("entitlements_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_organizations_parent_id", "organizations", ["parent_id"])
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("organization_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("entitlements_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_workspaces_organization_id", "workspaces", ["organization_id"])
    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("organization_id", sa.String(64), nullable=False),
        sa.Column("workspace_id", sa.String(64), nullable=True),
        sa.Column("role", sa.String(30), nullable=False, server_default="member"),
        sa.Column("entitlements_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_organization_memberships_user_id", "organization_memberships", ["user_id"])
    op.create_index("ix_organization_memberships_organization_id", "organization_memberships", ["organization_id"])
    op.create_index("ix_organization_memberships_workspace_id", "organization_memberships", ["workspace_id"])
    op.add_column("templates", sa.Column("owner_user_id", sa.String(64), nullable=True))
    op.add_column("templates", sa.Column("workspace_id", sa.String(64), nullable=True))
    op.add_column("templates", sa.Column("visibility", sa.String(20), nullable=False, server_default="workspace"))
    op.create_index("ix_templates_owner_user_id", "templates", ["owner_user_id"])
    op.create_index("ix_templates_workspace_id", "templates", ["workspace_id"])
    op.create_table(
        "template_aliases",
        sa.Column("duplicate_template_id", sa.String(64), primary_key=True),
        sa.Column("canonical_template_id", sa.String(64), nullable=False),
        sa.Column("definition_hash", sa.String(64), nullable=False),
        sa.Column("reason", sa.String(200), nullable=False, server_default="exact-definition-duplicate"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_template_aliases_canonical_template_id", "template_aliases", ["canonical_template_id"])
    op.create_index("ix_template_aliases_definition_hash", "template_aliases", ["definition_hash"])
    connection = op.get_bind()
    connection.execute(sa.text(
        "INSERT INTO organizations (id,name,slug,entitlements_json) "
        "VALUES ('org-good-docs','Good docs','good-docs', :entitlements) "
        "ON CONFLICT (id) DO NOTHING"), {"entitlements": '{"version":1,"features":{"catalog":true,"guest":true}}'})
    connection.execute(sa.text(
        "INSERT INTO workspaces (id,organization_id,name,slug,entitlements_json) "
        "VALUES ('workspace-good-docs','org-good-docs','Good docs','good-docs', :entitlements) "
        "ON CONFLICT (id) DO NOTHING"), {"entitlements": '{"version":1,"features":{"templates.read":true}}'})
    connection.execute(sa.text("UPDATE templates SET workspace_id='workspace-good-docs' WHERE workspace_id IS NULL"))


def downgrade():
    op.drop_index("ix_template_aliases_definition_hash", table_name="template_aliases")
    op.drop_index("ix_template_aliases_canonical_template_id", table_name="template_aliases")
    op.drop_table("template_aliases")
    op.drop_index("ix_templates_workspace_id", table_name="templates")
    op.drop_index("ix_templates_owner_user_id", table_name="templates")
    op.drop_column("templates", "visibility")
    op.drop_column("templates", "workspace_id")
    op.drop_column("templates", "owner_user_id")
    op.drop_index("ix_organization_memberships_workspace_id", table_name="organization_memberships")
    op.drop_index("ix_organization_memberships_organization_id", table_name="organization_memberships")
    op.drop_index("ix_organization_memberships_user_id", table_name="organization_memberships")
    op.drop_table("organization_memberships")
    op.drop_index("ix_workspaces_organization_id", table_name="workspaces")
    op.drop_table("workspaces")
    op.drop_index("ix_organizations_parent_id", table_name="organizations")
    op.drop_table("organizations")
    op.drop_column("users", "entitlements_json")
    op.drop_column("users", "status")
    op.drop_column("users", "account_type")
