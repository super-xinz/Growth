"""bind confirmations to account and track daily quota"""

import sqlalchemy as sa

from alembic import context, op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    if context.get_context().config.attributes.get("growthagent_metadata_bootstrap"):
        return
    op.add_column(
        "xiaohongshu_confirmations",
        sa.Column("account_id", sa.String(120), nullable=False, server_default=""),
    )
    op.alter_column("xiaohongshu_confirmations", "account_id", server_default=None)
    op.add_column(
        "xiaohongshu_opportunities",
        sa.Column("commented_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_xiaohongshu_opportunities_commented_at",
        "xiaohongshu_opportunities",
        ["commented_at"],
    )


def downgrade():
    op.drop_index(
        "ix_xiaohongshu_opportunities_commented_at",
        table_name="xiaohongshu_opportunities",
    )
    op.drop_column("xiaohongshu_opportunities", "commented_at")
    op.drop_column("xiaohongshu_confirmations", "account_id")
