import logging

from .get_class_that_defined_method import get_class_that_defined_method
from .now import now

log = logging.getLogger(__name__)


def time_method(f):
    def wrap(*args, **kwargs):
        defining_class = get_class_that_defined_method(f)
        if defining_class is not None:
            fn_description = f"{defining_class.__name__}::{f.__name__}"
        else:
            fn_description = f.__name__

        time1 = now().timestamp()
        ret = f(*args, **kwargs)
        time2 = now().timestamp()
        log.debug(f"{fn_description} function took {(time2 - time1) * 1000.0:.3f} ms")
        return ret

    return wrap
