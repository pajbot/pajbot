from __future__ import with_statement

import argparse
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config
from sqlalchemy import pool

sys.path.append(os.path.dirname(os.path.abspath(__file__ + "/..")))

import pajbot.models.hsbet
from pajbot.bot import Bot
from pajbot.models.roulette import Roulette
from pajbot.models.webcontent import WebContent
from pajbot.modules import PredictModule
from pajbot.utils import load_config

tag = context.get_tag_argument()

parser = argparse.ArgumentParser()
parser.add_argument(
    "--config", "-c", default="config.ini", help="Specify which config file to use " "(default: config.ini)"
)
custom_args = None
if tag is not None:
    custom_args = tag.replace('"', "").split()
args, unknown = parser.parse_known_args(args=custom_args)

tb_config = load_config(args.config)

from pajbot.managers.db import Base

# from pajbot.models.user import User
# from pajbot.models.command import Command
# from pajbot.models import *

# from pajbot.utils import load_config

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

config.set_main_option("sqlalchemy.url", tb_config["main"]["db"])

# Interpret the config file for Python logging.
# This line sets up loggers basically.
# fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata
# sys.exit(0)

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=False)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
