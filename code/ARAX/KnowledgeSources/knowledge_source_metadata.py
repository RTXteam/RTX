#!/bin/env python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re
import inspect
import csv

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../ARAXQuery")
import Expand.expand_utilities as eu


class KnowledgeSourceMetadata:

    #### Constructor
    def __init__(self):
        pass

    #### Get a list of all supported subjects, predicates, and objects and reformat to /predicates format
    def get_kg_predicates(self):
        method_name = inspect.stack()[0][3]

        # We always furnish KG2C results
        kg_prefix = 'KG2C'

        # Verify that the source data file exists
        input_filename = os.path.dirname(os.path.abspath(__file__)) + f"/{kg_prefix}_allowed_predicate_triples.csv"
        if not os.path.exists(input_filename):
            eprint(f"ERROR [{method_name}]: File '{input_filename}' not found")
            return None

        # Read the data and fill the predicates dict
        predicates = {}
        iline = 0
        with open(input_filename) as infile:
            rows = csv.reader(infile, delimiter=',', quotechar='"')
            for columns in rows:
                iline += 1

                # Ensure there are exactly 3 columns
                if len(columns) != 3:
                    eprint(f"ERROR [{method_name}]: input file {input_filename} line '{iline} does not have 3 columns")
                    continue

                subject_category = columns[0]
                predicate = columns[1]
                object_category = columns[2]

                if subject_category not in predicates:
                    predicates[subject_category] = {}

                if object_category not in predicates[subject_category]:
                    predicates[subject_category][object_category] = []

                predicates[subject_category][object_category].append(predicate)

        return predicates


    #### Get a list of all supported subjects, predicates, and objects and return in /meta_knowledge_graph format
    def get_meta_knowledge_graph(self):
        method_name = inspect.stack()[0][3]

        # We always furnish KG2C results
        kg_prefix = 'RTX_KG2C'


        # Verify that the source data file exists
        input_filename = os.path.dirname(os.path.abspath(__file__)) + f"/{kg_prefix}_Data.json"
        if not os.path.exists(input_filename):
            eprint(f"ERROR [{method_name}]: File '{input_filename}' not found")
            return None

        try:
            with open(input_filename) as infile:
                return json.load(infile)
        except:
            eprint(f"ERROR: Unable to read meta_knowledge_graph from file '{input_filename}'")
            return


##########################################################################################
def main():

    ksm = KnowledgeSourceMetadata()
    predicates = ksm.get_kg_predicates()
    print(json.dumps(predicates,sort_keys=True,indent=2))

    meta_knowledge_graph = ksm.get_meta_knowledge_graph()
    print(json.dumps(meta_knowledge_graph,sort_keys=True,indent=2))

if __name__ == "__main__": main()
