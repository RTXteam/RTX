"""timeoutn decorator and exception."""

__author__ = 'kzhao'

from functools import wraps
import errno
import os
import signal


class TimeoutError(Exception):
    """Nothing but a timeout expection."""
    pass


def timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
    """returns a decorator controlling the running time of the decorated function.

    Throws a TimeoutError exception if the decorated function does not return in given time.
    """
    def decorator(func):
        """the decorator."""
        def _handle_timeout(_signum, _frame):
            raise TimeoutError(error_message)

        def wrapper(*args, **kwargs):
            """wraps the function"""
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wraps(func)(wrapper)

    return decorator
