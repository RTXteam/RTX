# This class will overlay the normalized google distance on a message (all edges)
#!/bin/env python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re

from response import Response


class ComputeNGD:

    #### Constructor
    def __init__(self, response, message, ngd_params):
        self.response = response
        self.message = message
        self.ngd_parameters = ngd_params

    def compute_ngd(self):

        # do some random stuff
        self.response.debug(f"Computing NGD")

        self.response.warning(f"More random numbers!")
        import random

        #### Loop over all results, computing and storing confidence scores
        for result in self.message.results:
            result.confidence = 2#float(int(random.random()*1000))/1000

        return self.response