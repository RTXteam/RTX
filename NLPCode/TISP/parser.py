"""Type-driven Incremental Semantic Parser."""

__author__ = 'kzhao'

import sys
LOGS = sys.stderr

import gflags as flags
FLAGS = flags.FLAGS

flags.DEFINE_integer("beam", 16, "beam size", short_name="b")
flags.DEFINE_boolean("dp", False, "dynamic programming")

from lambda_expr import TypeSystem
_TS = TypeSystem()

from lambda_expr import App, Variable, Lambda, LambdaExprParser, simplify_expr
from parsing_state import State


class Parser(object):
    """semantic parser"""

    postagmap = {"VBG": "VB", "VBZ": "VB", "VBN": "VB", "VBP": "VB", "VBD": "VB"}

    def __init__(self, indepKB, KB, model, State):
        self.indepKB = indepKB
        self.KB = KB
        self.model = model
        self.State = State

        self.beamwidth = FLAGS.beam
        self.beam = None

        self.dp = FLAGS.dp

    def preprocess(self, string):
        return [(w, (Parser.postagmap[p] if p in Parser.postagmap else p)) for (w,p) in string]

    def parse(self, string, filter_func=None, verbose=False):
        string = self.preprocess(string)

        self.State.setup(indepKB=self.indepKB, KB=self.KB, string=string, model=self.model)

        if verbose:
            print >> LOGS, string

        beamlen = len(string) * 2

        self.beam = [[] for i in xrange(beamlen)]
        self.beam[0].append(self.State.initstate())

        for step in xrange(beamlen):

            self.beam[step] = sorted(self.beam[step])
            workingbeam = []

            if self.dp:
                tmpbeam = {}
                for j, candidate in enumerate(self.beam[step]):
                    if candidate not in tmpbeam:
                        tmpbeam[candidate] = candidate
                        workingbeam.append(candidate)
                    else:
                        tmpbeam[candidate].mergewith(candidate)
                    if self.beamwidth > 0 and j == self.beamwidth - 1:
                        break
            else:
                if self.beamwidth > 0:
                    workingbeam = self.beam[step][:self.beamwidth]
                else:
                    workingbeam = self.beam[step]

            if verbose:
                print >> LOGS, "========== step %d (%d)==========" % (step, len(workingbeam))
                for item in self.beam[step]:
                    print >> LOGS, item, "|", item.s0[1], item.score, "|", item.extrainfo
                    if item.incomings != []:
                        print >> LOGS, "\t", item.incomings[0][0], \
                            item.incomings[0][0].extrainfo if item.incomings[0][0] else None
                        print >> LOGS, "\t", item.incomings[0][1], \
                            item.incomings[0][1].extrainfo if item.incomings[0][1] else None
                        print >> LOGS, "\t\t", (item.leftptrs[0], item.leftptrs[0].extrainfo) if item.leftptrs else None

            candidates = []
            for s in workingbeam:
                if type(s) == list:
                    print >> LOGS, s
                candidates += s.proceed()

            for c in candidates:
                if filter_func:
                    if filter_func(c.extrainfo) and c.step < beamlen:
                        self.beam[c.step].append(c)
                elif c.step < beamlen:
                    self.beam[c.step].append(c)

        return self.beam[-1][0] if len(self.beam[-1]) > 0 else None


class ExprGenerator(object):
    """Generates lambda expressions with given actions."""

    _and_expr = None
    _or_expr = None
    _t_type = None

    @staticmethod
    def setup():
        parser = LambdaExprParser()
        ExprGenerator._t_type = parser.parse_type("t")[0]
        ExprGenerator._and_expr = parser.parse("and:<t*,t>")[0]
        ExprGenerator._or_expr = parser.parse("or:<t*,t>")[0]

    @staticmethod
    def shift(state, expr):
        state.extrainfo = expr

    @staticmethod
    def reduce(state, func, arg):
        if arg is None:
            state.extrainfo = func
        else:
            if func is None:
                print >> LOGS, func, arg
                print >> LOGS, state.incomings[0][0], state.incomings[0][0].s0, \
                    state.incomings[0][0].extrainfo
                print >> LOGS, state.incomings[0][1], state.incomings[0][1].s0, \
                    state.incomings[0][1].extrainfo
                for s in state.trace_states():
                    print >> LOGS, s, s.leftptrs, s.incomings
            state.extrainfo = func.reduce_with(arg)

    @staticmethod
    def union(state, funcname, type, arg1, arg2):
        newvar = Variable.get_anonymous_var(type=type.fromtype)
        expr1 = App(predicate=arg1, args=[newvar], type=ExprGenerator._t_type)
        expr2 = App(predicate=arg2, args=[newvar], type=ExprGenerator._t_type)
        if funcname == "and":
            state.extrainfo = Lambda(var=newvar,
                                     body=App(predicate=ExprGenerator._and_expr,
                                              args=[expr1, expr2], type=ExprGenerator._t_type),
                                     type=type).reduce()
        elif funcname == "or":
            state.extrainfo = Lambda(var=newvar,
                                     body=App(predicate=ExprGenerator._or_expr,
                                              args=[expr1, expr2], type=ExprGenerator._t_type),
                                     type=type).reduce()
        else:
            assert False, "wrong union %s" % funcname


def decode_sentence(kb, sentid, weightfile):
    indepkb = IndepKnowledgeBase()
    model = Model()

    parser = Parser(indepkb, kb, model, State)

    State.model = model
    State.model.weights = pickle.load(open(weightfile))
    State.ExtraInfoGen = ExprGenerator
    ExprGenerator.setup()

    ret = parser.parse(kb.questions[sentid])
    print >> LOGS, "============================="
    print >> LOGS, simplify_expr(ret.get_expr())
    print >> LOGS, "TRACING"
    for s in ret.trace_states():
        print >> LOGS, s, s.extrainfo

if __name__ == "__main__":
    from indep_knowledgebase import IndepKnowledgeBase
    from geoquery import GeoQuery
    from model import Model
    import pickle

    flags.DEFINE_integer("sentid", 0, "sentence to decode")
    flags.DEFINE_string("eval", None, "which parameter settings to evaluate")
    FLAGS(sys.argv)

    sentid = FLAGS.sentid
    weightfile = FLAGS.eval

    decode_sentence(GeoQuery(), sentid, weightfile)
