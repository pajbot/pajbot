"""Move banphrases from filters to the new banphrase table

Revision ID: 1e79c9c63
Revises: 15712d19833
Create Date: 2015-12-24 23:26:41.098033

"""

# revision identifiers, used by Alembic.
revision = "1e79c9c63"
down_revision = "15712d19833"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Session = sessionmaker()

Base = declarative_base()


class Filter(Base):
    __tablename__ = "tb_filters"

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(128))
    type = sa.Column(sa.String(64))
    action_json = sa.Column("action", sa.dialects.mysql.TEXT)
    extra_extra_args = sa.Column("extra_args", sa.dialects.mysql.TEXT)
    filter = sa.Column(sa.dialects.mysql.TEXT)
    source = sa.Column(sa.dialects.mysql.TEXT)
    enabled = sa.Column(sa.Boolean)
    num_uses = sa.Column(sa.Integer)


class BanphraseData(Base):
    __tablename__ = "tb_banphrase_data"

    banphrase_id = sa.Column(sa.Integer, sa.ForeignKey("tb_banphrase.id"), primary_key=True, autoincrement=False)
    num_uses = sa.Column(sa.Integer, nullable=False, default=0)
    added_by = sa.Column(sa.Integer, nullable=True)

    def __init__(self, banphrase_id, **options):
        self.banphrase_id = banphrase_id
        self.num_uses = 0
        self.added_by = None


class Banphrase(Base):
    __tablename__ = "tb_banphrase"

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(256), nullable=False, default="")
    phrase = sa.Column(sa.String(256), nullable=False)
    length = sa.Column(sa.Integer, nullable=False, default=300)
    permanent = sa.Column(sa.Boolean, nullable=False, default=False)
    warning = sa.Column(sa.Boolean, nullable=False, default=True)
    notify = sa.Column(sa.Boolean, nullable=False, default=True)
    case_sensitive = sa.Column(sa.Boolean, nullable=False, default=False)

    DEFAULT_TIMEOUT_LENGTH = 300
    DEFAULT_NOTIFY = True

    def __init__(self, **options):
        self.id = None
        self.name = "No name"
        self.length = self.DEFAULT_TIMEOUT_LENGTH
        self.permanent = False
        self.warning = True
        self.notify = self.DEFAULT_NOTIFY
        self.case_sensitive = False


import json


def upgrade():
    bind = op.get_bind()
    session = Session(bind=bind)

    for filter in session.query(Filter).filter_by(type="banphrase"):
        action = json.loads(filter.action_json)
        extra_args = {}
        if filter.extra_extra_args:
            extra_args = json.loads(filter.extra_extra_args)
        banphrase = Banphrase()
        banphrase.phrase = filter.filter
        banphrase.length = extra_args["time"] if "time" in extra_args else 300
        banphrase.permanent = True if "cb" in action and action["cb"] == "ban_source" else False
        banphrase.name = filter.name
        banphrase.enabled = filter.enabled
        session.add(banphrase)
        session.commit()
        banphrase.data = BanphraseData(banphrase.id)
        banphrase.data.num_uses = filter.num_uses
        session.add(banphrase.data)
        session.delete(filter)

    session.commit()


def downgrade():
    # you're screwed if you want to downgrade EleGiggle
    pass
