import sys

from pajbot.utils import log


class AlembicContext:
    bot = None


def run_alembic_upgrade(bot):
    import alembic.config

    AlembicContext.bot = bot

    alembic_args = ["--raiseerr", "upgrade", "head", '--tag="{0}"'.format(" ".join(sys.argv[1:]))]

    try:
        alembic.config.main(argv=alembic_args)
    except:
        log.exception("xd")
        sys.exit(1)
