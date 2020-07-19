#!/bin/env python3
"""
This script creates a JSON file containing curies in KG2 and their corresponding text synonyms (as they appear in the
"synonym" property on nodes in KG2). The JSON file is created in the same directory the script is run from.
Example of entry in output:
   "CUI:C0035923":[
      "RUBELLA VIRUS VACCINE,LIVE",
      "Rubella Vaccine"
   ]
Usage: python dump_kg2_synonym_field.py
"""
import json
import os
import sys
import traceback
import ast

from typing import List, Dict
from neo4j import GraphDatabase

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration


def _run_cypher_query(cypher_query: str, kg='KG2') -> List[Dict[str, any]]:
    # This function sends a cypher query to neo4j (either KG1 or KG2) and returns results
    rtxc = RTXConfiguration()
    if kg == 'KG2':
        rtxc.live = 'KG2'
    try:
        driver = GraphDatabase.driver(rtxc.neo4j_bolt, auth=(rtxc.neo4j_username, rtxc.neo4j_password))
        with driver.session() as session:
            print(f"Sending cypher query to {kg} neo4j")
            query_results = session.run(cypher_query).data()
            print(f"Got {len(query_results)} results back from neo4j")
        driver.close()
    except Exception:
        tb = traceback.format_exc()
        error_type, error, _ = sys.exc_info()
        print(f"Encountered an error interacting with {kg} neo4j. {tb}")
        return []
    else:
        return query_results


def dump_kg2_synonym_field():   
    # This function creates a JSON file of KG2 nodes and their synonyms as listed in the node "synonym" property
    cypher_query = f"match (n) where n.synonym is not null and n.synonym <> '[]' return n.id, n.synonym"
    results = _run_cypher_query(cypher_query)
    if results:
        file_name = 'kg2_synonyms.json'
        synonym_map = dict()
        unparsable_nodes = dict()
        with open(file_name, 'w+') as output_file:
            for row in results:
                curie = row['n.id']
                synonym_list_as_string = row['n.synonym']
                try:
                    # Synonyms are stored as a list within a string in neo4j; parse to extract the list
                    synonym_map[curie] = ast.literal_eval(synonym_list_as_string)
                except Exception:
                    unparsable_nodes[curie] = synonym_list_as_string
            json.dump(synonym_map, output_file)
        print(f"Successfully created file '{file_name}' containing results.")
        if len(unparsable_nodes):
            print(f"WARNING: Skipped {len(unparsable_nodes)} nodes because there was an error when parsing "
                  f"their synonym field, likely due to strange characters. (EOF error or the like.)")
    else:
        print(f"Sorry, couldn't get synonym data. No file created.")


def main():
    dump_kg2_synonym_field()


if __name__ == "__main__":
    main()
