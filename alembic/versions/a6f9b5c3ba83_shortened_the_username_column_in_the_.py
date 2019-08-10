"""Shortened the username column in the user table, and indexed the points column

Revision ID: a6f9b5c3ba83
Revises: f7182019343e
Create Date: 2016-04-22 20:45:42.518092

"""

# revision identifiers, used by Alembic.
revision = "a6f9b5c3ba83"
down_revision = "f7182019343e"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


def upgrade():
    op.alter_column(
        "tb_user",
        "username",
        existing_type=mysql.VARCHAR(length=128),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
    op.alter_column(
        "tb_user",
        "username_raw",
        existing_type=mysql.VARCHAR(length=128),
        type_=sa.String(length=32),
        existing_nullable=True,
    )
    op.create_index(op.f("ix_tb_user_points"), "tb_user", ["points"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_tb_user_points"), table_name="tb_user")
    op.alter_column(
        "tb_user",
        "username_raw",
        existing_type=sa.String(length=32),
        type_=mysql.VARCHAR(length=128),
        existing_nullable=True,
    )
    op.alter_column(
        "tb_user",
        "username",
        existing_type=sa.String(length=32),
        type_=mysql.VARCHAR(length=128),
        existing_nullable=False,
    )
