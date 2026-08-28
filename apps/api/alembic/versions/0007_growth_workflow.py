"""add product ownership and durable opportunity drafts"""

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "products",
        sa.Column("is_owned", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("products", "is_owned", server_default=None)
    op.add_column("xiaohongshu_opportunities", sa.Column("draft_body", sa.Text()))
    op.add_column(
        "xiaohongshu_opportunities", sa.Column("draft_status", sa.String(30))
    )
    op.add_column(
        "xiaohongshu_opportunities",
        sa.Column("draft_generated_at", sa.DateTime(timezone=True)),
    )


def downgrade():
    op.drop_column("xiaohongshu_opportunities", "draft_generated_at")
    op.drop_column("xiaohongshu_opportunities", "draft_status")
    op.drop_column("xiaohongshu_opportunities", "draft_body")
    op.drop_column("products", "is_owned")
