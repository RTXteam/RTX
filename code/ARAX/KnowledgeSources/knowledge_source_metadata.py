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

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))

from RTXConfiguration import RTXConfiguration


class KnowledgeSourceMetadata:

    #### Define a class variable to cache the meta_knowledge_graph between objects
    cached_meta_knowledge_graph = None
    cached_simplified_meta_knowledge_graph = None

    #### Constructor
    def __init__(self):
        self.predicates = None
        self.meta_knowledge_graph = KnowledgeSourceMetadata.cached_meta_knowledge_graph
        self.simplified_meta_knowledge_graph = KnowledgeSourceMetadata.cached_simplified_meta_knowledge_graph
        self.RTXConfig = RTXConfiguration()


    #### Get a list of all supported subjects, predicates, and objects and reformat to /predicates format
    def get_kg_predicates(self):
        method_name = inspect.stack()[0][3]

        #### If we've already loaded the predicates, just return it
        if self.predicates is not None:
            return self.predicates

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

        self.predicates = predicates

        return predicates


    #### Get a list of all supported subjects, predicates, and objects and return in /meta_knowledge_graph format
    def get_meta_knowledge_graph(self, format=format):
        method_name = inspect.stack()[0][3]

        #### If we've already loaded the meta_knowledge_graph, just return it
        if self.meta_knowledge_graph is not None:
            eprint(f"INFO: Returning previously loaded meta_knowledge_graph")
            if format == 'simple':
                return self.simplified_meta_knowledge_graph
            else:
                return self.meta_knowledge_graph

        # We always furnish KG2C results
        kg_prefix = 'kg2c'

        # Verify that the source data file exists
        #input_filename = os.path.dirname(os.path.abspath(__file__)) + f"/{kg_prefix}_meta_kg.json"
        input_filename = f"{os.path.dirname(os.path.abspath(__file__))}/{self.RTXConfig.kg2c_meta_kg_path.split('/')[-1]}"
        if not os.path.exists(input_filename):
            eprint(f"ERROR [{method_name}]: File '{input_filename}' not found")
            return None

        #try:
        if True:
            with open(input_filename) as infile:
                self.meta_knowledge_graph = json.load(infile)
                KnowledgeSourceMetadata.cached_meta_knowledge_graph = self.meta_knowledge_graph
                eprint("INFO: Loaded meta_knowledge_graph from file and cached it")
                self.create_simplified_meta_knowledge_graph()
                if format == 'simple':
                    return self.simplified_meta_knowledge_graph
                else:
                    return self.meta_knowledge_graph

        #except:
        else:
            eprint(f"ERROR [{method_name}]: Unable to read meta_knowledge_graph from file '{input_filename}'")
            return


    #### Get a list of all supported subjects, predicates, and objects and return in /meta_knowledge_graph format
    def create_simplified_meta_knowledge_graph(self):
        method_name = inspect.stack()[0][3]

        self.simplified_meta_knowledge_graph = {
            'predicates_by_categories': {},
            'supported_predicates': {}
        }

        for edge in self.meta_knowledge_graph['edges']:
            if edge['subject'] not in self.simplified_meta_knowledge_graph['predicates_by_categories']:
                self.simplified_meta_knowledge_graph['predicates_by_categories'][edge['subject']] = {}
            if edge['object'] not in self.simplified_meta_knowledge_graph['predicates_by_categories'][edge['subject']]:
                self.simplified_meta_knowledge_graph['predicates_by_categories'][edge['subject']][edge['object']] = {}
            self.simplified_meta_knowledge_graph['predicates_by_categories'][edge['subject']][edge['object']][edge['predicate']] = True
            self.simplified_meta_knowledge_graph['supported_predicates'][edge['predicate']] = True

        for subject_category,subject_dict in self.simplified_meta_knowledge_graph['predicates_by_categories'].items():
            for object_category,object_dict in subject_dict.items():
                self.simplified_meta_knowledge_graph['predicates_by_categories'][subject_category][object_category] = sorted(list(object_dict))

        self.simplified_meta_knowledge_graph['supported_predicates'] = sorted(list(self.simplified_meta_knowledge_graph['supported_predicates']))


##########################################################################################
def main():

    ksm = KnowledgeSourceMetadata()
    #predicates = ksm.get_kg_predicates()
    #print(json.dumps(predicates,sort_keys=True,indent=2))

    meta_knowledge_graph = ksm.get_meta_knowledge_graph(format='simple')
    print(json.dumps(meta_knowledge_graph,sort_keys=True,indent=2))

if __name__ == "__main__": main()
