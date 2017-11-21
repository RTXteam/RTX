"""Domain-independent Knowledge.

Contains the lambda expression templates for lexicon grounding.
"""

__author__ = 'kzhao'

import os
from collections import defaultdict
from hashlib import md5

import sys
logs = sys.stderr

from lambda_expr import TypeSystem
from lambda_expr import LambdaExprParser as LambdaExprParser
_TS = TypeSystem()

__expr_tmpl_file__ = "expr_templates"


class IndepKnowledgeBase(object):
    """domain-independent knowledge"""

    def __init__(self):
        self.patterns = defaultdict(list)
        self.postags = defaultdict(list)

        self.expr_parser = LambdaExprParser()

        self.ruleid2rule = {}

        for line in open(__expr_tmpl_file__):
            if line != "\n" and not line.startswith("//"):
                self.add_rule(line.strip())

    def add_rule(self, line):
        p, exprstr = line.split(" :")
        exprstr = exprstr.strip()
        if exprstr != "":
            m = md5()
            m.update(line)
            ruleid = m.hexdigest()
            expr, te = self.expr_parser.parse(exprstr)
            assert ruleid not in self.ruleid2rule
            self.ruleid2rule[ruleid] = (expr, te)
            if p.startswith("POS#"):
                self.postags[p[4:]].append((expr, te, ruleid))
            else:
                self.patterns["_".join(p.split())].append((expr, te, ruleid))

    def fetch_postag(self, postag):
        """return the exprs associated with the given postag
        we rename the type variable ids in the exprs to avoid conflicting
        """
        if postag not in self.postags:
            return
        for expr, te, ruleid in self.postags[postag]:
            tvmapping = {}
            vmapping = {}
            yield (expr.duplicate(vmapping, tvmapping), te.duplicate(tvmapping), ruleid)

    def fetch_pattern(self, pattern):
        """return the exprs associated with the given pattern
        we rename the type variable ids in the exprs to avoid conflicting
        """
        if pattern not in self.patterns:
            return
        for expr, te, ruleid in self.patterns[pattern]:
            tvmapping = {}
            vmapping = {}
            yield (expr.duplicate(vmapping, tvmapping), te.duplicate(tvmapping), ruleid)

    def fetch_ruleid(self, ruleid):
        if ruleid not in self.ruleid2rule:
            return None, None
        expr, te = self.ruleid2rule[ruleid]
        tvmapping = {}
        vmapping = {}
        return expr.duplicate(vmapping, tvmapping), te.duplicate(tvmapping)
