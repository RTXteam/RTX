"""
To manage all methods (or functions) decorated with `@functools.lru_cache`
"""

__all__ = ['register', 'cache_info', 'cache_clear']

# all methods (or function) decorated with `@CachedMethod.register` will be added to this list
cached_methods = []


def register(method):
    """
    Put the decorated method (or function) into `cached_methods`

    :param method: the method (or function) decorated with `@functools.lru_cache`
                   that you want to be managed by this module
    :return:
    """
    cached_methods.append(method)
    return method


def cache_info():
    """
    Call `.cache_info()` for each method in `cached_methods`; return the aggregated string, one line for one method
    """
    info_list = ["[{}] {}".format(method.__qualname__, method.cache_info()) for method in cached_methods]
    return '\n'.join(info_list)


def cache_clear():
    """
    Clear all the caches of all the methods in `cached_methods`
    """
    for method in cached_methods:
        method.cache_clear()
