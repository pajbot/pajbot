"""Remove emote tables

Revision ID: 34d6f5a24cbe
Revises: 100b2d456262
Create Date: 2016-04-10 11:29:11.326286

"""

# revision identifiers, used by Alembic.
revision = "34d6f5a24cbe"
down_revision = "100b2d456262"
branch_labels = None
depends_on = None

import argparse

from alembic import context
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship

from pajbot.utils import load_config
from pajbot.managers.redis import RedisManager

Session = sessionmaker()

Base = declarative_base()

tag = context.get_tag_argument()

parser = argparse.ArgumentParser()
parser.add_argument(
    "--config", "-c", default="config.ini", help="Specify which config file to use " "(default: config.ini)"
)
custom_args = None
if tag is not None:
    custom_args = tag.replace('"', "").split()
args, unknown = parser.parse_known_args(args=custom_args)

pb_config = load_config(args.config)

redis_options = {}
if "redis" in pb_config:
    redis_options = dict(pb_config.items("redis"))


RedisManager.init(**redis_options)


class Emote(Base):
    __tablename__ = "tb_emote"

    id = sa.Column(sa.Integer, primary_key=True)
    emote_id = sa.Column(sa.Integer, nullable=True)  # twitch.tv Emote ID
    emote_hash = sa.Column(sa.String(32), nullable=True)  # BTTV Emote Hash
    code = sa.Column(sa.String(length=64, collation="utf8mb4_bin"), nullable=False, index=True)

    stats = relationship("EmoteStats", uselist=False)


class EmoteStats(Base):
    __tablename__ = "tb_emote_stats"

    emote_code = sa.Column(
        sa.String(length=64, collation="utf8mb4_bin"),
        sa.ForeignKey("tb_emote.code"),
        primary_key=True,
        autoincrement=False,
    )
    tm_record = sa.Column(sa.Integer, nullable=False, default=0)
    tm_record_date = sa.Column(sa.DateTime, nullable=True)
    count = sa.Column(sa.Integer, nullable=False, default=0)


def upgrade():
    bind = op.get_bind()
    session = Session(bind=bind)

    with RedisManager.pipeline_context() as pipeline:
        streamer = pb_config["main"]["streamer"]
        count_key = "{streamer}:emotes:count".format(streamer=streamer)
        epmrecord_key = "{streamer}:emotes:epmrecord".format(streamer=streamer)
        pipeline.delete(count_key, epmrecord_key)
        for emote in session.query(Emote):
            if emote.stats:
                pipeline.zincrby(count_key, emote.code, emote.stats.count)
                pipeline.zincrby(epmrecord_key, emote.code, emote.stats.tm_record)

    op.drop_table("tb_emote_stats")
    op.drop_table("tb_emote")

    session.commit()


def downgrade():
    op.create_table(
        "tb_emote",
        sa.Column("id", mysql.INTEGER(display_width=11), nullable=False),
        sa.Column("emote_id", mysql.INTEGER(display_width=11), autoincrement=False, nullable=True),
        sa.Column("emote_hash", mysql.VARCHAR(length=32), nullable=True),
        sa.Column("code", mysql.VARCHAR(charset="utf8mb4", collation="utf8mb4_bin", length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        mysql_default_charset="utf8mb4",
        mysql_engine="InnoDB",
    )
    op.create_table(
        "tb_emote_stats",
        sa.Column("emote_code", mysql.VARCHAR(charset="utf8mb4", collation="utf8mb4_bin", length=64), nullable=False),
        sa.Column("tm_record", mysql.INTEGER(display_width=11), autoincrement=False, nullable=False),
        sa.Column("tm_record_date", mysql.DATETIME(), nullable=True),
        sa.Column("count", mysql.INTEGER(display_width=11), autoincrement=False, nullable=False),
        sa.ForeignKeyConstraint(["emote_code"], ["tb_emote.code"], name="tb_emote_stats_ibfk_1"),
        sa.PrimaryKeyConstraint("emote_code"),
        mysql_default_charset="utf8mb4",
        mysql_engine="InnoDB",
    )
