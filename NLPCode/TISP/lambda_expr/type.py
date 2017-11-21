"""Type system in lambda calculus."""

__author__ = 'kzhao'

import sys
_logs = sys.stderr

from collections import defaultdict
from utils import Singleton


""" Types for lambda calculus

All type data structures are IMMUTABLE.
Type variable binding ONLY changes TypeEnv.
"""

#TODO: turn this off
_sanity_check = True

_TS = None


class TypeSystem(object):
    """Type System.

    This singleton class resolves all type relations.
    """

    __metaclass__ = Singleton

    def __init__(self):
        self.max_type_id = 1e8
        self.max_type_id_allocated = None
        self.type_id_pool = None
        self.type_atomics = None
        self.type_lists = None

        self.subtypes = None  # direct children
        self.all_subtypes = None  # all children
        self.parent_type = None
        self._root_atomic_type = None
        self.TE = None
        self.reset()

    def get_type_variable(self, name):
        """get a new type variable

        set type variable's name if given
        """
        if len(self.type_id_pool) == 0:
            type_var_id = self.max_type_id_allocated
            self.max_type_id_allocated += 1
            assert self.max_type_id_allocated < self.max_type_id
        else:
            type_var_id = self.type_id_pool.pop()
            assert type_var_id not in self.type_id_pool

        if name is None:   # anonymous
            name = "T%d_" % type_var_id

        tv = TypeVariable(name, type_var_id)

        return tv

    def duplicate_type(self, t, tvmapping=None):
        """duplicate t, rename the type variables in t.

        this function will be used together with AST's duplicate function
        """
        if tvmapping is None:
            tvmapping = {}

        if isinstance(t, AtomicType) or isinstance(t, ListType):
            return t
        elif isinstance(t, ComplexType):
            return ComplexType(self.duplicate_type(t.fromtype, tvmapping),
                               self.duplicate_type(t.totype, tvmapping))
        elif isinstance(t, TypeVariable):
            if t not in tvmapping:
                newt = self.get_type_variable(name=t.name)
                tvmapping[t] = newt
            return tvmapping[t]

    def get_atomic_type(self, name):
        if name not in self.type_atomics:
            v = AtomicType(name)
            self.type_atomics[name] = v
            return v
        return self.type_atomics[name]

    def get_complex_type(self, fromtype, totype):
        return ComplexType(fromtype, totype)

    def get_list_type(self, name):
        if name not in self.type_lists:
            v = ListType(name)
            self.type_lists[name] = v
            return v
        return self.type_lists[name]

    def reset(self):
        self.type_id_pool = set()
        self.max_type_id_allocated = 0
        self.type_atomics = {}
        self.type_lists = {}
        self.all_subtypes = defaultdict(set)
        self.subtypes = defaultdict(set)
        self._root_atomic_type = None
        self.parent_type = {}
        self.TE = None

    def add_subtype(self, parent, child):
        assert isinstance(parent, AtomicType), "parent type must be AtomicType"
        assert isinstance(child, AtomicType), "child type must be AtomicType"
        if child not in self.all_subtypes[parent]:
            self.all_subtypes[parent].add(child)
            self.subtypes[parent].add(child)
            self.all_subtypes[parent] |= self.all_subtypes[child]
            self.parent_type[child] = parent

            # trace up
            c = parent
            while c in self.parent_type:
                p = self.parent_type[c]
                self.all_subtypes[p] |= self.all_subtypes[c]
                c = p

    def get_root_atomic_type(self):
        """assume there is one root atomic type"""
        if self._root_atomic_type is None:
            c = self.subtypes.keys()[0]
            # trace up
            while c in self.parent_type:
                c = self.parent_type[c]
            self._root_atomic_type = c
        return self._root_atomic_type

    def unify_subtype(self, parent, child):
        """unify parent and child s.t. child <= parent"""

        if child <= parent:
            return True
        elif isinstance(parent, AtomicType) and isinstance(child, AtomicType):
            return False
        elif isinstance(parent, AtomicType) and isinstance(child, TypeVariable):
            _TS.TE[child] = parent
            return True
        elif isinstance(parent, TypeVariable) and isinstance(child, AtomicType):
            return False
        elif isinstance(parent, TypeVariable) and isinstance(child, TypeVariable):
            _TS.TE[child] = _TS.TE[parent]
            return True
        elif isinstance(parent, ComplexType) and isinstance(child, ComplexType):
            return self.unify_subtype(parent=child.fromtype, child=parent.fromtype) and \
                self.unify_subtype(parent=parent.totype, child=child.totype)
        return False

    def is_reducible(self, func, arg):
        if isinstance(func, ComplexType):
            return self.unify_subtype(parent=func.fromtype, child=arg)
        return False


