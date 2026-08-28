"""Store encrypted local application settings."""

import sqlalchemy as sa

from alembic import context, op

revision = "0010"
down_revision = "0009"


def upgrade():
    if context.get_context().config.attributes.get("growthagent_metadata_bootstrap"):
        return
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value_encrypted", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade():
    op.drop_table("app_settings")
