#!/usr/bin/env python

"""Forced decoding using given model parameters.

Searches through the forced decoding space, where every derivaiton is ccorrect,
to find correct derivations leading to the reference meaning representation.
"""

__author__ = 'kaizhao'

import sys
logs = sys.stderr

import time
from multiprocessing import Pool, cpu_count
import pickle

from utils import timeout, TimeoutError

from indep_knowledgebase import IndepKnowledgeBase
from model import Model
from parsing_state import State
from knowledgebase import KnowledgeBase
from parser import Parser, ExprGenerator

from lambda_expr import collect_constants, TypeEnv, TypeSystem, simplify_expr

_TS = TypeSystem()

TIMEOUT = 60


class ConstraintKB(KnowledgeBase):

    __builtin_constant__ = ["and", "argmax", "argmin", "count", "exists", "not"]
    __collapsable_constants__ = ["and", "argmax", "argmin", "count", "exists", "not"]

    def __init__(self, kb, predicates):
        """ kb is a normal knowledgebase, e.g., GeoQuery, whose typing will be used
            predicates is a list of predicates (predicate_name, Type) that can be fetched
        """

        self.kb = kb

        self.predicates = []

        for (p, te) in predicates:
            if p.name in self.kb.predicate2annotation:
                annotation = self.kb.predicate2annotation[p.name]
                self.predicates.append((p, te, annotation))

        self.nnps = self.kb.nnps


class ForcedDecoder(object):
    """forced decoding"""

    def __init__(self, kb):
        ExprGenerator.setup()
        State.ExtraInfoGen = ExprGenerator
        ForcedDecoder.model = Model()
        ForcedDecoder.indepKB = IndepKnowledgeBase()
        ForcedDecoder.KB = kb
        kb.postedit_indepkb(ForcedDecoder.indepKB)
        ForcedDecoder.parser = Parser(ForcedDecoder.indepKB, ForcedDecoder.KB, ForcedDecoder.model, State)
        ForcedDecoder.questions = kb.questions
        ForcedDecoder.logicalexprs = kb.logicalexprs
        ForcedDecoder.verbose = False

    @timeout(seconds=TIMEOUT)
    def timed_decode(self, args):
        ret = (0, [])
        is_timeout = False
        start_t = time.time()
        try:
            ret = self.decode(args)
        except TimeoutError:
            is_timeout = True
        except:
            ret = (0, {})
        end_t = time.time()
        print >> logs, "finish", args
        return ret, is_timeout, end_t-start_t

    def decode(self, sentid):
        string = ForcedDecoder.questions[sentid]
        goldexpr = ForcedDecoder.logicalexprs[sentid]

        if ForcedDecoder.verbose:
            print >> logs, string
            print >> logs, goldexpr

        _TS.TE = goldexpr[1]

        constant_unigrams, constant_bigrams = collect_constants(goldexpr[0])

        constant_bigrams.add(('and', 'and'))
        constant_bigrams.add(('or', 'or'))

        if ForcedDecoder.verbose:
            print >> logs, constant_unigrams
            print >> logs, constant_bigrams

        predicate_candidates = sorted([(expr, TypeEnv()) for expr in constant_unigrams if expr.name not in ConstraintKB.__builtin_constant__],
                                      key=lambda t: t[0].name)
        constant_unigram_names = set(c.name for c in constant_unigrams)

        cKB = ConstraintKB(ForcedDecoder.KB, predicate_candidates)
        cKB.adjs = ForcedDecoder.KB.adjs
        cKB.pmi = ForcedDecoder.KB.pmi

        ForcedDecoder.parser.KB = cKB

        def filter_expr(expr):
            if expr:
                u, b = collect_constants(expr)
                if any(c.name not in constant_unigram_names for c in u):
                    return False
                return b.issubset(constant_bigrams)
            return True

        ForcedDecoder.parser.parse(string, filter_func=filter_expr, verbose=ForcedDecoder.verbose)

        matches = []

        if ForcedDecoder.verbose:
            print >> logs, "========== checking last beam step =========="

        for candidate in ForcedDecoder.parser.beam[-1]:
            if candidate.extrainfo:
                r = simplify_expr(candidate.extrainfo)
                if r.semantic_eq(goldexpr[0]):
                    matches.append(candidate)
                else:
                    pass

        if ForcedDecoder.verbose:
            print >> logs, "========== %d matches ==========" % len(matches)

            for candidate in matches:
                print >> logs, candidate.trace_states()

        hg = {}  # hypergraph, each item is state_id -> (action, match, incomings)
        for candidate in matches:
            for s in candidate.trace_states():
                if s.state_id not in hg:
                    incomings = []
                    for (n1, n2) in s.incomings:
                        n1id = n1.state_id if n1 else None
                        n2id = n2.state_id if n2 else None
                        if ((n1id and n1id in hg) or not n1id) and \
                                ((n2id and n2id in hg) or not n2id):
                            incomings.append((n1id, n2id))
                        else:
                            print >> logs, s.state_id
                            print >> logs, n1id, n2id, hg.keys()
                            print >> logs, s.trace_states()
                            assert False
                    hg[s.state_id] = (s.action, s.match, s.ruleid, incomings)

        return len(matches), hg

    def parallel_decode(self, sentids):
        """ trainingset is a list of (string, goldexpr) """

        ncpus = cpu_count()
        pool = Pool(processes=ncpus, maxtasksperchild=1)

        if FLAGS.beam == 0:
            results = pool.map(self.timed_decode, sentids)
        else:
            results = pool.map(self.decode, sentids)
            results = [(x, False, 0) for x in results]

        return results


