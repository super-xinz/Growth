"""add guarded Xiaohongshu automation state"""

from alembic import op
import sqlalchemy as sa


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    product_columns = [
        sa.Column("auto_score_threshold", sa.Float(), nullable=False, server_default="0.75"),
        sa.Column("auto_risk_threshold", sa.Float(), nullable=False, server_default="0.35"),
        sa.Column("search_interval_hours", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("min_publish_interval_hours", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("keywords_per_run", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("details_per_keyword", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("automation_status", sa.String(30), nullable=False, server_default="IDLE"),
        sa.Column("automation_error", sa.Text()),
        sa.Column("automation_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_auto_search_at", sa.DateTime(timezone=True)),
        sa.Column("next_auto_search_at", sa.DateTime(timezone=True)),
        sa.Column("last_auto_publish_at", sa.DateTime(timezone=True)),
    ]
    for column in product_columns:
        op.add_column("products", column)
    op.create_index("ix_products_next_auto_search_at", "products", ["next_auto_search_at"])

    op.add_column(
        "xiaohongshu_opportunities",
        sa.Column("score_reason", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "xiaohongshu_opportunities",
        sa.Column("match_signals", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
    op.add_column("xiaohongshu_opportunities", sa.Column("publish_error", sa.Text()))
    op.add_column(
        "xiaohongshu_opportunities", sa.Column("evaluated_at", sa.DateTime(timezone=True))
    )

    # The current product definition is autonomous. Existing products are opted
    # in with conservative limits and an explicit truthful ownership phrase.
    op.execute(
        "UPDATE products SET autopublish_enabled = true, daily_reply_limit = LEAST(daily_reply_limit, 2), "
        "is_owned = true, disclosure_template = CASE WHEN disclosure_template = '' THEN '自家做的' ELSE disclosure_template END, "
        "next_auto_search_at = NOW() WHERE deleted_at IS NULL"
    )


def downgrade():
    for name in ("evaluated_at", "publish_error", "match_signals", "score_reason"):
        op.drop_column("xiaohongshu_opportunities", name)
    op.drop_index("ix_products_next_auto_search_at", table_name="products")
    for name in (
        "last_auto_publish_at",
        "next_auto_search_at",
        "last_auto_search_at",
        "automation_failures",
        "automation_error",
        "automation_status",
        "details_per_keyword",
        "keywords_per_run",
        "min_publish_interval_hours",
        "search_interval_hours",
        "auto_risk_threshold",
        "auto_score_threshold",
    ):
        op.drop_column("products", name)
