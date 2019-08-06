"""Added a new table for storing data about commands

Revision ID: 5393671cca7
Revises: 496dba8300a
Create Date: 2015-12-13 03:41:30.735949

"""

# revision identifiers, used by Alembic.
revision = "5393671cca7"
down_revision = "496dba8300a"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Session = sessionmaker()

Base = declarative_base()


class CommandData(Base):
    __tablename__ = "tb_command_data"

    command_id = sa.Column(sa.Integer, sa.ForeignKey("tb_command.id"), primary_key=True, autoincrement=False)
    num_uses = sa.Column(sa.Integer, nullable=False)


class Command(Base):
    __tablename__ = "tb_command"

    id = sa.Column(sa.Integer, primary_key=True)
    level = sa.Column(sa.Integer, nullable=False, default=100)
    action_json = sa.Column("action", sa.TEXT)
    extra_extra_args = sa.Column("extra_args", sa.TEXT)
    command = sa.Column(sa.TEXT, nullable=False)
    description = sa.Column(sa.TEXT, nullable=True)
    delay_all = sa.Column(sa.Integer, nullable=False, default=5)
    delay_user = sa.Column(sa.Integer, nullable=False, default=15)
    enabled = sa.Column(sa.Boolean, nullable=False, default=True)
    num_uses = sa.Column(sa.Integer, nullable=False, default=0)
    cost = sa.Column(sa.Integer, nullable=False, default=0)
    can_execute_with_whisper = sa.Column(sa.Boolean)
    sub_only = sa.Column(sa.Boolean, nullable=False, default=False)
    mod_only = sa.Column(sa.Boolean, nullable=False, default=False)


def upgrade():
    bind = op.get_bind()
    session = Session(bind=bind)

    op.create_table(
        "tb_command_data",
        sa.Column("command_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("num_uses", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["command_id"], ["tb_command.id"]),
        sa.PrimaryKeyConstraint("command_id"),
    )

    for command in session.query(Command):
        data = CommandData()
        data.command_id = command.id
        data.num_uses = command.num_uses
        session.add(data)

    session.commit()


def downgrade():
    bind = op.get_bind()
    session = Session(bind=bind)

    for data in session.query(CommandData):
        command = session.query(Command).filter_by(id=data.command_id).one()
        command.num_uses = data.num_uses
        session.add(data)

    session.commit()

    op.drop_table("tb_command_data")
