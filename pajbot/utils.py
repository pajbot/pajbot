import logging
import subprocess
import sys
import time

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


def time_method(f):
    import inspect

    def get_class_that_defined_method(meth):
        if inspect.ismethod(meth):
            for cls in inspect.getmro(meth.__self__.__class__):
                if cls.__dict__.get(meth.__name__) is meth:
                    return cls
            meth = meth.__func__
        if inspect.isfunction(meth):
            cls = getattr(inspect.getmodule(meth),
                          meth.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0])
            if isinstance(cls, type):
                return cls
        return None

    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        log.debug('{0.__name__}::{1.__name__} function took {2:.3f} ms'.format(get_class_that_defined_method(f), f, (time2 - time1) * 1000.0))
        return ret
    return wrap


def time_nonclass_method(f):
    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        log.debug('{0.__name__} function took {1:.3f} ms'.format(f, (time2 - time1) * 1000.0))
        return ret
    return wrap


def find(predicate, seq):
    """Method shamelessly taken from https://github.com/Rapptz/discord.py """

    for element in seq:
        if predicate(element):
            return element
    return None
