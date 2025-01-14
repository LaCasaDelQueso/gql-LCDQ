""" This module implements the decorator @deprecated.
    Credits: https://stackoverflow.com/questions/2536307/decorators-in-the-python-standard-lib-deprecated-specifically
"""
import functools
import inspect
from typing import Callable, Type
import warnings

string_types = (type(b""), type(""))


def deprecated(reason: bytes | str | Type | Callable, module: str = ""):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used.

    Parameters
    ----------
    reason : bytes | str | object | function
    module : str, optional (default is "")

    Returns
    -------
    functools._Wrapped

    Raises
    ------
    TypeError
    """

    if isinstance(reason, string_types):
        # The @deprecated is used with a 'reason'.
        #
        # .. code-block:: python
        #
        #    @deprecated("please, use another function")
        #    def old_function(x, y):
        #      pass

        def decorator(func1):
            if inspect.isclass(func1):
                fmt1 = "Call to deprecated class {module}{name} ({reason})."
            else:
                fmt1 = "Call to deprecated function {module}{name} ({reason})."

            @functools.wraps(func1)
            def new_func1(*args, **kwargs):
                warnings.simplefilter("always", DeprecationWarning)
                warnings.warn(
                    fmt1.format(
                        name=func1.__name__,
                        reason=reason,
                        module=(f"[{module}] " if module else ""),
                    ),
                    category=DeprecationWarning,
                    stacklevel=2,
                )
                warnings.simplefilter("default", DeprecationWarning)
                return func1(*args, **kwargs)

            return new_func1

        return decorator

    elif inspect.isclass(reason) or inspect.isfunction(reason):
        # The @deprecated is used without any 'reason'.
        #
        # .. code-block:: python
        #
        #    @deprecated
        #    def old_function(x, y):
        #      pass

        func2 = reason

        if inspect.isclass(func2):
            fmt2 = "Call to deprecated class {module}{name}."
        else:
            fmt2 = "Call to deprecated function {module}{name}."

        @functools.wraps(func2)
        def new_func2(*args, **kwargs):
            warnings.simplefilter("always", DeprecationWarning)
            warnings.warn(
                fmt2.format(
                    name=func2.__name__, module=(f"[{module}] " if module else "")
                ),
                category=DeprecationWarning,
                stacklevel=2,
            )
            warnings.simplefilter("default", DeprecationWarning)
            return func2(*args, **kwargs)

        return new_func2

    else:
        raise TypeError(repr(type(reason)))
