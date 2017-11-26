"""PMI is used as an initial feature for lexicon grounding."""

__author__ = 'kaizhao'

import sys
import os
from collections import defaultdict
import cPickle as pickle

import gflags as flags
FLAGS = flags.FLAGS

from lambda_expr import LambdaExprParser, collect_constants, ComplexType


def calc_pmi(datapairs):
    """frequency mutual information"""
    paircount = defaultdict(int)
    wordcount = defaultdict(int)
    constcount = defaultdict(int)

    for words, consts in datapairs:
        for w in words:
            wordcount[w] += 1
        for c in consts:
            c = c[:-1] if c[-1].isdigit() else c
            constcount[c] += 1
        for w in words:
            for c in consts:
                c = c[:-1] if c[-1].isdigit() else c
                paircount[(w, c)] += 1

    ret = defaultdict(lambda: defaultdict(float))
    for (w, c), count in paircount.iteritems():
        ret[w][c] = float(count)*float(count)/wordcount[w]/constcount[c]

    return ret

if __name__ == "__main__":
    flags.DEFINE_string("corpus", None, "corpus path")
    FLAGS(sys.argv)

    corpus = FLAGS.corpus

    stem = "%s/stems.txt" % corpus
    exprfile = "%s/logicalexprs" % corpus
    questionfile = "%s/questions" % corpus
    adjsfile = "%s/adjs.txt" % corpus
    pmifile = "%s/pmi.all.pickle" % corpus

    trainsize = 4473

    if stem:
        stemming = {}
        for line in open(stem):
            w, p, s = line.strip().split()
            stemming[(w, p)] = s

    adjs = {}
    for line in open(adjsfile):
        tup = tuple(line.strip().split())
        for adj in tup:
            adjs[adj] = tup

    datapairs = []

    exprparser = LambdaExprParser()

    sensitive_tags = ["N", "V", "J", "R"]

    for i, (exprline, questionline) in enumerate(zip(open(exprfile), open(questionfile))):
        if i >= trainsize:
            break
        expr = exprparser.parse(exprline.strip())[0]
        unigrams, _ = collect_constants(expr)
        consts = [c.name for c in unigrams if isinstance(c.type, ComplexType)]
        wordtags = [w.rsplit("/", 1) for w in questionline.strip().split()]
        words = [(w, t) for w, t in wordtags if t != "NP"]
        # stemming
        words = [(stemming[(w, t)], t) if (w, t) in stemming else (w, t) for w, t in words]
        # convert comparative and superlative to normal degree
        words = [(adjs[w][0], t) if w in adjs else (w, t) for w, t in words]
        words = [w for w, _ in words]
        datapairs.append((words, consts))

    pmiinfo = calc_pmi(datapairs)

    pickle.dump(pmiinfo, open(pmifile, "w"), pickle.HIGHEST_PROTOCOL)

    for w in pmiinfo:
        items = sorted([(p, c) for (c, p) in pmiinfo[w].iteritems()], reverse=True)[:10]
        print w, " ".join("%s:%f"%(c, p) for p, c in items)
