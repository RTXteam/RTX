"""The sparse model for the parser."""

__author__ = 'kzhao'

import sys
import tempfile

from wvector import WVector

import gflags as flags
FLAGS = flags.FLAGS

flags.DEFINE_string("feats", "feats/budget7.notag.feats", "feature template file", short_name="f")


class Model(object):
    """ templates and weights """
    names = {"SHIFT": 0, "REDUCE": 1, "SKIP": 2}
    start_sym = "<s>"
    end_sym = "</s>"
    none_sym = "<NONE>"

    eval_module = None  # will be loaded on the fly

    def __init__(self):
        assert FLAGS.feats, "please specify feature templates"

        WVector.setup(Model.names.values())

        self.weights = WVector()

        self.feature_templates = []

        self.load_eval_module()

    @staticmethod
    def new_weights():
        return WVector()

    def load_eval_module(self):
        tffilename = FLAGS.feats
        # atomic feats include:
        # s0lw, s0lt, s0rw, s0rt : leftmost/rightmost word/tag of s0
        # s0tp                   : type of s0
        # s0m0, s0m1             : matched preds at s0
        # s1lw, s1lt, s1rw, s1rt, s1tp
        # s2lw, s2lt, s2rw, s2rt, s2tp
        # q0w, q0t, q1w, q1t, q2w, q2t

        # feature template line is like: s0lw q0w

        indent = " "*4

        tffile = tempfile.NamedTemporaryFile(prefix="semparser_", suffix=".py")

        print >> tffile, "def static_eval((q0w, q0t), (q1w, q1t), (q2w, q2t), (s0lw, s0lt), (s0rw, s0rt), (s1lw, s1lt), (s1rw, s1rt), (s2lw, s2lt), (s2rw, s2rt), s0tp, s1tp, s2tp, s0m0, s0m1, ruleid):"
        print >> tffile, "%sreturn [" % indent

        feattempset = set()
        for line_ in open(tffilename):
            line = line_.strip()
            if not line.startswith("#") and line != "":
                atm_feats = tuple(sorted(line.split()))
                if atm_feats not in feattempset:
                    feattempset.add(atm_feats)
                    self.feature_templates.append(atm_feats)
                    featid = len(self.feature_templates) - 1
                    pattern = "%s'%d=%s'%%(%s)," % (indent*2, featid,
                                                    "|".join(["%s"]*len(atm_feats)),
                                                    ",".join(atm_feats))
                    print >> tffile, pattern
        print >> tffile, "%s]" % (indent*2)

        tffile.flush()

        tfpath, tfname = tffile.name.rsplit('/', 1)
        sys.path.append(tfpath)
        Model.eval_module = __import__(tfname[:-3])

    def eval_feats(self, action, feats):
        return self.weights.evaluate(action, feats)
