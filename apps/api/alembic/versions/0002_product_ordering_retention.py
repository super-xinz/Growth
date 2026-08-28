"""add product ordering and retention fields"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("products", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("products", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("products", sa.Column("purge_after", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_products_sort_order", "products", ["sort_order"])
    op.create_index("ix_products_deleted_at", "products", ["deleted_at"])
    op.create_index("ix_products_purge_after", "products", ["purge_after"])
    op.execute("""
        WITH ordered AS (
          SELECT id, ROW_NUMBER() OVER (ORDER BY created_at ASC, id ASC) - 1 AS position
          FROM products
        )
        UPDATE products SET sort_order = ordered.position FROM ordered WHERE products.id = ordered.id
    """)
    op.alter_column("products", "sort_order", server_default=None)


def downgrade():
    op.drop_index("ix_products_purge_after", table_name="products")
    op.drop_index("ix_products_deleted_at", table_name="products")
    op.drop_index("ix_products_sort_order", table_name="products")
    op.drop_column("products", "purge_after")
    op.drop_column("products", "deleted_at")
    op.drop_column("products", "sort_order")
