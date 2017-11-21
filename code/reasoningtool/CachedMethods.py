""" This module keeps track of all cacheable methods (or functions) for NCATS project.
"""
__author__ = ""
__copyright__ = ""
__credits__ = []
__license__ = ""
__version__ = ""
__maintainer__ = ""
__email__ = ""
__status__ = "Prototype"

from functools import lru_cache

__all__ = ['register', 'cache_info', 'cache_clear']

# all methods (or function) decorated with `@CachedMethod.register` will be added to this list
cached_methods = []

enabled = True

lru_cache_setting = {
    "maxsize": 1024,
    "typed": False
}


def register(method):
    """
    Put the lru_cache enabled method (or function) into `cached_methods`

    :param method: the method (or function) wrapped by `@functools.lru_cache`
                   that you want to be managed by this module
    :return:
    """
    global enabled, cached_methods, lru_cache_setting

    if enabled:
        method = lru_cache(**lru_cache_setting)(method)
        cached_methods.append(method)
        return method
    else:
        return method


def cache_info():
    """
    Call `.cache_info()` for each method in `cached_methods`; return the aggregated string, one line for one method
    """
    global cached_methods

    if len(cached_methods) == 0:
        return None
    else:
        info_list = ["[{}] {}".format(method.__qualname__, method.cache_info()) for method in cached_methods]
        return '\n'.join(info_list)


def cache_clear():
    """
    Clear all the caches of all the methods in `cached_methods`
    """
    global cached_methods

    for method in cached_methods:
        method.cache_clear()
