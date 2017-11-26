#!/usr/bin/env python

from collections import defaultdict


class floatpair:
    """A pair of floats.

    Used for averaged perceptron.
    """
    __slots__ = "first", "second"
    def __init__(self):
        self.first = 0.0
        self.second = 0.0

    def __lt__(self, other):
        return self.first < other.first


class svector(defaultdict):
    """Sparse vector for structured training."""
    def __init__(self, valtype=floatpair, d={}):
        defaultdict.__init__(self, lambda: floatpair(), d)

    def __setitem__(self, key, v):
        t = None
        if type(v) is float:
            dict.__getitem__(self, key).first = v
        else: # called by getitem
            dict.__setitem__(self, key, v)

    def __getitem__(self, key):
        return dict.__getitem__(self, key).first

    def evaluate(self, feats):
        return sum(self[f] for f in feats if f in self)

    def iadd(self, other, step=1):
        for key, values in other.iteritems():
            mypair = dict.__getitem__(self, key)
            mypair.first += values.first
            mypair.second += values.first * step
        return self

    def iaddc(self, other, c):
        for key, values in other.iteritems():
            mypair = dict.__getitem__(self, key)
            mypair.first += values.first * c
            mypair.second += values.second * c
        return self

    def iaddl(self, feats, c):
        for f in feats:
            (dict.__getitem__(self, f)).first += c
        return self

    def dot(self, other):
        shorter, longer = (self, other) if len(self) < len(other) else (other, self)
        return sum([longer[key] * values.first for key, values in shorter.iteritems()])

    def times(self, val):
        for k in self:
            mypair = dict.__getitem__(self, k)
            mypair.first *= val
            mypair.second *= val
        return self

    def set_avg(self, c):
        if c > 0:
            c = -1. / c
            for values in self.values():
                y = values.first
                values.first += values.second*c
                values.second = y

    def reset_avg(self, c):
        for values in self.values():
            y = values.second
            values.second = c*(values.second - values.first)
            values.first = y

    def __deepcopy__(self):
        n = svector()
        for key, values in self.iteritems():
            dict.__getitem__(n, key).first = values.first

        return n
