#!/bin/env python3
"""
This script creates a TSV of node pairs linked by an 'equivalent_to'/'same_as' relationship in KG2. The TSV file is
created in the same directory the script is run from. Example of rows in the output file:
CUI:C0027358	CUI:C0014563
CUI:C0878440	CUI:C0014563
Usage: python dump_kg2_equivalencies.py
"""
import csv
import os
import sys
import traceback

from typing import List, Dict
from neo4j import GraphDatabase

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration


def _run_cypher_query(cypher_query: str, kg="KG2") -> List[Dict[str, any]]:
    # This function sends a cypher query to neo4j (either KG1 or KG2) and returns results
    rtxc = RTXConfiguration()
    if kg == "KG2":
        rtxc.live = "KG2"
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


def dump_kg2_equivalencies():
    # This function creates a TSV file of node pairs linked by an 'equivalent_to' or 'same_as' relationship in KG2
    cypher_query = f"match (n1)-[:equivalent_to|:same_as]->(n2) return distinct n1.id, n2.id"
    equivalent_node_pairs = _run_cypher_query(cypher_query)
    if equivalent_node_pairs:
        column_headers = equivalent_node_pairs[0].keys()
        file_name = "kg2_equivalencies.tsv"
        with open(file_name, "w+") as output_file:
            dict_writer = csv.DictWriter(output_file, column_headers, delimiter='\t')
            dict_writer.writeheader()
            dict_writer.writerows(equivalent_node_pairs)
        print(f"Successfully created file '{file_name}' containing results")
    else:
        print(f"Sorry, couldn't get equivalency data. No file created.")


def main():
    dump_kg2_equivalencies()


if __name__ == "__main__":
    main()
