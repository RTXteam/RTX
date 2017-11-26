"""AST nodes for lambda expressions: Variable, Constant, App, Lambda.

All nodes are IMMUTABLE


Supported operations:

__eq__: returns True iff the two exprs are EXACTLY the same

semantic_eq: returns True iff the two exprs are semantically the same, which means
             for Variable, two variables represent the same one under some rename mapping;
             for atomic Constants, both names and types are the same;
             for complex Constants (predicates), the names are the same

substitute: substitutes the occurrences of var with expr

reduce: recursively reduce downward

duplicate: duplicates self, but renames all type variables
"""

__author__ = 'kzhao'

import sys
_logs = sys.stderr

from type import AtomicType, ComplexType, ListType, TypeVariable, TypeSystem

_TS = TypeSystem()


class Variable(object):
    """Variable in lambda calculus."""
    __slots__ = "name", "type", "var_id"

    _pool = set()
    _max_var_id_allocated = 0

    @staticmethod
    def get_anonymous_var(type=None):
        """gets a new anonymous"""
        if len(Variable._pool) > 0:
            var_id = Variable._pool.pop()
        else:
            var_id = Variable._max_var_id_allocated + 10000
            Variable._max_var_id_allocated += 1
        varname = "$%d" % var_id
        ret = Variable(name=varname, type=type)
        ret.var_id = var_id
        return ret

    def __init__(self, name, type=None):
        self.name = name
        self.type = type
        self.var_id = None

    def __str__(self):
        return self.name

    __repr__ = __str__

    def fulltype_str(self):
        return "%s:%s" % (self.name, self.type)

    def __eq__(self, other):
        return isinstance(other, Variable) and self.name == other.name

    def semantic_eq(self, other, varmapping=None):
        if not isinstance(other, Variable):
            return False
        if varmapping is None:
            return True
        elif self.name in varmapping:
            return varmapping[self.name] == other.name
        return False

    def reduce(self):
        return self

    def substitute(self, var, expr):
        if self == var:
            return expr
        return self

    def duplicate(self, vmapping=None, tvmapping=None):
        if tvmapping is None:
            tvmapping = {}
        if vmapping is None:
            vmapping = {}
        if self.name.startswith("$P"):
            return Variable(name=self.name, type=_TS.duplicate_type(self.type, tvmapping))
        elif self.name in vmapping:
            newvar = Variable(name=vmapping[self.name], type=_TS.duplicate_type(self.type, tvmapping))
        else:
            newvar = Variable.get_anonymous_var(type=_TS.duplicate_type(self.type, tvmapping))
            vmapping[self.name] = newvar.name
        return newvar
        #return Variable(name=self.name, type=_TS.duplicate_type(self.type, tvmapping))

    def __del__(self):
        if self.var_id:
            Variable._pool.add(self.var_id)


class Constant(object):
    """Constant in lambda calculus."""
    __slots__ = "name", "type"

    def __init__(self, name, type):
        self.name = name
        self.type = type

    def __str__(self):
        return "%s:%s" % (self.name, self.type)

    __repr__ = __str__

    def fulltype_str(self):
        return str(self)

    def __eq__(self, other):
        return isinstance(other, Constant) and self.name == other.name and self.type == other.type

    def semantic_eq(self, other, varmapping=None):
        if isinstance(other, Constant):
            if isinstance(self.type, AtomicType):
                return self.name == other.name and self.type == other.type
            return self.name == other.name
        return False

    def reduce(self):
        return self

    def substitute(self, var, expr):
        return self

    def duplicate(self, vmapping=None, tvmapping=None):
        if tvmapping is None:
            tvmapping = {}
        return Constant(name=self.name, type=_TS.duplicate_type(self.type, tvmapping))


