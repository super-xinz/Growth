"""add xiaohongshu content and opportunities"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "xiaohongshu_contents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dedupe_key", sa.String(300), nullable=False),
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("platform_content_id", sa.String(120), nullable=False),
        sa.Column("parent_content_id", sa.String(120)),
        sa.Column("xsec_token", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False, server_default=""),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("author_id", sa.String(120), nullable=False, server_default=""),
        sa.Column("author_name", sa.String(200), nullable=False, server_default=""),
        sa.Column("source_keyword", sa.String(300), nullable=False, server_default=""),
        sa.Column("raw_json", sa.JSON(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("dedupe_key"),
    )
    op.create_index("ix_xiaohongshu_contents_dedupe_key", "xiaohongshu_contents", ["dedupe_key"])
    op.create_index(
        "ix_xiaohongshu_contents_platform_content_id",
        "xiaohongshu_contents",
        ["platform_content_id"],
    )
    op.create_index(
        "ix_xiaohongshu_contents_parent_content_id",
        "xiaohongshu_contents",
        ["parent_content_id"],
    )
    op.create_table(
        "xiaohongshu_opportunities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "product_id",
            sa.String(36),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "content_id",
            sa.String(36),
            sa.ForeignKey("xiaohongshu_contents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("opportunity_score", sa.Float(), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("product_id", "content_id"),
    )
    op.create_index(
        "ix_xiaohongshu_opportunities_product_id",
        "xiaohongshu_opportunities",
        ["product_id"],
    )
    op.create_index(
        "ix_xiaohongshu_opportunities_content_id",
        "xiaohongshu_opportunities",
        ["content_id"],
    )


def downgrade():
    op.drop_index("ix_xiaohongshu_opportunities_content_id", table_name="xiaohongshu_opportunities")
    op.drop_index("ix_xiaohongshu_opportunities_product_id", table_name="xiaohongshu_opportunities")
    op.drop_table("xiaohongshu_opportunities")
    op.drop_index("ix_xiaohongshu_contents_parent_content_id", table_name="xiaohongshu_contents")
    op.drop_index("ix_xiaohongshu_contents_platform_content_id", table_name="xiaohongshu_contents")
    op.drop_index("ix_xiaohongshu_contents_dedupe_key", table_name="xiaohongshu_contents")
    op.drop_table("xiaohongshu_contents")
