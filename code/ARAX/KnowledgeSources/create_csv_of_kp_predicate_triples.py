#!/bin/env python3
"""create_csv_of_kp_predicate_triples.py

Creates a CSV of all predicate triples of the form (node type, edge type, node type) for KG1, KG2, and BTE (ARAX's current knowledge providers).
Resulting columns are: subject_type, edge_type, object_type

Usage: python create_csv_of_kp_predicate_triples.py

"""

# adapted from Amy Glen's code in create_csv_of_kp_node_pairs.py

import requests
import sys
import os
import csv
import time
import pandas as pd
import json

from neo4j import GraphDatabase

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration


def run_neo4j_query(cypher, kg_name, data_type):
    rtx_config = RTXConfiguration()
    kg2_neo4j_info = rtx_config.get_neo4j_info(kg_name)
    driver = GraphDatabase.driver(kg2_neo4j_info['bolt'],
                                  auth=(kg2_neo4j_info['username'],
                                        kg2_neo4j_info['password']))
    with driver.session() as session:
        start = time.time()
        print(f"Grabbing {data_type} from {kg_name} neo4j...")
        results = session.run(cypher).data()
        elapsed_time = time.time() - start
        print(f"...done. Query took {round(elapsed_time / 60, 2)} minutes.")
    driver.close()
    return results


def get_kg2_predicate_triples():
    cypher = 'match (n)-[r]->(m) with distinct labels(n) as n1s, type(r) as rel, '+\
            'labels(m) as n2s unwind n1s as n1 unwind n2s as n2 with distinct n1 as '+\
            'node1, rel as relationship, n2 as node2 where node1 <> "Base" and '+\
            'node2 <> "Base" return node1, relationship, node2'
            # Changed this from using n.category so that it can handle node with multiple labels
            # Unfortunetly this makes the cypher a little more unweildly and likely slows a query a bit.
    results = run_neo4j_query(cypher, "KG2pre", "predicate triples")
    triples_dict = {"subject":[], "predicate":[], "object":[]}
    for result in results:
        subject_type = result.get('node1')
        object_type = result.get('node2')
        predicate = result.get('relationship')
        triples_dict['subject'].append(subject_type)
        triples_dict['object'].append(object_type)
        triples_dict['predicate'].append(predicate)
    return pd.DataFrame(triples_dict)

def get_kg2c_predicate_triples():
    cypher = 'match (n)-[r]->(m) with distinct labels(n) as n1s, type(r) as rel, '+\
            'labels(m) as n2s unwind n1s as n1 unwind n2s as n2 with distinct n1 as '+\
            'node1, rel as relationship, n2 as node2 where node1 <> "Base" and '+\
            'node2 <> "Base" return node1, relationship, node2'
            # Changed this from using n.category so that it can handle node with multiple labels
            # Unfortunetly this makes the cypher a little more unweildly and likely slows a query a bit.
    results = run_neo4j_query(cypher, "KG2c", "predicate triples")
    triples_dict = {"subject":[], "predicate":[], "object":[]}
    for result in results:
        subject_type = result.get('node1')
        object_type = result.get('node2')
        predicate = result.get('relationship')
        triples_dict['subject'].append(subject_type)
        triples_dict['object'].append(object_type)
        triples_dict['predicate'].append(predicate)
    return pd.DataFrame(triples_dict)

def get_kg2_predicate_triples_examples():
    cypher = 'match (n)-[r]->(m) with distinct labels(n) as n1s, type(r) as rel, labels(m) as n2s ' +\
                'unwind n1s as n1 unwind n2s as n2 with distinct n1 as node1, rel as relationship, ' +\
                'n2 as node2 where node1 <> "Base" and node2 <> "Base" CALL ' +\
                "apoc.cypher.run('match (n2:`' + node1 + '`)-[r2:`' + relationship + '`]->(m2:`' + node2 + '`) " +\
                "return n2.id as subject, m2.id as object limit 1', {}) YIELD value return node1, relationship, " +\
                "node2, value.subject as subject, value.object as object"
    results = run_neo4j_query(cypher, "KG2pre", "predicate triples")
    triples_dict = {"subject":[], "predicate":[], "object":[]}
    examples_json = {"url": "https://kg2cploverdb.transltr.io",
                    "TRAPI": True,
                    "edges": []}
    for result in results:
        subject_type = result.get('node1')
        object_type = result.get('node2')
        predicate = result.get('relationship')
        subject_example = result.get('subject')
        object_example = result.get('object')
        triples_dict['subject'].append(subject_type)
        triples_dict['object'].append(object_type)
        triples_dict['predicate'].append(predicate)
        example = {
            "subject_category": subject_type,
            "object_category": object_type,
            "predicate": predicate,
            "subject": subject_example,
            "object": object_example
        }
        examples_json['edges'].append(example)
    return pd.DataFrame(triples_dict).drop_duplicates(ignore_index=True), examples_json