class App(object):
    """Function application in lambda calculus."""
    __slots__ = "predicate", "args", "type"

    __collective_preds__ = "and", "or", "equals"

    def __init__(self, predicate, args, type):
        self.predicate = predicate
        self.args = args
        self.type = type

    def __str__(self):
        return "(%s %s)" % (self.predicate, " ".join(str(arg) for arg in self.args))

    __repr__ = __str__

    def fulltype_str(self):
        return "(%s %s):%s" % (self.predicate.fulltype_str(),
                               " ".join(arg.fulltype_str() for arg in self.args), self.type)

    def __eq__(self, other):
        return isinstance(other, App) and self.predicate == other.predicate and \
               len(self.args) == len(other.args) and \
               all([x == y for (x, y) in zip(self.args, other.args)])

    def semantic_eq(self, other, varmapping=None):
        if isinstance(other, App) and \
           self.predicate.semantic_eq(other.predicate, varmapping) and \
           len(self.args) == len(other.args):
            if isinstance(self.predicate, Constant) and \
               self.predicate.name in App.__collective_preds__:
                # the order of the args does not matter
                other_matched = set()  # idx of arg in other.args that have been used
                for x in self.args:
                    found_match = False
                    for i, y in enumerate(other.args):
                        if i not in other_matched:
                            new_varmapping = dict(varmapping) if varmapping else None
                            if x.semantic_eq(y, new_varmapping):
                                found_match = True
                                other_matched.add(i)
                                break
                    if not found_match:
                        return False
                return True
            else:
                return all([x.semantic_eq(y, varmapping) for (x, y) in zip(self.args, other.args)])
        return False

    def reduce(self):
        newargs = [arg.reduce() for arg in self.args]
        reduce_result = self.predicate.reduce()
        while isinstance(reduce_result, Lambda) and len(newargs) > 0:
            # TODO: sanity check if the types match
            reduce_result = reduce_result.reduce_with(newargs[0])
            newargs = newargs[1:]
        if len(newargs) == 0:
            return reduce_result
        else:
            return App(predicate=reduce_result, args=newargs,
                       type=reduce_result.type.skip_first(len(newargs)))

    def substitute(self, var, expr):
        return App(predicate=self.predicate.substitute(var, expr),
                   args=[arg.substitute(var, expr) for arg in self.args],
                   type=self.type)

    def duplicate(self, vmapping=None, tvmapping=None):
        if tvmapping is None:
            tvmapping = {}
        if vmapping is None:
            vmapping = {}
        return App(self.predicate.duplicate(vmapping, tvmapping),
                   [arg.duplicate(vmapping, tvmapping) for arg in self.args],
                   _TS.duplicate_type(self.type, tvmapping))


class Lambda(object):
    """Lambda expression in lambda calculus."""
    __slots__ = "var", "body", "type"

    def __init__(self, var, body, type):
        self.var = var
        self.body = body
        self.type = type

    def __str__(self):
        return "(lambda %s:%s %s)" % (self.var, self.var.type, self.body)

    __repr__ = __str__

    def fulltype_str(self):
        return "(lambda %s %s):%s" % (self.var.fulltype_str(), self.body.fulltype_str(), self.type)

    def __eq__(self, other):
        return isinstance(other, Lambda) and self.var == other.var and self.body == other.body

    def semantic_eq(self, other, varmapping=None):
        if isinstance(other, Lambda):
            if varmapping is None:
                varmapping = {}
            if self.var.name not in varmapping:
                varmapping[self.var.name] = other.var.name
            return self.var.semantic_eq(other.var, varmapping) and \
                self.body.semantic_eq(other.body, varmapping)

    def reduce(self):
        body = self.body.reduce()
        return Lambda(var=self.var, body=body,
                      type=ComplexType(fromtype=self.var.type, totype=body.type))

    def substitute(self, var, expr):
        """replace all occurrences of var w/ expr"""
        if var.name != self.var.name:
            return Lambda(var=self.var, body=self.body.substitute(var, expr), type=self.type)
        return self

    def reduce_with(self, arg):
        """assume reducible"""
        expr = self.body.substitute(self.var, arg)
        return expr.reduce()

    def duplicate(self, vmapping=None, tvmapping=None):
        if tvmapping is None:
            tvmapping = {}
        if vmapping is None:
            vmapping = {}
        return Lambda(self.var.duplicate(vmapping, tvmapping), self.body.duplicate(vmapping, tvmapping),
                      _TS.duplicate_type(self.type, tvmapping))


