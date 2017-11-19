"""Wrapper of the GeoQuery dataset."""

__author__ = 'kzhao'

import os
import sys
logs = sys.stderr
from collections import defaultdict
from hashlib import md5
import pickle

import gflags as flags
FLAGS = flags.FLAGS

flags.DEFINE_boolean("stem", True, "use stemmed words")
flags.DEFINE_integer("trainsize", 10, "training set size")
flags.DEFINE_integer("devsize", 5, "development set size")
flags.DEFINE_integer("testsize", 5, "testing set size")

from lambda_expr import TypeSystem, LambdaExprParser, simplify_expr, collect_constants, ComplexType

_TS = TypeSystem()

from knowledgebase import KnowledgeBase

__base_dir__ = "sampledata"

__preds_file__ = __base_dir__ + "/preds"
__types_file__ = __base_dir__ + "/types"
__questions_file__ = __base_dir__ + "/questions"
__exprs_file__ = __base_dir__ + "/logicalexprs"
__nnp_file__ = __base_dir__ + "/nps.txt"
__stem_file__ = __base_dir__ + "/stems.txt"
__adjs_file__ = __base_dir__ + "/adjs.txt"
__pmi_file__ = __base_dir__ + "/pmi.all.pickle"


class GeoQuery(KnowledgeBase):

    def __init__(self):
        # load subtype hierarchy
        for line in open(__types_file__):
            c, p = line.split("\t")[0].replace("(", "").replace(")", "").split()
            parent = _TS.get_atomic_type(p)
            child = _TS.get_atomic_type(c)
            _TS.add_subtype(parent=parent, child=child)

        parser = LambdaExprParser()

        self.nnps = defaultdict(list)
        seennnps = defaultdict(set)
        self.ruleid2rule = {}
        for line in open(__nnp_file__):
            if not line.startswith("//"):
                m = md5()
                m.update(line.strip())
                ruleid = m.hexdigest()
                nnp, _, exprstr = line.strip().split(" :")
                nnp = nnp.strip().replace(" ", "_")
                exprstr = exprstr.strip()
                if exprstr not in seennnps[nnp]:
                    seennnps[nnp].add(exprstr)
                    expr, te = parser.parse(exprstr)
                    # we assign the score to 1.0 in GeoQuery
                    self.nnps[nnp].append((1.0, expr, te, ruleid))
                    if ruleid in self.ruleid2rule:
                        print >> logs, ruleid
                        print >> logs, self.ruleid2rule[ruleid]
                        print >> logs, expr, te
                        assert False
                    self.ruleid2rule[ruleid] = (1.0, expr, te)

        self.predicates = []
        self.predicate2annotation = {}
        seenpredicates = set()
        for line in open(__preds_file__):
            if not line.startswith("//"):
                exprstr, annotation = line.strip().split("\t")
                if exprstr not in seenpredicates:
                    seenpredicates.add(exprstr)
                    expr, te = parser.parse(exprstr)
                    self.predicates.append((expr, te, annotation))
                    self.predicate2annotation[expr.name] = annotation

        self.questions = []

        adjs = {}
        # comparative/superlative => normal
        for line in open(__adjs_file__):
            forms = line.strip().split()
            for f in forms:
                adjs[f] = forms[0]
        self.adjs = adjs
        pmithreshold = 0.01
        self.pmi = pickle.load(open(__pmi_file__))
        for w, pw in self.pmi.iteritems():
            todelete = [p for p in pw if pw[p] < pmithreshold]
            for d in todelete:
                del pw[d]
        for w in [w for w, pw in self.pmi.iteritems() if len(pw) == 0]:
            del self.pmi[w]



        stem = FLAGS.stem

        if stem:
            self.stemming = {}
            if FLAGS.stem:
                for line in open(__stem_file__):
                    w, p, s = line.strip().split("\t")
                    self.stemming[(w, p)] = s

        for line in open(__questions_file__):
            string = []
            for tok in line.strip().split():
                w, t = tok.split("/")
                if stem:
                    if (w, t) in self.stemming:
                        w = self.stemming[(w, t)]
                if w in adjs:
                    w = adjs[w]
                string.append((w, t))
            self.questions.append(string)

        # load logical exprs
        self.logicalexprs = []
        self.expr_unigrams = []
        for line in open(__exprs_file__):
            expr, exprte = parser.parse(line.strip())
            expr = simplify_expr(expr)
            self.expr_unigrams.append(set(x.name if isinstance(x.type, ComplexType)
                                          else str(x) for x in collect_constants(expr)[0]))
            self.logicalexprs.append((expr, exprte))

        self.trainsize = FLAGS.trainsize
        self.devsize = FLAGS.devsize
        self.testsize = FLAGS.testsize

        assert self.trainsize + self.devsize + self.testsize <= len(self.questions)