def get_kg2c_predicate_triples_examples():
    cypher = 'match (n)-[r]->(m) with distinct labels(n) as n1s, type(r) as rel, labels(m) as n2s ' +\
                'unwind n1s as n1 unwind n2s as n2 with distinct n1 as node1, rel as relationship, ' +\
                'n2 as node2 where node1 <> "Base" and node2 <> "Base" CALL ' +\
                "apoc.cypher.run('match (n2:`' + node1 + '`)-[r2:`' + relationship + '`]->(m2:`' + node2 + '`) " +\
                "return n2.id as subject, m2.id as object limit 1', {}) YIELD value return node1, relationship, " +\
                "node2, value.subject as subject, value.object as object"
    results = run_neo4j_query(cypher, "KG2c", "predicate triples")
    triples_dict = {"subject":[], "predicate":[], "object":[]}
    examples_json = {"url": "https://kg2cploverdb.transltr.io",
                    "TRAPI": True,
                    "edges": []}
    for result in results:
        subject_type = result.get('node1')
        object_type = result.get('node2')
        predicate = result.get('relationship')
        subject_example = result.get('subject')
        object_example = result.get('object')
        triples_dict['subject'].append(subject_type)
        triples_dict['object'].append(object_type)
        triples_dict['predicate'].append(predicate)
        example = {
            "subject_category": subject_type,
            "object_category": object_type,
            "predicate": predicate,
            "subject": subject_example,
            "object": object_example
        }
        examples_json['edges'].append(example)
    return pd.DataFrame(triples_dict).drop_duplicates(ignore_index=True), examples_json

def get_kg2_node_labels():
    cypher = 'call db.labels()'
    results = run_neo4j_query(cypher, "KG2pre", "node labels")
    labels_dict = {"label":[]}
    for result in results:
        label = result.get('label')
        labels_dict["label"].append(label)
    return pd.DataFrame(labels_dict)

def get_kg2c_node_labels():
    cypher = 'call db.labels()'
    results = run_neo4j_query(cypher, "KG2c", "node labels")
    labels_dict = {"label":[]}
    for result in results:
        label = result.get('label')
        labels_dict["label"].append(label)
    return pd.DataFrame(labels_dict)

def get_kg2_relationship_types():
    cypher = 'call db.relationshipTypes()'
    results = run_neo4j_query(cypher, "KG2pre", "relationship types")
    predicate_dict = {"predicate":[]}
    for result in results:
        predicate = result.get('relationshipType')
        predicate_dict["predicate"].append(predicate)
    return pd.DataFrame(predicate_dict)

def get_kg2c_relationship_types():
    cypher = 'call db.relationshipTypes()'
    results = run_neo4j_query(cypher, "KG2c", "relationship types")
    predicate_dict = {"predicate":[]}
    for result in results:
        predicate = result.get('relationshipType')
        predicate_dict["predicate"].append(predicate)
    return pd.DataFrame(predicate_dict)


def main():
    print("----- starting script -----")
    
    #kg2_triple_df, KG2_examples_json = get_kg2_predicate_triples_examples()
    kg2c_triple_df, KG2c_examples_json = get_kg2c_predicate_triples_examples()
    #kg2_triple_df.to_csv("KG2_allowed_predicate_triples.csv", index=False)
    #with open('RTX_KG2_Data.json','w') as fid:
    #    json.dump(KG2_examples_json, fid, indent=4)
    kg2c_triple_df.to_csv("KG2c_allowed_predicate_triples.csv", index=False)
    with open('RTX_KG2c_Data.json','w') as fid:
        json.dump(KG2c_examples_json, fid, indent=4)

    #kg2_labels_df = get_kg2_node_labels()
    kg2c_labels_df = get_kg2c_node_labels()
    #kg2_labels_df.to_csv("KG2_allowed_node_labels.csv", index=False)
    kg2c_labels_df.to_csv("KG2c_allowed_node_labels.csv", index=False)

    #kg2_labels_df = get_kg2_relationship_types()
    kg2c_labels_df = get_kg2c_relationship_types()
    #kg2_labels_df.to_csv("KG2_allowed_relationship_types.csv", index=False)
    kg2c_labels_df.to_csv("KG2c_allowed_relationship_types.csv", index=False)
    print("----- script finished -----")

if __name__ == "__main__":
    main()
