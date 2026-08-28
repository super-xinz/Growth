"""remove the retired manual confirmation workflow"""

from alembic import op
import sqlalchemy as sa


revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("xiaohongshu_confirmations")


def downgrade():
    op.create_table(
        "xiaohongshu_confirmations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "opportunity_id",
            sa.String(36),
            sa.ForeignKey("xiaohongshu_opportunities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token", sa.String(120), nullable=False, unique=True),
        sa.Column("account_id", sa.String(120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("body_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
