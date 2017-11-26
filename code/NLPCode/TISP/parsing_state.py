"""State in the incremental parsing, also called parsing configuration."""

__author__ = 'kzhao'

import sys
logs = sys.stderr

import traceback

from lambda_expr import TypeSystem, Lambda, ComplexType, AtomicType, TypeEnv, TypeVariable

_TS = TypeSystem()


class State(object):
    """Parsing State
    Each state is a hyper node in the parsing hypergraph.
    Each state only maintains its type, which is used to determine reduce direction.

    In forced decoding, additional information contains the logical expr;
    """
    __slots__ = ["i", "j", "step", "incomings", "leftptrs", "action",
                 "match", "s0", "extrainfo", "state_id",
                 "skipped_words", "leftmost_skipped",
                 "action_info",  # for sh, the expr; for re, reduce type (left/right/union)
                 "inside", "shiftcost", "score", "actioncost",
                 "feat_s0", "feat_s1", "feat_s2", "feat_q0", "feat_q1", "feat_q2",
                 "feat_s0tp", "feat_s1tp", "feat_s2tp", "ruleid",
                 "_signature", "_hash", "mergedwith"]

    actionmaps = {0: "SHIFT", 1: "REDUCE", 2: "SKIP"}
    epsilon = 1e-8
    match_cache = {}

    ExtraInfoGen = None

    indepKB = None
    KB = None
    string = None
    model = None
    state_id_allocated = None

    @staticmethod
    def setup(indepKB, KB, string, model):
        State.indepKB = indepKB
        State.KB = KB
        State.string = string
        State.model = model
        State.state_id_allocated = 0

    @staticmethod
    def initstate():
        return State(step=0, i=-1, j=0, leftptrs=[], incomings=[], s0=None, action=0)

    def __init__(self, step, i, j, leftptrs, incomings, s0, action):
        """incomings is always a list of pairs (a, b),
        where a is the direct parent state of self;
        b is the state being reduced with a to generate self.
        b is None for shifted state
        """
        self.step = step
        self.i = i
        self.j = j
        self.leftptrs = leftptrs
        self.incomings = incomings
        self.s0 = s0 if s0 is not None else (None, TypeEnv())
        self.action = action

        self.shiftcost = 0
        self.inside = 0
        self.score = 0
        self.actioncost = 0
        self.match = (State.model.none_sym, State.model.none_sym)
        self.extrainfo = None
        self.skipped_words = None
        self.leftmost_skipped = None
        self.ruleid = None
        self.action_info = None

        self._signature = None
        self._hash = None

        self.state_id = State.state_id_allocated
        State.state_id_allocated += 1

        _TS.TE = self.s0[1]

        self.feat_s0 = (State.string[i] if i >= 0 else (State.model.start_sym, State.model.start_sym),
                        State.string[j-1] if j > 0 else (State.model.start_sym, State.model.start_sym))
        self.feat_s0tp = self.s0[0].anonymous_str() if self.s0[0] else State.model.none_sym

        if self.leftptrs and self.leftptrs != []:
            self.feat_s1 = self.leftptrs[0].feat_s0
            self.feat_s2 = self.leftptrs[0].feat_s1
            self.feat_s1tp = self.leftptrs[0].feat_s0tp
            self.feat_s2tp = self.leftptrs[0].feat_s1tp
        else:
            self.feat_s1 = ((State.model.start_sym, State.model.start_sym), (State.model.start_sym, State.model.start_sym))
            self.feat_s2 = ((State.model.start_sym, State.model.start_sym), (State.model.start_sym, State.model.start_sym))
            self.feat_s1tp = State.model.none_sym
            self.feat_s2tp = State.model.none_sym

        self.feat_q0 = State.string[j] if j < len(State.string) else (State.model.end_sym, State.model.end_sym)
        self.feat_q1 = State.string[j+1] if j+1 < len(State.string) else (State.model.end_sym, State.model.end_sym)
        self.feat_q2 = State.string[j+2] if j+2 < len(State.string) else (State.model.end_sym, State.model.end_sym)

    def signature(self):
        if self._signature is None:
            self._signature = (self.i, self.j,
                self.feat_s0[0], self.feat_s0[1],
                self.feat_s1[0], self.feat_s1[1],
                self.feat_s2[0], self.feat_s2[1],
                self.feat_s0tp, self.feat_s1tp, self.feat_s2tp,
                self.match[0], self.match[1], self.ruleid)
        return self._signature

    def __hash__(self):
        if self._hash is None:
            self._hash = hash(self.signature())
        return self._hash

    def __eq__(self, other):
        return self.signature() == other.signature()

    def mergewith(self, other):
        if self.score + State.epsilon < other.score:
            print >> logs, "wrong order after sort self %f other %f" % (self.score, other.score)
            assert False
        if self.action != 1:  # SHIFT or SKIP
            other.mergedwith = self
            if self.leftptrs is None:
                assert other.leftptrs is None
            else:
                self.leftptrs.append(other.leftptrs[0])  # assert len(other.leftptrs) == 1
        self.incomings.append(other.incomings[0])

    def rerank_incomings(self):
        actioncost = State.model.eval_feats(action=self.action,
                                            feats=self.make_feats())
        self.actioncost = actioncost
        scores = [(self.evaluate_incoming(incoming), incoming) for incoming in self.incomings]
        scores = sorted(scores, reverse=True)
        self.incomings = [incoming for _, incoming in scores]
        self.score, self.inside, self.shiftcost = self.evaluate_incoming(self.incomings[0])
        # we don't rerank leftstates

    def evaluate_incoming(self, incoming):
        """
        evaluate the score with a given incoming hyperedge of (parent, leftstate)
        """
        shiftcost = 0
        score = 0
        inside = 0
        actioncost = self.actioncost
        if self.action == 0:  # shift
            shiftcost = actioncost
            score = incoming[0].score + actioncost
            inside = 0
        elif self.action == 1:  # app
            # self = reduce(leftstate, parent)
            # incoming = (parent, leftstate)
            shiftcost = incoming[1].shiftcost  # from leftstate
            inside = incoming[1].inside + incoming[0].inside + incoming[0].shiftcost + actioncost
            score = incoming[1].score + incoming[0].inside + incoming[0].shiftcost + actioncost
        elif self.action == 2:  # skip, behaves like a shift+reduce
            shiftcost = incoming[0].shiftcost
            inside = incoming[0].inside + actioncost
            score = incoming[0].score + actioncost
        else:
            assert False
        return score, inside, shiftcost

    def __cmp__(self, other):
        return 1 if other.score - self.score > State.epsilon else \
            -1 if self.score - other.score > State.epsilon else \
            1 if other.inside - self.inside > State.epsilon else \
            -1 if self.inside - other.inside > State.epsilon else 0

    def evaluate(self):
        self.actioncost = State.model.weights.dot(self.make_feats())
        #self.actioncost = State.model.eval_feats(action=self.action, feats=self.make_feats())

        self.score, self.inside, self.shiftcost = self.evaluate_incoming(self.incomings[0])

    def is_shiftable(self):
        return self.j < len(State.string)

    def shift(self, given_candidates=None):
        """push the next word in queue onto the stack"""

        word, pos = State.string[self.j]
        if given_candidates is None:
            candidates = []  # candidates is a list of (expr, te)
            if pos == "NP":
                candidates = [(expr, te, ruleid) for _, expr, te, ruleid in self.KB.fetch_NNP(word)]
            elif pos == "PAT":
                candidates = self.indepKB.fetch_pattern(word)
            elif pos in self.indepKB.postags:
                candidates = self.indepKB.fetch_postag(pos)
        else:
            candidates = given_candidates

        covered_words = [word]
        leftmost = self.leftmost_skipped

        ret = []

        for (expr, te, ruleid) in candidates:
            for retexpr, rette, retmatch in self.match_expr(expr, te, covered_words, ruleid):
                if len(retmatch) == 0:
                    match = (State.model.none_sym, State.model.none_sym)
                elif len(retmatch) == 1:
                    match = (retmatch[0], State.model.none_sym)
                elif len(retmatch) == 2:
                    match = (retmatch[0], retmatch[1])
                else:
                    assert False, "wrong number of matches"

                newstate = State(step=self.step+1, i=self.j, j=self.j+1, leftptrs=[self],
                                 incomings=[(self, None)], s0=(retexpr.type, rette), action=0)
                newstate.match = match
                newstate.ruleid = ruleid
                newstate.action_info = retexpr
                newstate.gen_extra_info()

                newstate.evaluate()
                ret.append(newstate)
        return ret

    def match_expr(self, expr, te, covered_words, ruleid=None):
        """grounding the given expr for given covered_words"""
        cache = False
        if cache and ruleid and (ruleid, covered_words) in State.match_cache:
            ret = []
            for retexpr, rette, retmatch in State.match_cache[(ruleid, covered_words)]:
                tvmapping = {}
                vmapping = {}
                ret.append((retexpr.duplicate(vmapping, tvmapping), rette.duplicate(tvmapping), retmatch))
            return ret
        ret = []
        if isinstance(expr, Lambda) and expr.var.name.startswith("$P"):
            args = self.KB.fetch_predicates(expr.var.type, te, covered_words)
            for pred, predte, match in args:
                reducete = te.merge(predte)
                _TS.TE = reducete
                if _TS.is_reducible(func=expr.type, arg=pred.type):
                    result = expr.reduce_with(pred)
                    subret = self.match_expr(result, reducete, covered_words, None)
                    for subexpr, subte, submatch in subret:
                        ret.append((subexpr, subte, [match] + submatch))
        else:
            ret = [(expr, te, [])]
        if cache and ruleid:
            State.match_cache[(ruleid, covered_words)] = ret
        return ret

    def extend_covered_words(self, all_skipped, new_word):
        word, pos = new_word
        if any(pos.startswith(x) for x in ["VB", "JJ", "RB", "NN", "IN"]):
            if all_skipped is None:
                return word
            else:
                return "%s_%s" % (all_skipped, word)
        else:
            return all_skipped

    def skip(self):
        """skip current word"""
        newstate = State(step=self.step+2, i=self.i, j=self.j+1,
                         leftptrs=self.leftptrs, incomings=[(self, None)],
                         s0=self.s0, action=2)
        if self.action == 2:
            newstate.leftmost_skipped = self.leftmost_skipped
        else:
            newstate.leftmost_skipped = newstate
        newstate.skipped_words = self.extend_covered_words(self.skipped_words, State.string[self.j])
        newstate.gen_extra_info()
        newstate.evaluate()
        return [newstate]

    def is_reducible(self):
        return len(self.leftptrs) > 0 and self.leftptrs[0].s0[0]

    def reduce_with(self, leftstate):
        """reduce with a given leftstate
        handles following cases:
            reduce with a skipped state
            left/right reduce
            union
        """
        if leftstate.i == -1:  # leftstate is INIT
            return []
        ret = []
        s0, s0te = self.s0
        s1, s1te = leftstate.s0
        try:
            newte = s0te.merge(s1te)
        except:
            print >> logs, "merge TE error"
            print >> logs, "s0", s0, s0te
            print >> logs, "s1", s1, s1te
            print >> logs, "s0 expr", self.get_expr()
            print >> logs, "s1 expr", leftstate.get_expr()
            print >> logs, "s0 traceback"
            for s in self.trace_states():
                expr = s.get_expr()
                print >> logs, "\t", s, s.s0, expr.fulltype_str() if expr else None

            def collect_tv(t_):
                if isinstance(t_, TypeVariable):
                    return [t_]
                elif isinstance(t_, ComplexType):
                    return collect_tv(t_.fromtype) + collect_tv(t_.totype)
                else:
                    return []
            print >> logs, "---", s0
            for t in collect_tv(s0):
                print >> logs, t, id(t)
            print >> logs, "---", s1
            for t in collect_tv(s1):
                print >> logs, t, id(t)
            raise Exception("".join(traceback.format_exception(*sys.exc_info())))

        _TS.TE = newte

        if _TS.is_reducible(func=s1, arg=s0) or (s1 and s0 is None):
            news0 = s1 if s0 is None else s1.totype
            newstate = State(step=self.step+1, i=leftstate.i, j=self.j,
                             leftptrs=leftstate.leftptrs, incomings=[(self, leftstate)],
                             s0=(news0, newte), action=1)
            newstate.match = (State.model.none_sym, State.model.none_sym)
            newstate.action_info = "left"
            newstate.gen_extra_info()
            ret.append(newstate)
        elif _TS.is_reducible(func=s0, arg=s1) or (s0 and s1 is None):
            news0 = s0 if s1 is None else s0.totype
            newstate = State(step=self.step+1, i=leftstate.i, j=self.j,
                             leftptrs=leftstate.leftptrs, incomings=[(self, leftstate)],
                             s0=(news0, newte), action=1)
            newstate.match = (State.model.none_sym, State.model.none_sym)
            newstate.action_info = "right"
            newstate.gen_extra_info()
            ret.append(newstate)
        elif isinstance(s0, ComplexType) and \
                (isinstance(s0.fromtype, AtomicType) or isinstance(s0.fromtype, TypeVariable)) and \
                isinstance(s0.totype, AtomicType) and s0.totype.type == "t" and \
                isinstance(s1, ComplexType) and \
                (isinstance(s1.fromtype, AtomicType) or isinstance(s1.fromtype, TypeVariable)) and \
                isinstance(s1.totype, AtomicType) and s1.totype.type == "t" and \
                (s1.fromtype == s0.fromtype or s1.fromtype <= s0.fromtype or s0.fromtype <= s1.fromtype):
            match_and = ("and", State.model.none_sym)
            match_or = ("or", State.model.none_sym)
            _TS.TE = newte
            news0 = ComplexType(fromtype=(s0.fromtype if s0.fromtype <= s1.fromtype else s1.fromtype),
                                totype=s0.totype)
            for m in [match_and, match_or]:
                newstate = State(step=self.step+1, i=leftstate.i, j=self.j,
                                 leftptrs=leftstate.leftptrs, incomings=[(self, leftstate)],
                                 s0=(news0, newte), action=1)
                newstate.match = m
                newstate.action_info = m[0]
                newstate.gen_extra_info()
                ret.append(newstate)
        return ret

    def reduce(self):
        ret = []
        for leftstate in self.leftptrs:
            ret += self.reduce_with(leftstate)
        for r in ret:
            r.evaluate()
        return ret

    def proceed(self):
        ret = []
        if self.is_shiftable():
            ret += self.shift()
            ret += self.skip()
        if self.is_reducible():
            ret += self.reduce()
        return ret

    def get_atomic_feats(self):
        return [self.feat_q0, self.feat_q1, self.feat_q2,
                self.feat_s0[0], self.feat_s0[1],
                self.feat_s1[0], self.feat_s1[1],
                self.feat_s2[0], self.feat_s2[1],
                self.feat_s0tp, self.feat_s1tp, self.feat_s2tp,
                self.match[0], self.match[1], self.ruleid]

    def make_feats(self):
        """ return a list of feats """
        stdfeats = State.model.eval_module.static_eval(*(self.get_atomic_feats()))
        additionalfeats = []
        ret = State.model.new_weights()
        ret = ret.iaddl(self.action, stdfeats)

        matchscore = 0.0
        if self.action == 0 and self.i >= 0:
            word, tag = State.string[self.i]
            if tag[0] in ["N", "V", "J", "R"]:
                if word in State.KB.adjs:
                    word = State.KB.adjs[word]
                if word in State.KB.pmi:
                    pmi = State.KB.pmi[word]
                    if self.match[0] in pmi:
                        matchscore += pmi[self.match[0]]
                    if self.match[1] in pmi:
                        matchscore += pmi[self.match[1]]
        ret[self.action].iaddl(["match"], matchscore)

        for idx in xrange(self.j-3, self.j):
            word = State.string[idx][0] if idx > 0 else State.model.none_sym
            additionalfeats.append("match0=%s-%s" % (word, self.match[0]))
            additionalfeats.append("match1=%s-%s" % (word, self.match[1]))
        ret.iaddl(self.action, additionalfeats)

        return ret

    def __str__(self):
        _TS.TE = self.s0[1]
        if self.s0[0] is None:
            return "%s@%s[%d]" % (("SKIP_%s" % State.string[self.j-1][0]) if self.action == 2
                                   else "INIT", self.step, self.state_id)
        ret = "%s_%s@%d[%d]:(%d,%d)" % (State.actionmaps[self.action],
                                         (State.string[self.j-1][0] if self.action == 0 or self.action == 2 else ""),
                                         self.step, self.state_id, self.i, self.j)
        if self.action == 0:
            ret += ":"
            ret += ":".join(self.match)
        return ret

    __repr__ = __str__

    def trace_states(self):
        if not self.incomings:
            return []
        elif self.incomings[0][1] is None:
            return self.incomings[0][0].trace_states() + [self]
        else:
            return self.incomings[0][1].trace_states() + \
                self.incomings[0][0].trace_inside_states() + [self]

    def trace_inside_states(self):
        if not self.incomings:  # init
            return []
        elif self.action == 0:  # shift
            return [self]
        elif self.action == 2:  # skip
            return self.incomings[0][0].trace_inside_states() + [self]
        else:  # reduce
            return self.incomings[0][1].trace_inside_states() + \
                self.incomings[0][0].trace_inside_states() + [self]

    def recover_feats(self):
        if self.incomings:
            myfeats = self.make_feats()
            feats = None
            if self.incomings[0][1]:  # from leftstate
                leftfeats = self.incomings[0][1].recover_feats()
                rightfeats = self.incomings[0][0].recover_inside_feats()
                feats = leftfeats.iadd(myfeats)
                feats = feats.iadd(rightfeats)
            else:  # for shift and skip
                prevfeats = self.incomings[0][0].recover_feats()
                feats = prevfeats.iadd(myfeats)
            return feats
        else:
            # for INIT@0
            return self.model.new_weights()

    def recover_inside_feats(self):
        if self.incomings:
            myfeats = self.make_feats()
            feats = None
            if self.incomings[0][1]:
                leftfeats = self.incomings[0][1].recover_inside_feats()
                rightfeats = self.incomings[0][0].recover_inside_feats()
                feats = leftfeats.iadd(myfeats)
                feats = feats.iadd(rightfeats)
            else:
                if self.action == 0:  # shift:
                    feats = self.model.new_weights()
                elif self.action == 2:  # skip:
                    feats = self.incomings[0][0].recover_inside_feats()
                feats.iadd(myfeats)
            return feats
        else:
            return self.model.new_weights()

    def forced_proceed(self, action, match, ruleid, leftstate):
        """generate decendent state."""
        if action == 0:
            _, expr, te = self.KB.fetch_ruleid(ruleid)
            if expr is None:
                expr, te = self.indepKB.fetch_ruleid(ruleid)
            assert expr
            ret = self.shift(given_candidates=[(expr, te, ruleid)])
            ret = [x for x in ret if x.match == match]
            if len(ret) != 1:
                print >> logs, "ret", len(ret)
                print >> logs, "self", self
                print >> logs, "given", expr, ruleid
                for s in ret:
                    print >> logs, s, s.match
                assert False
            return ret[0]
        elif action == 1:
            reduceresult = [x for x in self.reduce_with(leftstate) if x.match == match]
            assert len(reduceresult) == 1
            return reduceresult[0]
        elif action == 2:
            return self.skip()[0]

    def gen_extra_info(self):
        if State.ExtraInfoGen:
            if self.action == 0:
                State.ExtraInfoGen.shift(self, self.action_info)
            elif self.action == 1:
                parent, leftstate = self.incomings[0]
                if self.action_info == "left":
                    State.ExtraInfoGen.reduce(state=self, func=leftstate.extrainfo, arg=parent.extrainfo)
                elif self.action_info == "right":
                    State.ExtraInfoGen.reduce(state=self, func=parent.extrainfo, arg=leftstate.extrainfo)
                elif self.action_info == "and" or self.action_info == "or":
                    State.ExtraInfoGen.union(state=self, funcname=self.action_info, type=self.s0[0],
                                                arg1=leftstate.extrainfo, arg2=parent.extrainfo)
            else:
                self.extrainfo = self.incomings[0][0].extrainfo if self.i != -1 else None

    def get_expr(self):
        deriv = self.trace_states()
        for s in deriv:
            s.gen_extra_info()
        return deriv[-1].extrainfo
