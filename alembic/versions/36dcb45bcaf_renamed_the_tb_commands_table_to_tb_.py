"""Renamed the tb_commands table to tb_command

Revision ID: 36dcb45bcaf
Revises: 24fc72755a4
Create Date: 2015-12-13 00:06:34.485842

"""

# revision identifiers, used by Alembic.
revision = "36dcb45bcaf"
down_revision = "24fc72755a4"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


def upgrade():
    op.rename_table("tb_commands", "tb_command")


def downgrade():
    op.rename_table("tb_command", "tb_commands")
