"""Parses a string of lambda calculus expression, returns an expression defined in lambda_expr."""

__author__ = 'kzhao'

from pyparsing import Word, nums, Combine, OneOrMore, Forward, Suppress, alphanums, Optional

from utils import Singleton
from type import TypeSystem, ComplexType, TypeEnv
from lambda_expr import Variable, Constant, App, Lambda, TypeInferer

_TS = TypeSystem()


class LambdaExprParser(object):
    """Lambda expression parser."""
    __metaclass__ = Singleton

    def __init__(self):
        self.TS = TypeSystem()
        self.TE = None
        self.type_var_names = None  # used for retrieving type variable for a given name
        self._type_grammar, self._grammar = self.init_grammar()

    def get_type_variable_by_name(self, name):
        """return the type variable with the given name;
        if it does not exist, create a new type variable
        """
        if name not in self.type_var_names:
            tv = self.TS.get_type_variable(name)
            self.TE[tv] = self.TS.get_root_atomic_type()
            self.type_var_names[name] = tv
        return self.type_var_names[name]

    def init_grammar(self):
        """define the grammar for types and lambda expressions"""

        def type_handler(v):
            v_ = v.asList()
            if len(v_) == 1:
                if v_[0][-1] == "*":  # list type
                    return self.TS.get_list_type(v_[0][:-1])
                else:  # atomic type or type variable
                    return self.get_type_variable_by_name(v_[0]) if v_[0][0].isupper() \
                        else self.TS.get_atomic_type(v_[0])
            else:  # complex type
                return self.TS.get_complex_type(v_[0], v_[1])

        def var_handler(v):
            return Variable(name=v[0])

        def const_handler(v):
            v = v.asList()
            return Constant(name=v[0], type=v[1])

        def app_handler(v):
            v = v.asList()
            args = v[1:]
            return App(predicate=v[0], args=args, type=None)

        def lambda_handler(v):
            v = v.asList()
            var = v[0]
            var.type = v[1]
            return Lambda(var=var, body=v[2], type=None)

        intexpr = Word(nums)
        varnameexpr = Word(nums+"P")
        realexpr = Combine(Word(nums) + "." + Word(nums))

        colon = Suppress(":")

        typeexpr = Forward()
        typeexpr << (Combine(Word(alphanums+"_") + Optional("*")) |
                     (Suppress("<") + typeexpr + Suppress(",") + typeexpr + Suppress(">")))

        typeexpr.setParseAction(type_handler)

        varexpr = Combine("$"+varnameexpr)
        varexpr.setParseAction(var_handler)

        identifierexpr = Word(alphanums+"-"+"_"+"<"+">"+"=")

        constexpr = (intexpr + colon + typeexpr) | \
                    (realexpr + colon + typeexpr) | \
                    (identifierexpr + colon + typeexpr)
        constexpr.setParseAction(const_handler)

        appexpr = Forward()
        lambdaexpr = Forward()
        argexpr = (varexpr | constexpr | appexpr | lambdaexpr)
        appexpr << (Suppress("(") + (constexpr | lambdaexpr | varexpr) + OneOrMore(argexpr) + Suppress(")"))
        lambdaexpr << (Suppress("(") + Suppress("lambda") + varexpr + colon + typeexpr +
                       (appexpr | lambdaexpr | varexpr) + Suppress(")"))

        appexpr.setParseAction(app_handler)
        lambdaexpr.setParseAction(lambda_handler)

        expr = appexpr | lambdaexpr | constexpr

        return typeexpr, expr

    def parse_type(self, input_str):
        self.type_var_names = {}
        self.TE = TypeEnv()
        _TS.TE = self.TE
        return self._type_grammar.parseString(input_str)[0], self.TE

    def parse(self, input_str):
        self.type_var_names = {}
        self.TE = TypeEnv()
        _TS.TE = self.TE
        expr = self._grammar.parseString(input_str)[0]
        TypeInferer.infer_type(expr)
        return expr, _TS.TE


def _test():
    parser = LambdaExprParser()

    print "============== testing types ==============="
    print "setting c <: b <: a"
    ta = parser.parse_type("a")[0]
    tb = parser.parse_type("b")[0]
    tc = parser.parse_type("c")[0]
    _TS.add_subtype(parent=ta, child=tb)
    _TS.add_subtype(parent=tb, child=tc)
    print "testing b <: a", tb <= ta
    tv, te = parser.parse_type("E")
    _TS.TE = te
    print "type variable tv:", tv
    print "unify tv <: ta", _TS.unify_subtype(parent=ta, child=tv, TE=te)
    print "tv:", tv, _TS.TE[tv]
    print "unify tv <: tb", _TS.unify_subtype(parent=tb, child=tv, TE=te)
    print "tv:", tv, _TS.TE[tv]
    print "unify tc <: tv", _TS.unify_subtype(parent=tv, child=tc, TE=te)
    print "tv:", tv, _TS.TE[tv]

    print "\n============ test exprs ================"
    exprstr1 = "(lambda $P:<E0,E1> (lambda $0:E0 ($P $0)))"
    print "parse", exprstr1
    expr1 = parser.parse(exprstr1)
    print expr1
    print expr1[0].fulltype_str()
    print

    exprstr2 = "(lambda $0:E1 (lambda $1:E1 (and:<t*,t> $0 $1)))"
    print "parse", exprstr2
    expr2, expr2te = parser.parse(exprstr2)
    _TS.TE = expr2te
    print TypeInferer.infer_type(expr2)
    print expr2, expr2.type, expr2te
    print

    print "\n============ test reduce ================"
    exprstr3 = "xy:a"
    expr3 = parser.parse(exprstr3)[0]
    print "reduce %s <-------- %s" % (expr2, expr3)
    expr4 = expr2.reduce_with(expr3)
    print expr4



if __name__ == "__main__":
    _test()
