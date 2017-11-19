"""Utility functions/classes for Type-driven Incremental Semantic Parser

This module only contains:

Singleton: the base class for singleton pattern

timeout: function used as a decorator that forces the decorated function to terminate
         after given time.

Timeout: a class used for error passing

"""

__author__ = 'kzhao'

__all__ = ["singleton", "timeout"]

from singleton import Singleton
from timeout import TimeoutError, timeout
