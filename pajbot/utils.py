import logging
import subprocess
import sys

log = logging.getLogger(__name__)


def alembic_upgrade():
    try:
        subprocess.check_call(['alembic', 'upgrade', 'head'] + ['--tag="{0}"'.format(' '.join(sys.argv[1:]))])
    except subprocess.CalledProcessError:
        log.exception('aaaa')
        log.error('Unable to call `alembic upgrade head`, this means the database could be out of date. Quitting.')
        sys.exit(1)
    except PermissionError:
        log.error('No permission to run `alembic upgrade head`. This means your user probably doesn\'t have execution rights on the `alembic` binary.')
        log.error('The error can also occur if it can\'t find `alembic` in your PATH, and instead tries to execute the alembic folder.')
        sys.exit(1)
    except FileNotFoundError:
        log.error('Could not found an installation of alembic. Please install alembic to continue.')
        sys.exit(1)
    except:
        log.exception('Unhandled exception when calling db update')
        sys.exit(1)
