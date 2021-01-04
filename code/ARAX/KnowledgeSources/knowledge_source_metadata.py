#!/bin/env python3
import sys
def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

import os
import json
import ast
import re
import inspect
import csv


class KnowledgeSourceMetadata:

    #### Constructor
    def __init__(self):
        pass

    #### Top level decision maker for applying filters
    def get_kg_predicates(self, kg_name='KG2'):
        method_name = inspect.stack()[0][3]

        # Determine the table prefix for the knowledge graph selected
        if kg_name.upper() == 'KG1' or kg_name.upper() == 'KG2':
            kg_prefix = kg_name.upper()
        else:
            eprint(f"ERROR [{method_name}]: kg_name must be either 'KG1' or 'KG2'")
            return None


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

                if columns[0] not in predicates:
                    predicates[columns[0]] = {}

                if columns[2] not in predicates[columns[0]]:
                    predicates[columns[0]][columns[2]] = []

                predicates[columns[0]][columns[2]].append(columns[1])

        return predicates


##########################################################################################
def main():

    ksm = KnowledgeSourceMetadata()
    #predicates = ksm.get_kg_predicates(kg_name='KG1')
    predicates = ksm.get_kg_predicates(kg_name='KG2')
    print(json.dumps(predicates,sort_keys=True,indent=2))


if __name__ == "__main__": main()
