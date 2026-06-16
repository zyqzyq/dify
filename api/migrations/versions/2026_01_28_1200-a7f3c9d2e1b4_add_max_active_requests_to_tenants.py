"""add max active requests to tenants

Revision ID: a7f3c9d2e1b4
Revises: 788d3099ae3a
Create Date: 2026-01-28 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "a7f3c9d2e1b4"
down_revision = "788d3099ae3a"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("tenants", schema=None) as batch_op:
        batch_op.add_column(sa.Column("max_active_requests", sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table("tenants", schema=None) as batch_op:
        batch_op.drop_column("max_active_requests")
