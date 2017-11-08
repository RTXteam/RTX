__all__ = ['register', 'cache_info', 'cache_clear']

cached_methods = []


def register(method):
    cached_methods.append(method)
    return method


def cache_info():
    info_list = ["[{}] {}".format(method.__qualname__, method.cache_info()) for method in cached_methods]
    return '\n'.join(info_list)


def cache_clear():
    for method in cached_methods:
        method.cache_clear()
