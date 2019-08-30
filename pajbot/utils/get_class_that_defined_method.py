import inspect


def get_class_that_defined_method(meth):
    if inspect.ismethod(meth):
        for cls in inspect.getmro(meth.__self__.__class__):
            if cls.__dict__.get(meth.__name__) is meth:
                return cls
        meth = meth.__func__

    if inspect.isfunction(meth):
        cls = getattr(inspect.getmodule(meth), meth.__qualname__.split(".<locals>", 1)[0].rsplit(".", 1)[0])
        if isinstance(cls, type):
            return cls

    return None
