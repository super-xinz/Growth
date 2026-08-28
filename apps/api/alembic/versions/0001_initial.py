"""initial MVP tables"""

from alembic import context, op
from app.models import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    Base.metadata.create_all(bind=op.get_bind())
    context.get_context().config.attributes["growthagent_metadata_bootstrap"] = True


def downgrade():
    Base.metadata.drop_all(bind=op.get_bind())
