"""Create the eight SalesGenie core tables."""
from alembic import op
from backend.db import Base
revision="0001_core_schema"
down_revision=None
branch_labels=None
depends_on=None
def upgrade():
    Base.metadata.create_all(bind=op.get_bind())
def downgrade():
    # Explicit downgrade only; normal startup never drops user data.
    Base.metadata.drop_all(bind=op.get_bind())
