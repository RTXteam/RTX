#!/bin/env python3
"""
  create_json_of_kp_predicate_triples.py

  Creates a JSON of all distinct predicate triples for KG2c in the format
  {
    "url": "https://kg2.transltr.io/api/rtxkg2/v1.2",
    "TRAPI": true,
    "edges": [
       {
            "subject_category": "biolink:SmallMolecule",
            "object_category": "biolink:Disease",
            "predicate": "biolink:treats",
            "subject_id": "CHEBI:3002",     # beclomethasone dipropionate
            "object_id": "MESH:D001249"     # asthma
            "association": "biolink:ChemicalToDiseaseOrPhenotypicFeatureAssociation",
            "qualifiers": [
                 {
                      "qualifier_type_id": "biolink:causal_mechanism_qualifier"
                      "qualifier_value": "inhibition"
                 },
                 # ...other qualifier constraint type_id/value pairs?
             ]
        },
        # ...other test edges
   ]
}

  Usage: python3 create_json_of_kp_predicate_triples.py
  Returns: RTX_KG2c_test_triples.json
"""

# Adapted from Amy Glen's code in create_csv_of_kp_node_pairs.py

import sys
import os
import time
import json

from neo4j import GraphDatabase
#from RTXConfiguration import RTXConfiguration

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../")  # code directory
from RTXConfiguration import RTXConfiguration


def run_neo4j_query(cypher, kg_name, data_type):
    rtx_config = RTXConfiguration()
    rtx_config.neo4j_kg2 = kg_name
    driver = GraphDatabase.driver(rtx_config.neo4j_bolt, auth=(rtx_config.neo4j_username, rtx_config.neo4j_password))
    with driver.session() as session:
        start = time.time()
        print(f"Grabbing {data_type} from {kg_name} neo4j...")
        results = session.run(cypher).data()
        print(f"...done. Query took {round((time.time() - start) / 60, 2)} minutes.")
    driver.close()
    return results


def get_kg2_predicate_triples():
    cypher = 'match (n)-[e]-(m) where not (n.id starts with "biolink:") and not (m.id starts with "biolink:") ' + \
             'and (e.qualified_predicate is not null) with distinct n.category as `subject_category`, ' + \
             'e.predicate as `predicate`, e.qualified_predicate as `qualified_predicate`, ' + \
             'e.qualified_object_aspect as `qualified_object_aspect`, e.qualified_object_direction as ' + \
             '`qualified_object_direction`, m.category as `object_category`, min(n.id + "---" + m.id) as mk with *, ' + \
             'split(mk, "---") as s return `subject_category`, `predicate`, `qualified_predicate`, ' + \
             '`qualified_object_aspect`, `qualified_object_direction`, `object_category`, head(s) as subject, ' + \
             'head(tail(s)) as object'
    results = run_neo4j_query(cypher, "KG2c", "predicate triples")
    triples_dict = {"subject": [], "predicate": [], "object": []}
    test_triples_json = {"url": "https://kg2.transltr.io/api/rtxkg2/v1.4",
                         "TRAPI": True,
                         "edges": []
                         }
    for result in results:
        subject_category = result.get('subject_category')
        object_category = result.get('object_category')
        predicate = result.get('predicate')
        subject_id = result.get('subject')
        object_id = result.get('object')
        qualified_predicate = result.get('qualified_predicate')
        if qualified_predicate is not None:
            predicate = qualified_predicate
        qualified_object_aspect = result.get('qualified_object_aspect')
        if qualified_object_aspect is not None:
            qualifier_type_id_aspect = "biolink:aspect_qualifier"
            aspect_dict = {"qualifier_type_id": qualifier_type_id_aspect,
                           "qualifier_value": qualified_object_aspect}
        qualified_object_direction = result.get('qualified_object_direction')
        if qualified_object_direction is not None:
            qualifier_type_id_direction = "biolink:direction_qualifier"
            object_dict = {"qualifier_type_id": qualifier_type_id_direction,
                           "qualifier_value": qualified_object_direction}
        qualifiers_list = []
        if qualified_object_aspect is not None:
            qualifiers_list.append(aspect_dict)
        if qualified_object_direction is not None:
            qualifiers_list.append(object_dict)

        example = {
            "subject_category": subject_category,
            "object_category": object_category,
            "predicate": predicate,
            "subject_id": subject_id,
            "object_id": object_id,
            "qualifiers": qualifiers_list
        }
        test_triples_json['edges'].append(example)
    return test_triples_json


def main():
    print("----- starting script -----")

    KG2c_test_triples_json = get_kg2_predicate_triples()
    with open('RTX_KG2c_test_triples.json', 'w') as fp:
        json.dump(KG2c_test_triples_json, fp, indent=4)

    print("----- script finished -----")


if __name__ == "__main__":
    main()

