#!/bin/env python3
"""create_csv_of_kp_node_pairs.py

Creates a CSV of all pairs of node types for KG1, KG2, and BTE (ARAX's current knowledge providers).
Resulting columns are: subject_type, object_type, provider, source, predicates

Usage: python create_csv_of_kp_node_pairs.py

"""

import requests
import sys
import os
import csv
import time

from neo4j import GraphDatabase

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration


def get_bte_node_pairs():
    print("Grabbing BTE node pairs...")
    url = "https://smart-api.info/registry/translator/meta-kg"
    r = requests.get(url)
    print("...done.")
    bte_associations = r.json()['associations']
    node_pairs_dict = dict()
    for bte_association in bte_associations:
        subject_type = convert_pascal_case_to_snake_case(bte_association['subject']['semantic_type'])
        object_type = convert_pascal_case_to_snake_case(bte_association['object']['semantic_type'])
        predicate = bte_association['predicate']['label']
        provider = "BTE"
        source = bte_association['predicate']['source']
        node_pairs_dict = update_node_pairs_dict(node_pairs_dict, subject_type, object_type, predicate, provider, source)
    return list(node_pairs_dict.values())


def get_kg1_node_pairs():
    cypher = "match (n0)-[e]->(n1) return distinct n0.category, n1.category, e.predicate, e.provided_by"
    results = run_neo4j_query(cypher, "KG1")
    node_pairs_dict = dict()
    for result in results:
        subject_type = result.get('n0.category')
        object_type = result.get('n1.category')
        predicate = result.get('e.predicate')
        provider = "KG1"
        source = result.get('e.provided_by')
        node_pairs_dict = update_node_pairs_dict(node_pairs_dict, subject_type, object_type, predicate, provider, source)
    return list(node_pairs_dict.values())


def get_kg2_node_pairs():
    cypher = "match (n0)-[e]->(n1) return distinct n0.category_label, n1.category_label, e.simplified_edge_label, e.provided_by"
    results = run_neo4j_query(cypher, "KG2")
    node_pairs_dict = dict()
    for result in results:
        subject_type = result.get('n0.category_label')
        object_type = result.get('n1.category_label')
        predicate = result.get('e.simplified_edge_label')
        provider = "KG2"
        # NOTE: Have to do some special handling for KG2 edge.provided_by being a list with buggy format
        sources = result.get('e.provided_by')
        for source in sources:
            node_pairs_dict = update_node_pairs_dict(node_pairs_dict, subject_type, object_type, predicate, provider, source)
    return list(node_pairs_dict.values())


def get_node_pair_key(source, subject_type, object_type):
    return f"{source}:{subject_type}->{object_type}"


def convert_pascal_case_to_snake_case(pascal_string):
    snake_string = pascal_string[0].lower()
    if len(pascal_string) > 1:
        for letter in pascal_string[1:]:
            if letter.isupper():
                snake_string += "_"
            snake_string += letter.lower()
    return snake_string


def update_node_pairs_dict(node_pairs_dict, subject_type, object_type, predicate, provider, source):
    node_pair_key = get_node_pair_key(source, subject_type, object_type)
    if node_pair_key in node_pairs_dict:
        node_pairs_dict[node_pair_key]['predicates'].add(predicate)
    else:
        node_pairs_dict[node_pair_key] = {'subject_type': subject_type, 'object_type': object_type,
                                          'provider': provider, 'source': source, 'predicates': {predicate}}
    return node_pairs_dict


def run_neo4j_query(cypher, kg_name):
    rtx_config = RTXConfiguration()
    if kg_name == "KG2":  # Flip into KG2 mode if this is a KG2 query (otherwise we're already set to use KG1)
        rtx_config.live = "KG2"
    driver = GraphDatabase.driver(rtx_config.neo4j_bolt, auth=(rtx_config.neo4j_username, rtx_config.neo4j_password))
    with driver.session() as session:
        start = time.time()
        print(f"Grabbing node pairs from {kg_name} neo4j...")
        results = session.run(cypher).data()
        print(f"...done. Query took {round((time.time() - start) / 60, 2)} minutes.")
    driver.close()
    return results


def main():
    print("----- starting script -----")
    bte_node_pairs = get_bte_node_pairs()
    kg1_node_pairs = get_kg1_node_pairs()
    kg2_node_pairs = get_kg2_node_pairs()
    all_pairs = bte_node_pairs + kg1_node_pairs + kg2_node_pairs
    keys = all_pairs[0].keys()
    with open('kp_node_pairs.csv', 'w') as output_file:
        dw = csv.DictWriter(output_file, keys)
        dw.writeheader()
        dw.writerows(all_pairs)
    print("----- script finished -----")


if __name__ == "__main__":
    main()
