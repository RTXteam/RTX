"""Domain-dependent knowledge.

Loaded from the domain knowledge file for each dataset.
"""

__author__ = 'kzhao'

import sys
logs = sys.stderr

from lambda_expr import TypeSystem

_TS = TypeSystem()


class KnowledgeBase(object):
    def __init__(self):
        self.nnps = None
        self.logicalexprs = None
        self.predicates = None
        self.predicate2annotation = None
        self.ruleid2rule = None
        self.adjs = None
        self.pmi = None
        self.expr_unigrams = None

    def fetch_NNP(self, nnp, n=0):
        """ fetch the top n constants for a given nnp
        :return: a list of (score, const_expr, typeenv) tuples
        """
        ret = self.nnps[nnp][:n] if n > 0 else self.nnps[nnp]
        for score, expr, te, ruleid in ret:
            tvmapping = {}
            vmapping = {}
            yield (score, expr.duplicate(vmapping, tvmapping), te.duplicate(tvmapping), ruleid)

    def fetch_predicates(self, pred_type, te, string, n=0):
        """return the predicates matching the given type
        ranked by the lexical similarity to the given string
        """
        #TODO: cache this
        tvmapping = {}
        newpredt = _TS.duplicate_type(pred_type, tvmapping)
        newpredtte = te.duplicate(tvmapping)
        word = string[-1]

        for predexpr, predte, annotation in self.predicates:
            rette = newpredtte.merge(predte)
            _TS.TE = rette
            if _TS.unify_subtype(parent=newpredt, child=predexpr.type):
                tvmapping = {}
                vmapping = {}
                predname = predexpr.name[:-1] if predexpr.name[-1].isdigit() else predexpr.name
                if word in self.pmi:
                    if predname not in self.pmi[word]:
                        continue
                yield (predexpr.duplicate(vmapping, tvmapping), predte.duplicate(tvmapping), annotation)

    def fetch_ruleid(self, ruleid):
        if ruleid not in self.ruleid2rule:
            return 0.0, None, None
        score, expr, te = self.ruleid2rule[ruleid]
        tvmapping = {}
        vmapping = {}
        return score, expr.duplicate(vmapping, tvmapping), te.duplicate(tvmapping)

    def postedit_indepkb(self, indepKB):
        return