class TypeInferer(object):
    """Hindley Milner type inference
    based on:
    http://smallshire.org.uk/sufficientlysmall/2010/04/11/a-hindley-milner-type-inference-implementation-in-python
    """

    var_id_pool = None
    max_id_allocated = None
    max_var_id = None

    class InferTypeVar(object):
        """Type Variable."""
        __slots__ = ["var_id", "instance"]

        def __init__(self, var_id):
            self.var_id = var_id
            self.instance = None

        def __eq__(self, other):
            other_ = other
            if isinstance(other, TypeInferer.InferTypeVar):
                other_ = other.instance
            return self.instance == other_

    @staticmethod
    def reset():
        """resets the type system."""
        TypeInferer.max_var_id = 1e8
        TypeInferer.max_id_allocated = 0
        TypeInferer.var_id_pool = set()

    @staticmethod
    def get_infertypevar():
        """Get a new type variable."""
        if len(TypeInferer.var_id_pool) == 0:
            var_id = TypeInferer.max_id_allocated
            TypeInferer.max_id_allocated += 1
            assert TypeInferer.max_id_allocated < TypeInferer.max_var_id
        else:
            var_id = TypeInferer.var_id_pool.pop()

        return TypeInferer.InferTypeVar(var_id=var_id)

    @staticmethod
    def infer_type(expr):
        """infers the type of the expr."""
        TypeInferer.reset()
        return TypeInferer._infer_type(expr, env=dict(), non_generic=set())

    @staticmethod
    def _infer_type(expr, env, non_generic):
        if isinstance(expr, Variable):
            envtype = TypeInferer._get_type(expr.name, env, non_generic)
            if envtype:
                expr.type = envtype
        elif isinstance(expr, Constant):
            assert expr.type
        elif isinstance(expr, App):
            predicate_type = TypeInferer._infer_type(expr.predicate, env, non_generic)
            if isinstance(predicate_type, ComplexType) and \
               isinstance(predicate_type.fromtype, ListType):
                result_type = TypeInferer.get_infertypevar()
                for arg in expr.args:
                    arg_type = TypeInferer._infer_type(arg, env, non_generic)
                    TypeInferer._unify_types_subtype(predicate_type.fromtype.type, arg_type)
                TypeInferer._unify_types_subtype(result_type, predicate_type.totype)
                expr.type = TypeInferer._prune_type(result_type)
            else:
                result_type = TypeInferer.get_infertypevar()
                predptype = predicate_type
                for arg in expr.args:
                    pt = predptype.fromtype
                    arg_type = TypeInferer._infer_type(arg, env, non_generic)
                    TypeInferer._unify_types_subtype(pt, arg_type)
                    predptype = predptype.totype
                TypeInferer._unify_types_subtype(result_type, predptype)
                expr.type = TypeInferer._prune_type(result_type)
        elif isinstance(expr, Lambda):
            vartype = expr.var.type if expr.var.type else TypeInferer.get_infertypevar()
            env[expr.var.name] = vartype
            non_generic.add(vartype)
            TypeInferer._infer_type(expr.body, env, non_generic)
            newvartype = TypeInferer._prune_type(vartype)
            expr.var.type = newvartype
            expr.type = ComplexType(fromtype=expr.var.type, totype=expr.body.type)
        else:
            assert False, "wrong expr %s" % expr
        return expr.type

    @staticmethod
    def _get_type(varname, env, non_generic):
        if varname in env:
            return TypeInferer._fresh(env[varname], non_generic)
        else:
            return None

    @staticmethod
    def _fresh(vartype, non_generic):
        mappings = {}

        def fresh_rec(varp):
            p = TypeInferer._prune_type(varp)
            if isinstance(p, TypeInferer.InferTypeVar):
                if TypeInferer._is_type_generic(p, non_generic):
                    if p not in mappings:
                        mappings[p.name] = _TS.get_type_variable()
                    else:
                        return mappings[p.name]
                else:
                    return p
            elif isinstance(p, AtomicType) or \
                 isinstance(p, ListType) or \
                 isinstance(p, TypeVariable):
                return p
            elif isinstance(p, ComplexType):
                return ComplexType(fromtype=fresh_rec(p.fromtype), totype=fresh_rec(p.totype))

        ret = fresh_rec(vartype)
        return ret

    @staticmethod
    def _prune_type(t):
        """InferTypeVar -> AtomicType/ListType/TypeVariable unless InferTypeVar is unbounded"""
        if isinstance(t, TypeInferer.InferTypeVar):
            if t.instance:
                t.instance = TypeInferer._prune_type(t.instance)
                return t.instance
        elif isinstance(t, ComplexType):
            return ComplexType(fromtype=TypeInferer._prune_type(t.fromtype),
                               totype=TypeInferer._prune_type(t.totype))
        return t

    @staticmethod
    def _occurs_in(a, b):
        """type b occurs in a?"""
        b2 = TypeInferer._prune_type(b)
        if a == b2:
            return True
        elif isinstance(b2, ComplexType):
            return TypeInferer._occurs_in(a, b2.fromtype) or TypeInferer._occurs_in(a, b2.totype)
        return False

    @staticmethod
    def _is_type_generic(v, non_generic):
        return not any(TypeInferer._occurs_in(v, t) for t in non_generic)

    @staticmethod
    def _unify_types_subtype(t1, t2):
        """unification s.t. t2 <: t1"""
        a = TypeInferer._prune_type(t1)
        b = TypeInferer._prune_type(t2)
        if isinstance(a, TypeInferer.InferTypeVar):
            if a != b:
                if TypeInferer._occurs_in(a, b):
                    return False
                a.instance = b
                return True
        elif isinstance(b, TypeInferer.InferTypeVar):
            if a != b:
                if TypeInferer._occurs_in(b, a):
                    return False
                b.instance = a
                return True
        elif isinstance(a, ComplexType) and isinstance(b, ComplexType):
            return TypeInferer._unify_types_subtype(b.fromtype, a.fromtype) and \
                   TypeInferer._unify_types_subtype(a.totype, b.totype)
        else:
            return _TS.unify_subtype(parent=a, child=b)