def forced_decode_corpus(KB, sentids, weightfile):
    print >> logs, "forced decode %d sentences" % len(sentids)
    fd = ForcedDecoder(KB)

    if weightfile:
        ForcedDecoder.model.weights = pickle.load(open(weightfile))
        print >> logs, "weight file loaded, len", len(ForcedDecoder.model.weights)

    start_t = time.time()
    if len(sentids) == 1:
        ForcedDecoder.verbose = True
        results = [(fd.decode(sentids[0]), False, 0)]
    else:
        results = fd.parallel_decode(sentids)
    end_t = time.time()

    succ_count = 0
    hgs = {}
    for sentid, ((c, hg), is_timeout, t) in zip(sentids, results):
        if c == 0:
            print >> logs, "sent %d failed, timeout %s time %f s: %s" % (sentid, str(is_timeout), t, KB.questions[sentid])
        else:
            succ_count += 1
            hgs[sentid] = hg

    print >> logs, "all done, %d/%d succ, taking %f s" % (succ_count, len(sentids), (end_t - start_t))

    if FLAGS.output:
        pickle.dump(hgs, open(FLAGS.output, "w"), pickle.HIGHEST_PROTOCOL)
        print >> logs, "%d hgs dumped" % len(hgs)


if __name__ == "__main__":
    from geoquery import GeoQuery

    flags.DEFINE_string("dataset", "train", "which dataset (train/dev/test) to forced decode")
    flags.DEFINE_string("corpus", "geoquery", "which corpus to decode")
    flags.DEFINE_string("eval", None, "which parameter settings to evaluate")
    flags.DEFINE_string("output", None, "output hg file")

    FLAGS(sys.argv)

    weightfile = FLAGS.eval

    KB = GeoQuery()

    if FLAGS.dataset == "train":
        sentids = range(KB.trainsize)
    elif FLAGS.dataset == "dev":
        sentids = range(KB.trainsize, KB.trainsize + KB.devsize)
    elif FLAGS.dataset == "test":
        sentids = range(KB.trainsize + KB.devsize, KB.trainsize + KB.devsize + KB.testsize)
    elif FLAGS.dataset.isdigit():
        sentids = [int(FLAGS.dataset)]
    else:
        sentids = [int(x) for x in open(FLAGS.dataset).readlines()]

    forced_decode_corpus(KB, sentids, weightfile)
