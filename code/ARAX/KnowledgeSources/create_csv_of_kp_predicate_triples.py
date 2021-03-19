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

from neo4j import GraphDatabase

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration

def run_neo4j_query(cypher, kg_name, data_type):
    rtx_config = RTXConfiguration()
    if kg_name != "KG1":
        rtx_config.live = kg_name
    driver = GraphDatabase.driver(rtx_config.neo4j_bolt, auth=(rtx_config.neo4j_username, rtx_config.neo4j_password))
    with driver.session() as session:
        start = time.time()
        print(f"Grabbing {data_type} from {kg_name} neo4j...")
        results = session.run(cypher).data()
        print(f"...done. Query took {round((time.time() - start) / 60, 2)} minutes.")
    driver.close()
    return results

def get_kg1_predicate_triples():
    cypher = 'match (n)-[r]->(m) with distinct labels(n) as n1s, type(r) as rel, '+\
            'labels(m) as n2s unwind n1s as n1 unwind n2s as n2 with distinct n1 as '+\
            'node1, rel as relationship, n2 as node2 where node1 <> "Base" and '+\
            'node2 <> "Base" return node1, relationship, node2'
            # Changed this from using n.category so that it can handle node with multiple labels
            # Unfortunetly that makes the cypher a little more unweildly and likely slows a query a bit.
    results = run_neo4j_query(cypher, "KG1", "predicate triples")
    triples_dict = {"subject":[], "predicate":[], "object":[]}
    for result in results:
        subject_type = result.get('node1')
        object_type = result.get('node2')
        predicate = result.get('relationship')
        triples_dict['subject'].append(subject_type)
        triples_dict['object'].append(object_type)
        triples_dict['predicate'].append(predicate)
    return pd.DataFrame(triples_dict)


def get_kg2_predicate_triples():
    cypher = 'match (n)-[r]->(m) with distinct labels(n) as n1s, type(r) as rel, '+\
            'labels(m) as n2s unwind n1s as n1 unwind n2s as n2 with distinct n1 as '+\
            'node1, rel as relationship, n2 as node2 where node1 <> "Base" and '+\
            'node2 <> "Base" return node1, relationship, node2'
            # Changed this from using n.category so that it can handle node with multiple labels
            # Unfortunetly this makes the cypher a little more unweildly and likely slows a query a bit.
    results = run_neo4j_query(cypher, "KG2", "predicate triples")
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

def get_kg1_node_labels():
    cypher = 'call db.labels()'
    results = run_neo4j_query(cypher, "KG1", "node labels")
    labels_dict = {"label":[]}
    for result in results:
        label = result.get('label')
        labels_dict["label"].append(label)
    return pd.DataFrame(labels_dict)

def get_kg2_node_labels():
    cypher = 'call db.labels()'
    results = run_neo4j_query(cypher, "KG2", "node labels")
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

def get_kg1_relationship_types():
    cypher = 'call db.relationshipTypes()'
    results = run_neo4j_query(cypher, "KG1", "relationship types")
    predicate_dict = {"predicate":[]}
    for result in results:
        predicate = result.get('relationshipType')
        predicate_dict["predicate"].append(predicate)
    return pd.DataFrame(predicate_dict)

def get_kg2_relationship_types():
    cypher = 'call db.relationshipTypes()'
    results = run_neo4j_query(cypher, "KG2", "relationship types")
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
    
    kg1_triple_df = get_kg1_predicate_triples()
    kg2_triple_df = get_kg2_predicate_triples()
    kg2c_triple_df = get_kg2c_predicate_triples()
    kg1_triple_df.to_csv("KG1_allowed_predicate_triples.csv", index=False)
    kg2_triple_df.to_csv("KG2_allowed_predicate_triples.csv", index=False)
    kg2c_triple_df.to_csv("KG2c_allowed_predicate_triples.csv", index=False)

    kg1_labels_df = get_kg1_node_labels()
    kg2_labels_df = get_kg2_node_labels()
    kg2c_labels_df = get_kg2c_node_labels()
    kg1_labels_df.to_csv("KG1_allowed_node_labels.csv", index=False)
    kg2_labels_df.to_csv("KG2_allowed_node_labels.csv", index=False)
    kg2c_labels_df.to_csv("KG2c_allowed_node_labels.csv", index=False)

    kg1_labels_df = get_kg1_relationship_types()
    kg2_labels_df = get_kg2_relationship_types()
    kg2c_labels_df = get_kg2c_relationship_types()
    kg1_labels_df.to_csv("KG1_allowed_relationship_types.csv", index=False)
    kg2_labels_df.to_csv("KG2_allowed_relationship_types.csv", index=False)
    kg2c_labels_df.to_csv("KG2c_allowed_relationship_types.csv", index=False)
    print("----- script finished -----")

if __name__ == "__main__":
    main()