def collect_constants(expr):
    """collect constant unigrams and bigrams in expr"""
    if isinstance(expr, Variable):
        return set(), set()
    elif isinstance(expr, Constant):
        return set([expr]), set()
    elif isinstance(expr, App):
        if isinstance(expr.predicate, Constant):
            unigrams = set([expr.predicate])
            bigrams = set()
            for arg in expr.args:
                if isinstance(arg, Constant):
                    unigrams.add(arg)
                    bigrams.add((expr.predicate.name, arg.name))
                elif isinstance(arg, App) and isinstance(arg.predicate, Constant):
                    bigrams.add((expr.predicate.name, arg.predicate.name))
                    u, b = collect_constants(arg)
                    unigrams |= u
                    bigrams |= b
                else:
                    u, b = collect_constants(arg)
                    unigrams |= u
                    bigrams |= b
        else:
            unigrams, bigrams = collect_constants(expr.predicate)
            for arg in expr.args:
                u, b = collect_constants(arg)
                unigrams |= u
                bigrams |= b
        return unigrams, bigrams
    elif isinstance(expr, Lambda):
        return collect_constants(expr.body)
    else:
        assert False, "unknown expr %s" % expr


def simplify_expr(expr):
    """Simplifies the expression with some heuristics."""
    if isinstance(expr, Lambda):
        if isinstance(expr.body, App) and isinstance(expr.body.predicate, Constant) and \
                len(expr.body.args) == 1 and expr.body.args[0] == expr.var:
            return expr.body.predicate
        else:
            return Lambda(var=expr.var, body=simplify_expr(expr.body), type=expr.type)
    elif isinstance(expr, App):
        newpred = simplify_expr(expr.predicate)
        newargs = [simplify_expr(arg) for arg in expr.args]
        # (and ... (and ... ) ... )
        newargs2 = []
        if isinstance(newpred, Constant) and newpred.name == "and":
            for arg in newargs:
                if isinstance(arg, App) and isinstance(arg.predicate, Constant) and \
                                arg.predicate.name == "and":
                    newargs2 += arg.args
                else:
                    newargs2.append(arg)
        elif isinstance(newpred, Constant) and newpred.name == "or":
            # (or ... (or ... ) ...)
            for arg in newargs:
                if isinstance(arg, App) and isinstance(arg.predicate, Constant) and \
                                arg.predicate.name == "or":
                    newargs2 += arg.args
                else:
                    newargs2.append(arg)
        else:
            newargs2 = newargs
        return App(predicate=newpred, args=newargs2, type=expr.type)
    elif isinstance(expr, Variable) or isinstance(expr, Constant):
        return expr
    else:
        assert False, "wrong expr %s" % expr
