"""add one-time xiaohongshu confirmations"""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "xiaohongshu_confirmations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "opportunity_id",
            sa.String(36),
            sa.ForeignKey("xiaohongshu_opportunities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token", sa.String(120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("body_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_xiaohongshu_confirmations_opportunity_id",
        "xiaohongshu_confirmations",
        ["opportunity_id"],
    )
    op.create_index(
        "ix_xiaohongshu_confirmations_token",
        "xiaohongshu_confirmations",
        ["token"],
        unique=True,
    )
    op.create_index(
        "ix_xiaohongshu_confirmations_expires_at",
        "xiaohongshu_confirmations",
        ["expires_at"],
    )


def downgrade():
    op.drop_index("ix_xiaohongshu_confirmations_expires_at", table_name="xiaohongshu_confirmations")
    op.drop_index("ix_xiaohongshu_confirmations_token", table_name="xiaohongshu_confirmations")
    op.drop_index(
        "ix_xiaohongshu_confirmations_opportunity_id",
        table_name="xiaohongshu_confirmations",
    )
    op.drop_table("xiaohongshu_confirmations")
