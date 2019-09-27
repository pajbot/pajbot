import logging

from .get_class_that_defined_method import get_class_that_defined_method
from .now import now

log = logging.getLogger(__name__)


def time_method(f):
    def wrap(*args, **kwargs):
        defining_class = get_class_that_defined_method(f)
        if defining_class is not None:
            fn_description = "{0.__name__}::{1.__name__}".format(defining_class, f)
        else:
            fn_description = f.__name__

        time1 = now().timestamp()
        ret = f(*args, **kwargs)
        time2 = now().timestamp()
        log.debug("{0} function took {1:.3f} ms".format(fn_description, (time2 - time1) * 1000.0))
        return ret

    return wrap
