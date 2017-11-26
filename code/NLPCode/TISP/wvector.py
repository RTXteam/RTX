"""Weight vector.

This is a wrapper over svector. The value space for each action in the parser is defined separately.
"""

from __future__ import division


from collections import defaultdict

import copy  # slow
import math

import sys
logs = sys.stderr
from hashlib import md5

import gflags as flags
FLAGS = flags.FLAGS

flags.DEFINE_boolean("nonzerolen", False, "output non-zero feature len")

flags.DEFINE_boolean("mydouble", True, "use C module mydouble instead of Python immutable float/int")

import time

from svector import svector


class WVector(defaultdict):
    """ wvector[action][feat] = weight"""

    action_names = []
    value_class = float  # mydouble
    zero = 0

    @staticmethod
    def setup(names):
        WVector.action_names = names

    def __init__(self, valtype=None, d={}):
        defaultdict.__init__(self, svector,
                             [(action, svector()) for action in WVector.action_names])

    def resorted(self):
        new = WVector()
        for action, feats in self.iteritems():
            new[action] = svector(sorted(feats.items()))

        del self
        return new

    def evaluate(self, action, list_of_features):
        return self[action].evaluate(list_of_features)

    def iadd(self, other):
        for (action, feats) in other.iteritems():
            self[action].iadd(feats)  # int defaultdict

        return self

    def iadd_wstep(self, other, step=1):
        for (action, feats) in other.iteritems():
            self[action].iadd(feats, step)  # int defaultdict

        return self

    def iaddc(self, other, c=1):
        """add value c to each element in other"""
        for (action, feats) in other.iteritems():
            self[action].iaddc(feats, c)

        return self

    def iaddl(self, action, other, c=1):
        """add value c to each element in other"""
        self[action].iaddl(other, c)
        return self

    def dot(self, other):
        """dot product"""
        s = 0
        for (action, feats) in other.iteritems():
            s += self[action].dot(feats)
        return s

    def times(self, val):
        assert type(val) is float or type(val) is int
        for feats in self.values():
            feats = feats.times(val)
        return self

    def set_avg(self, c):
        for _, feats in self.iteritems():
            feats.set_avg(c)

    def reset_avg(self, c):
        for _, feats in self.iteritems():
            feats.reset_avg(c)

    def copy(self):
        """ should be made a lot faster!!"""

        t = time.time()
        new = WVector()
        for action, feats in self.iteritems():
            new[action] = copy.deepcopy(feats)  # now mydouble is mutable, must deepcopy

        print >> logs, "copying took %.1f seconds" % (time.time() - t)
        return new

    def deepcopy(self):
        new = WVector()
        for action, feats in self.iteritems():
            new[action] = feats.deepcopy()
        return new

    def get_flat_weights(self):
        """return single-layer dictionary"""
        w = {}
        for action, feats in self.iteritems():
            for f, v in feats.iteritems():
                w["%s=>%s" % (f, action)] = v.first
        return w

    def trim(self):
        """remove all elements w/ weight 0"""
        for feats in self.itervalues():
            for f, v in feats.items():
                if v.first == 0:  # or v == WVector.zero:
                    #del v # N.B. free this mydouble instance!
                    del feats[f]

    def __len__(self):
        """ non-zero length """
        return sum(map(len, self.values())) if not FLAGS.nonzerolen else \
            sum(len(filter(lambda v: math.fabs(v.first) > 1e-3, feats.values()))
                for feats in self.values())

    def __str__(self):
        s = []
        for action, feats in self.iteritems():
            for f, v in feats.iteritems():
                s.append("%s=>%s=%f" % (action, f, v.first))
        return " ".join(s)

    def get_hash(self):
        s = []
        for action, feats in self.iteritems():
            for f, v in feats.iteritems():
                s += ["%s=>%s=%f" % (action, f, v.first)]
        s = sorted(s)
        m = md5()
        m.update(" ".join(s))
        return m.hexdigest()