_TS = TypeSystem()


class TypeEnv(dict):
    """Type Environment."""

    def __str__(self):
        return " ".join(["%s<:%s" % (k, v) for k, v in sorted(self.iteritems(),
                                                              key=lambda x: x[0].var_id)])

    def merge(self, other):
        """merge two type environments
        make sure there are no id collisions
        """
        if _sanity_check:
            self_ids = set([x.var_id for x in self.keys()])
            other_ids = set([x.var_id for x in other.keys()])
            if len(self_ids & other_ids) != 0:
                print >> _logs, self_ids, [(x, id(x)) for x in self.keys()]
                print >> _logs, other_ids, [(x, id(x)) for x in other.keys()]
                assert False
        return TypeEnv(self.items() + other.items())

    def duplicate(self, tvmapping=None):
        if tvmapping is None:
            tvmapping = {}
        newte = TypeEnv()
        for tv in self.keys():
            if tv not in tvmapping:
                newtv = _TS.get_type_variable(tv.name)
                tvmapping[tv] = newtv
            newte[tvmapping[tv]] = self[tv]
        return newte


class AtomicType(object):
    """Concrete Type, IMMUTABLE"""

    __slots__ = ["type"]

    TS = TypeSystem()

    def __init__(self, t):
        self.type = str(t)

    def __str__(self):
        return self.type

    anonymous_str = __str__

    __repr__ = __str__

    def __eq__(self, other):
        if isinstance(other, AtomicType):
            return self.type == other.type
        return False

    def __le__(self, other):
        #other_ = None
        if isinstance(other, AtomicType):
            other_ = other
        elif isinstance(other, TypeVariable):
            other_ = AtomicType.TS.TE[other]
        else:  # other is list or complex type
            return False
        return self == other_ or self in AtomicType.TS.all_subtypes[other_]


class ListType(object):
    """List of atomic type"""

    __slots__ = ["type"]

    TS = TypeSystem()

    def __init__(self, name):
        self.type = ListType.TS.get_atomic_type(name)

    def __str__(self):
        return "%s*" % self.type

    __repr__ = __str__

    anonymous_str = __str__

    def __eq__(self, other):
        if isinstance(other, ListType):
            return self.type == other.type
        return False

    def __le__(self, other):
        if isinstance(other, ListType):
            return self.type <= other.type
        return False


class ComplexType(object):
    """Complex Type: <a,b>"""

    __slots__ = "fromtype", "totype"

    def __init__(self, fromtype, totype):
        self.fromtype = fromtype
        self.totype = totype

    def __str__(self):
        return "<%s,%s>" % (self.fromtype, self.totype)

    __repr__ = __str__

    def anonymous_str(self):
        return "<%s,%s>" % (self.fromtype.anonymous_str(), self.totype.anonymous_str())

    def __eq__(self, other):
        if isinstance(other, ComplexType):
            return self.fromtype == other.fromtype and self.totype == other.totype
        return False

    def __le__(self, other):
        """contravariant"""
        if isinstance(other, ComplexType):
            return other.fromtype <= self.fromtype and self.totype <= other.totype
        return False

    def skip_first(self, n):
        """skip first n arguments"""
        if isinstance(self.fromtype, ListType):
            return self.totype
        if n == 1:
            return self.totype
        return self.totype.skip_first(n-1)


class TypeVariable(object):
    """Type Variable"""

    __slots__ = "name", "var_id"

    def __init__(self, name, var_id):
        self.name = name
        self.var_id = var_id

    def __str__(self):
        #return "%s" % self.name
        return "%s[%s]" % (self.name, self.var_id)

    def anonymous_str(self):
        return "[%s]" % _TS.TE[self]

    __repr__ = __str__

    def __hash__(self):
        return hash(self.var_id)

    def __copy__(self):
        return self

    __deepcopy__ = __copy__

    def __eq__(self, other):
        """eq in a given type environment"""
        if isinstance(other, TypeVariable):
            return _TS.TE[self] == _TS.TE[other]
        return False

    def __le__(self, other):
        if isinstance(other, AtomicType):
            other_ = other
        elif isinstance(other, TypeVariable):
            other_ = _TS.TE[other]
        else:
            return False
        return _TS.TE[self] == other_ or \
            _TS.TE[self] in _TS.all_subtypes[other_]

    def __del__(self):
        _TS.type_id_pool.add(self.var_id)
