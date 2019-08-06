"""Created a table for storing emote stats

Revision ID: e54fed8855
Revises: 4a7ace75092
Create Date: 2015-12-03 02:58:39.145988

"""

# revision identifiers, used by Alembic.
revision = "e54fed8855"
down_revision = "4a7ace75092"
branch_labels = None
depends_on = None

import datetime
from alembic import op
import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.dialects import mysql
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session as BaseSession, relationship

Session = sessionmaker()

Base = declarative_base()


class Emote(Base):
    __tablename__ = "tb_emote"

    id = sa.Column(sa.Integer, primary_key=True)
    emote_id = sa.Column(sa.Integer, nullable=True)
    emote_hash = sa.Column(sa.String(32), nullable=True)
    code = sa.Column(sa.String(64), nullable=False, index=True)
    tm_record = sa.Column(sa.Integer)
    count = sa.Column(sa.Integer)


class EmoteStats(Base):
    __tablename__ = "tb_emote_stats"

    emote_code = sa.Column(sa.String(64), sa.ForeignKey("tb_emote.code"), primary_key=True, autoincrement=False)
    tm_record = sa.Column(sa.Integer, nullable=False, default=0)
    tm_record_date = sa.Column(sa.DateTime, nullable=True)
    count = sa.Column(sa.Integer, nullable=False, default=0)

    emote = relationship("Emote", backref="stats", lazy="joined")


def upgrade():
    bind = op.get_bind()
    session = Session(bind=bind)

    op.alter_column("tb_emote", "code", existing_type=mysql.VARCHAR(length=64, collation="utf8mb4_bin"), nullable=False)

    op.create_index(op.f("ix_tb_emote_code"), "tb_emote", ["code"], unique=False)

    op.create_table(
        "tb_emote_stats",
        sa.Column("emote_code", sa.String(length=64, collation="utf8mb4_bin"), autoincrement=False, nullable=False),
        sa.Column("tm_record", sa.Integer(), nullable=False),
        sa.Column("tm_record_date", sa.DateTime(), nullable=True),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["emote_code"], ["tb_emote.code"]),
        sa.PrimaryKeyConstraint("emote_code"),
    )

    emote_stat_data = {}
    for emote in session.query(Emote):
        if (emote.count is not None and emote.count > 0) or (emote.tm_record is not None and emote.tm_record > 0):
            if emote.code not in emote_stat_data:
                emote_stat_data[emote.code] = {
                    "count": emote.count if emote.count is not None else 0,
                    "tm_record": emote.tm_record if emote.tm_record is not None else 0,
                }
            else:
                emote_stat_data[emote.code]["count"] += emote.count
                emote_stat_data[emote.code]["tm_record"] += emote.tm_record
            emote_stat = EmoteStats()
            emote_stat.emote_code = emote.code
            emote_stat.count = emote.count
            emote_stat.tm_record = emote.tm_record
            emote_stat.tm_record_date = datetime.datetime.now

    for code in emote_stat_data:
        emote_stat = EmoteStats()
        emote_stat.emote_code = code
        emote_stat.count = emote_stat_data[code]["count"]
        emote_stat.tm_record = emote_stat_data[code]["tm_record"]
        emote_stat.tm_record_date = datetime.datetime.now()
        session.add(emote_stat)

    session.commit()

    op.drop_column("tb_emote", "tm_record")
    op.drop_column("tb_emote", "count")


def downgrade():
    bind = op.get_bind()
    session = Session(bind=bind)

    op.add_column("tb_emote", sa.Column("count", mysql.INTEGER(display_width=11), autoincrement=False, nullable=True))
    op.add_column(
        "tb_emote", sa.Column("tm_record", mysql.INTEGER(display_width=11), autoincrement=False, nullable=True)
    )

    for emote_stat in session.query(EmoteStats):
        emote_stat.emote.count = emote_stat.count
        emote_stat.emote.tm_record = emote_stat.tm_record

    session.commit()

    op.drop_table("tb_emote_stats")
    op.alter_column("tb_emote", "code", existing_type=mysql.VARCHAR(length=64, collation="utf8mb4_bin"), nullable=True)

    op.drop_index(op.f("ix_tb_emote_code"), table_name="tb_emote")
