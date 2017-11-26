"""Class Singleton.

This class can be used as the base class for singletons.
Each inherited class can have only one instance.

"""

__author__ = 'kzhao'


class Singleton(type):
    """Base class for Singleton pattern."""
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
