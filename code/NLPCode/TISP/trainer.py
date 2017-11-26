#!/usr/bin/env python

"""Latent Variable Structured Perceptron Trainer.
"""

__author__ = 'kzhao'

import sys
LOGS = sys.stderr

import pickle
from multiprocessing import cpu_count, Pool
import time
import math
import mmap
import traceback

from parsing_state import State
from model import Model
from parser import Parser, ExprGenerator
from indep_knowledgebase import IndepKnowledgeBase
from lambda_expr import simplify_expr, collect_constants, ComplexType
from forceddecoding import ForcedDecoder

import gflags as flags
FLAGS = flags.FLAGS

flags.DEFINE_integer("ncpus", 0, "number of cpus in parallel")
flags.DEFINE_string("ref", None, "reference beams")
flags.DEFINE_string("extraref", None, "extra reference beams")
flags.DEFINE_boolean("ontheflyfd", True, "fd on-the-fly")
flags.DEFINE_integer("fdbeam", 2048, "forced decoding beam size")
flags.DEFINE_integer("iter", 40, "number of iterations")
flags.DEFINE_boolean("singlegold", True, "use single gold (the best derivation in the end) as reference")
flags.DEFINE_string("outputprefix", None, "prefix of files for output weights")

_sanity_check = False


class Perceptron(object):
    """perceptron w/ minibatch"""

    shared_memo = None
    shared_memo_size = None
    indepKB = None
    KB = None
    model = None
    ncpus = None
    verbose = False
    ref_beams = None
    iter = 0
    c = 0
    beamsize = None
    parser = None
    min_task_time = 0.2  # for multiprocessing, set minimal task time 0.2s

    output_prefix = None

    ontheflyfd = None
    ForcedDecoder = None
    fdbeamsize = None

    single_gold = True

    def __init__(self, knowledgebase):
        if _sanity_check:
            ExprGenerator.setup()
            State.ExtraInfoGen = ExprGenerator
        Perceptron.model = Model()
        Perceptron.indepKB = IndepKnowledgeBase()
        Perceptron.KB = knowledgebase
        knowledgebase.postedit_indepkb(Perceptron.indepKB)
        Perceptron.c = 0
        Perceptron.iter = FLAGS.iter
        Perceptron.beamsize = FLAGS.beam
        Perceptron.parser = Parser(Perceptron.indepKB, Perceptron.KB, Perceptron.model, State)

        Perceptron.ncpus = FLAGS.ncpus

        Perceptron.ontheflyfd = FLAGS.ontheflyfd
        Perceptron.single_gold = FLAGS.singlegold
        Perceptron.output_prefix = FLAGS.outputprefix
        Perceptron.fdbeamsize = FLAGS.fdbeam

        if Perceptron.ncpus > 0:
            Perceptron.shared_memo_size = int(1024 * 1024 * 1024)  # 1G shared memory
            Perceptron.shared_memo = mmap.mmap(-1, Perceptron.shared_memo_size,
                                               mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)

        Perceptron.ref_beams = {}
        if FLAGS.ref:
            print >> LOGS, "loading refs",
            hgs = pickle.load(open(FLAGS.ref))
            self.load_hgs(hgs)

        if FLAGS.extraref:
            print >> LOGS, "loading extra refs",
            hgs = pickle.load(open(FLAGS.extraref))
            self.load_hgs(hgs)

    def load_hgs(self, hgs):
        """load decoding hypergraph to beam"""
        stepsize = len(hgs) / 10
        start_t = time.time()
        for j, (sentid, hg) in enumerate(hgs.iteritems()):
            if stepsize != 0 and j % stepsize == 0:
                print >> LOGS, ".",

            beam = self.load_ref_hg(sentid, hg)

            self.ref_beams[sentid] = beam

            if _sanity_check:
                for s in beam[-1]:
                    goldexpr = Perceptron.KB.logicalexprs[sentid][0]
                    refexpr = simplify_expr(s.extrainfo)
                    if not goldexpr.semantic_eq(refexpr):
                        print >> LOGS, "inconsistant at sent", sentid
                        print >> LOGS, "gold", goldexpr
                        print >> LOGS, "ref", refexpr
        end_t = time.time()
        print >> LOGS, "taking %fs" % (end_t - start_t)

    def load_ref_hg(self, sentid, hg):
        """load reference decoding hypergraph to beam"""
        string = Perceptron.KB.questions[sentid]
        beam = [[] for i in xrange(len(string)*2)]

        State.setup(indepKB=self.indepKB, KB=self.KB, string=string, model=self.model)
        states = {0: State.initstate()}
        beam[0].append(states[0])

        for sid, (action, match, ruleid, incomings) in sorted(hg.iteritems(), key=lambda x: x[0]):
            first_edge = incomings[0]
            if not first_edge[0] in states:
                print >> LOGS, sentid
                print >> LOGS, sid
                print >> LOGS, first_edge[0]
                print >> LOGS, states.keys()
                assert False
            if first_edge[1]:
                assert first_edge[1] in states
            if action == 1:
                if not first_edge[1]:
                    print >> LOGS, first_edge, "--", action, "-->", sid
                assert first_edge[1] in states
            newstate = states[first_edge[0]].forced_proceed(action, match, ruleid,
                                                            states[first_edge[1]] if first_edge[1] else None)
            states[sid] = newstate
            beam[newstate.step].append(newstate)
        return beam

    def rerank_beam(self, beam):
        for i, beamstep in enumerate(beam):
            if i != 0:
                for s in beamstep:
                    s.evaluate()
            beam[i] = sorted(beamstep)
        return beam

    def timed_learn_one(self, args):
        start_t = time.time()
        try:
            ret = self.learn_one(args)
        except:
            raise Exception("".join(traceback.format_exception(*sys.exc_info())))
        end_t = time.time()
        timeused = end_t - start_t
        if timeused < Perceptron.min_task_time:
            time.sleep(Perceptron.min_task_time-timeused)
        return ret

    def learn_one(self, args):
        sentid, update_c = args

        start_t = time.time()

        if Perceptron.ncpus > 0:
            Perceptron.shared_memo.seek(0)
            update_weights = pickle.load(Perceptron.shared_memo)
            Perceptron.model.weights.iadd_wstep(update_weights, update_c)
            Perceptron.c += 1

        ret = {
            "c": Perceptron.c,
            "start_t": start_t,
            "match_prec": 0,
            "match_recall": 0
        }

        if Perceptron.verbose:
            print >> LOGS, "sent", sentid
        if sentid == -1:
            ret["end_t"] = time.time()
            return None, ret

        string = Perceptron.KB.questions[sentid]
        goldexpr, goldte = Perceptron.KB.logicalexprs[sentid]
        if Perceptron.verbose:
            print >> LOGS, string
            print >> LOGS, goldexpr

        goldbeam = None
        if sentid in Perceptron.ref_beams:
            goldbeam = Perceptron.ref_beams[sentid]
        elif Perceptron.ontheflyfd:
            Perceptron.ForcedDecoder.parser.dp = False
            Perceptron.ForcedDecoder.parser.beamwidth = Perceptron.fdbeamsize
            (fdmatches, fdhg) = Perceptron.ForcedDecoder.decode(sentid)
            if fdmatches > 0:
                goldbeam = self.load_ref_hg(sentid, fdhg)

        Perceptron.parser.beamwidth = Perceptron.beamsize

        parse_result = Perceptron.parser.parse(string, filter_func=None, verbose=False)
        parse_result = simplify_expr(parse_result.get_expr()) if parse_result else None

        ret["parse"] = True if parse_result else False

        if Perceptron.verbose:
            print >> LOGS, "==>", parse_result

        if parse_result and parse_result.semantic_eq(goldexpr):
            ret["end_t"] = time.time()
            ret["match_recall"] = 1.0
            ret["match_prec"] = 1.0
            return True, ret
        elif goldbeam:
            # calculate partial predicate match
            viterbi_unigrams = collect_constants(parse_result)[0] if parse_result else set()
            viterbi_unigrams = set(x.name if isinstance(x.type, ComplexType) else str(x) for x in viterbi_unigrams)
            unigrams_intersection = viterbi_unigrams & Perceptron.KB.expr_unigrams[sentid]

            ret["match_prec"] = 1.0 * len(unigrams_intersection) / len(viterbi_unigrams) if len(viterbi_unigrams) > 0 \
                else 0.0
            ret["match_recall"] = 1.0 * len(unigrams_intersection) / len(Perceptron.KB.expr_unigrams[sentid])

            gb_ = self.rerank_beam(goldbeam)
            gb = None

            if Perceptron.single_gold:
                gb = [[] for i in xrange(len(gb_))]
                for item in gb_[-1][0].trace_states():
                    gb[item.step].append(item)
            else:
                gb = gb_

            maxstep = -1
            maxdiff = -float("inf")

            for i in xrange(len(gb)):
                if len(gb[i]) > 0 and len(Perceptron.parser.beam[i]) > 0:
                    scorediff = Perceptron.parser.beam[i][0].score - gb[i][0].score

                    if Perceptron.verbose:
                        golditem = gb[i][0]
                        viterbiitem = Perceptron.parser.beam[i][0]
                        print >> LOGS, "at %d: %f"%(i, scorediff), \
                            "\t\tgoldbeam len", len(gb[i]), \
                            "viterbi beam len", len(Perceptron.parser.beam[i])
                        print >> LOGS, "\tgold score", golditem.score, \
                            "actioncost", golditem.actioncost, \
                            "inside", golditem.inside, "shift", golditem.shiftcost, \
                            golditem, golditem.action, golditem.match
                        print >> LOGS, "\t\tgold.incomings", golditem.incomings, \
                            golditem.incomings[0][0].score if golditem.incomings else None
                        print >> LOGS, "\t\tgold.left", golditem.leftptrs
                        print >> LOGS, "\t\t", golditem.get_expr()
                        print >> LOGS, "\tviterbi score", viterbiitem.score, \
                            "actioncost", viterbiitem.actioncost, \
                            "inside", viterbiitem.inside, "shift", \
                            viterbiitem.shiftcost, viterbiitem, viterbiitem.action, viterbiitem.match
                        print >> LOGS, "\t\tviterbi.incomings", viterbiitem.incomings, \
                            viterbiitem.incomings[0][0].score if viterbiitem.incomings else None
                        print >> LOGS, "\t\tviterbi.left", viterbiitem.leftptrs
                        print >> LOGS, "\t\t", viterbiitem.get_expr()

                    if scorediff >= 0 and scorediff >= maxdiff:
                        maxdiff = scorediff
                        maxstep = i

            assert maxstep != -1, "max violation not found"

            viterbistate = Perceptron.parser.beam[maxstep][0]
            goldstate = gb[maxstep][0]

            viterbifeats = viterbistate.recover_feats()
            goldfeats = goldstate.recover_feats()

            deltafeats = goldfeats.iaddc(viterbifeats, -1)

            if _sanity_check:
                viterbiscore = Perceptron.model.weights.dot(viterbifeats)
                if abs(viterbiscore - viterbistate.score) > State.epsilon:
                    print >> LOGS, "wrong viterbi score", viterbiscore, viterbistate.score, str(viterbistate)
                    print >> LOGS, viterbifeats
                    print >> LOGS, State.model.eval_module.static_eval(*(viterbistate.get_atomic_feats()))
                    assert False
                scorediff_ = Perceptron.model.weights.dot(deltafeats)
                if abs(scorediff_ + maxdiff) > State.epsilon:
                    print >> LOGS, "wrong max violation", scorediff_, maxdiff
                    assert False

            ret["deltafeats"] = deltafeats
            ret["sentid"] = sentid

            ret["end_t"] = time.time()

            return False, ret
        else:
            ret["end_t"] = time.time()
            return False, ret

    def learn_one_pass(self, sentids):

        succ_count = 0
        parsed_count = 0

        match_prec = 0
        match_recall = 0

        if Perceptron.ontheflyfd:
            Perceptron.ForcedDecoder = ForcedDecoder(Perceptron.KB)
            Perceptron.ForcedDecoder.model.weights = Perceptron.model.weights

        pool = Pool(Perceptron.ncpus) if Perceptron.ncpus > 0 else None

        batchsize = Perceptron.ncpus if Perceptron.ncpus > 0 else 1

        delta_feats = Perceptron.model.new_weights()

        failed_parse = []
        wrong_parse = []

        tot_pool_time = 0
        tot_dec_time = 0

        for batchid in xrange(int(math.ceil(1.0*len(sentids)/batchsize))):
            args = [((sentids[x] if x < len(sentids) else -1), Perceptron.c)
                    for x in xrange(batchid*batchsize, (batchid+1)*batchsize)]

            if Perceptron.ncpus > 0:
                Perceptron.shared_memo.seek(0)
                pickle.dump(delta_feats, Perceptron.shared_memo)


            start_pool_t = time.time()

            results = pool.map(self.timed_learn_one, args) if pool else map(self.learn_one, args)

            end_pool_t = time.time()

            delta_feats = Perceptron.model.new_weights()
            n_df = 0

            batch_succ = 0
            batch_parsed = 0

            earliest_thread_start_t = float("inf")
            latest_thread_end_t = -float("inf")

            for (succ, info) in results:
                match_prec += info["match_prec"]
                match_recall += info["match_recall"]
                if succ:
                    batch_succ += 1
                    batch_parsed += 1
                else:
                    if "parse" in info and info["parse"]:
                        batch_parsed += 1

                    if "deltafeats" in info:
                        delta_feats.iaddc(info["deltafeats"], 1)
                        n_df += 1
                        sentid = -1
                        if "sentid" in info:
                            sentid = info["sentid"]
                            if "parse" in info:
                                if info["parse"]:
                                    wrong_parse.append(sentid)
                                else:
                                    failed_parse.append(sentid)

                if "start_t" in info:
                    s = info["start_t"]
                    e = info["end_t"]
                    if s < earliest_thread_start_t:
                        earliest_thread_start_t = s
                    if e > latest_thread_end_t:
                        latest_thread_end_t = e

            succ_count += batch_succ
            parsed_count += batch_parsed

            tot_pool_time += end_pool_t - start_pool_t
            tot_dec_time += (latest_thread_end_t - earliest_thread_start_t) if earliest_thread_start_t else 0

            print >> LOGS, "batch %d done: succ %d, taking %f s" % (batchid, batch_succ, end_pool_t-start_pool_t)

            if n_df > 0:
                delta_feats.times(1.0/n_df)
                delta_feats.trim()
                Perceptron.model.weights.iadd_wstep(delta_feats, step=Perceptron.c)

            Perceptron.c += 1

        if pool:
            pool.close()
            pool.join()

        ret = {
            "succ": succ_count,
            "parsed": parsed_count,
            "failed_parse": failed_parse,
            "wrong_parse": wrong_parse,
            "pool_time": tot_pool_time,
            "dec_time": tot_dec_time,
            "match_prec": match_prec / len(sentids),
            "match_recall": match_recall / len(sentids)
        }

        return ret

    def decode_sent(self, args):
        ret = {}
        try:
            ret = self._decode_sent(args)
        except:
            ret["sentid"] = args
            ret["parsed"] = False
            ret["succ"] = False
            ret["parse"] = str(None)
            ret["match_prec"] = 0.0
            ret["match_recall"] = 0.0
            print >> LOGS, "error", args

        return ret

    def _decode_sent(self, args):
        """ return: is_parsed, is_result_correct """
        sentid = args
        string = Perceptron.KB.questions[sentid]
        goldexpr, _ = Perceptron.KB.logicalexprs[sentid]

        parse_result = Perceptron.parser.parse(string, filter_func=None, verbose=Perceptron.verbose)
        parse_result = simplify_expr(parse_result.get_expr()) if parse_result else None

        ret = {
            "sentid": sentid,
            "parsed": parse_result is not None,
            "succ": parse_result and parse_result.semantic_eq(goldexpr),
            "parse": str(parse_result),
            "match_prec": 0.0,
            "match_recall": 0.0
        }

        if parse_result:
            parse_unigrams = set(x.name if isinstance(x.type, ComplexType) else str(x)
                                 for x in collect_constants(parse_result)[0])
            intersection = parse_unigrams & Perceptron.KB.expr_unigrams[sentid]
            ret["match_prec"] = 1.0 * len(intersection) / len(parse_unigrams) if len(parse_unigrams) > 0 else 0
            ret["match_recall"] = 1.0 * len(intersection) / len(Perceptron.KB.expr_unigrams[sentid])
        return ret

    def eval(self, sentids, verbose=False):
        parsed_count = 0
        succ_count = 0

        match_prec = 0.0
        match_recall = 0.0

        failed_parse = []
        wrong_parse = []

        ncpus = cpu_count()
        pool = Pool(ncpus) if ncpus > 0 else None

        print >> LOGS, "eval on", len(sentids), "sentences"

        results = pool.map(self.decode_sent, sentids) if pool else map(self._decode_sent, sentids)

        print >> LOGS, "get %d results" % len(results)

        for i, stats in enumerate(results):
            sentid = stats["sentid"]
            parsed_count += 1 if stats["parsed"] else 0
            succ_count += 1 if stats["succ"] else 0
            match_prec += stats["match_prec"]
            match_recall += stats["match_recall"]

            if not stats["parsed"]:
                failed_parse.append(sentid)
            elif not stats["succ"]:
                wrong_parse.append(sentid)

            if verbose:
                if not stats["parsed"] or not stats["succ"]:
                    print >> LOGS, "sent %d" % sentid
                    print >> LOGS, "sent", Perceptron.KB.questions[sentid]
                    print >> LOGS, "gold", Perceptron.KB.logicalexprs[sentid]
                    if not stats["parsed"]:
                        print >> LOGS, "parse failed"
                    elif not stats["succ"]:
                        print >> LOGS, "viterbi", stats["parse"]
                    print >> LOGS

        if pool:
            pool.close()
            pool.join()

        match_prec /= len(sentids)
        match_recall /= len(sentids)

        ret = {
            "parsed": parsed_count,
            "succ": succ_count,
            "failed_parse": failed_parse,
            "wrong_parse": wrong_parse,
            "match_recall": match_recall,
            "match_prec": match_prec
        }

        return ret


    def train(self, trainids=None, devids=None):
        if not trainids:
            trainids = [x for x in xrange(Perceptron.KB.trainsize) if x in Perceptron.ref_beams]
            if Perceptron.ontheflyfd:
                trainids += [x for x in xrange(Perceptron.KB.trainsize) if x not in Perceptron.ref_beams]
        if not devids:
            devids = range(Perceptron.KB.trainsize, Perceptron.KB.trainsize+Perceptron.KB.devsize)

        trainsize = len(trainids)
        devsize = len(devids)

        print >> LOGS, "train on %d examples, dev on %d examples" %  (trainsize, devsize)

        print >> LOGS, "init weights len", len(Perceptron.model.weights)

        for i in xrange(1, Perceptron.iter+1):
            train_start = time.time()

            print >> LOGS, "======== iter %d ========" % i

            train_stats = self.learn_one_pass(trainids)

            train_end = time.time()

            Perceptron.model.weights.set_avg(Perceptron.c)

            dev_stats = {"succ": 0, "parsed": 0, "match_prec": 0.0, "match_recall": 0.0}
            if devsize:
                dev_stats = self.eval(devids)

            dev_end = time.time()

            prec_train = 1.0*train_stats["succ"]/train_stats["parsed"] if train_stats["parsed"] != 0 else 0
            recall_train = 1.0*train_stats["succ"]/trainsize
            f1_train = prec_train*recall_train*2/(prec_train+recall_train) if (prec_train+recall_train) > 0 else 0.0

            print >> LOGS, "at iter %d training P %.2f R %.2f F1 %.2f" %\
                           (i, prec_train*100, recall_train*100, f1_train*100),

            prec_dev = 1.0*dev_stats["succ"]/dev_stats["parsed"] if dev_stats["parsed"] else 0.0
            recall_dev = 1.0*dev_stats["succ"]/devsize if devsize else 0.0
            f1_dev = prec_dev*recall_dev*2/(prec_dev+recall_dev) if (prec_dev+recall_dev) > 0 else 0.0

            print >> LOGS, "dev P %.2f R %.2f F1 %.2f" % (prec_dev*100, recall_dev*100, f1_dev*100)

            print >> LOGS, "train failed parse %d:" % len(train_stats["failed_parse"]), train_stats["failed_parse"]
            print >> LOGS, "train wrong parse %d:" % len(train_stats["wrong_parse"]), train_stats["wrong_parse"]

            if Perceptron.output_prefix:
                pickle.dump(Perceptron.model.weights,
                            open("%s.%i.pickle" % (Perceptron.output_prefix, i), "w"),
                            pickle.HIGHEST_PROTOCOL)

            Perceptron.model.weights.reset_avg(Perceptron.c)

    def eval_weight(self, weightfile):
        Perceptron.model.weights = pickle.load(open(weightfile))
        ExprGenerator.setup()
        State.ExtraInfoGen = ExprGenerator

        devsize = Perceptron.KB.devsize
        testsize = Perceptron.KB.testsize
        devids = range(Perceptron.KB.trainsize, Perceptron.KB.trainsize+Perceptron.KB.devsize)
        testids = range(Perceptron.KB.trainsize + Perceptron.KB.devsize,
                        Perceptron.KB.trainsize + \
                        Perceptron.KB.devsize + \
                        Perceptron.KB.testsize)


        if Perceptron.KB.devsize > 0:
            dev_stats = self.eval(devids)
            prec_dev = 1.0*dev_stats["succ"]/dev_stats["parsed"] if dev_stats["parsed"] else 0.0
            recall_dev = 1.0*dev_stats["succ"]/devsize if devsize else 0.0
            f1_dev = prec_dev*recall_dev*2/(prec_dev+recall_dev) if (prec_dev+recall_dev) > 0 else 0.0
            print >> LOGS, "dev P %.2f R %.2f F1 %.2f" % (prec_dev*100, recall_dev*100, f1_dev*100),

        test_stats = self.eval(testids, True)

        prec_test = 1.0*test_stats["succ"]/test_stats["parsed"] if test_stats["parsed"] != 0 else 0
        recall_test = 1.0*test_stats["succ"]/testsize
        f1_test = prec_test*recall_test*2/(prec_test+recall_test) if (prec_test+recall_test) > 0 else 0.0

        print >> LOGS, "test P %.2f R %.2f F1 %.2f" % (prec_test*100, recall_test*100, f1_test*100)


if __name__ == "__main__":
    from geoquery import GeoQuery
    flags.DEFINE_string("eval", None, "which parameter settings to evaluate")
    FLAGS(sys.argv)

    KB = GeoQuery()

    perc = Perceptron(KB)

    if FLAGS.eval is None:
        perc.train()
    else:
        perc.eval_weight(FLAGS.eval)
