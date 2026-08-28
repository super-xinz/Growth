"""clear generated product affiliation claims"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "UPDATE products SET disclosure_template = '' "
        "WHERE disclosure_template LIKE 'I''m building %'"
    )


def downgrade():
    pass
