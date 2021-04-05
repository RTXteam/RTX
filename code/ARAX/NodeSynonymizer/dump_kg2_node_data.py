"""
This script dumps KG2 node data to three files: one containing node ID, name, full_name, type for all KG2 nodes,
another containing node synonyms, and another containing pairs of equivalent nodes (connected by same_as edges in KG2).
These output files are used in the NodeSynonymizer build process.
Usage: python3 dump_kg2_node_data.py [--test]
"""
import argparse
import csv
import json
import traceback
from typing import List, Dict
import os
import sys
import re
from neo4j import GraphDatabase

import numpy as np
np.warnings.filterwarnings('ignore')

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../")  # code directory
from RTXConfiguration import RTXConfiguration
remove_tab_newlines = re.compile(r"\s+")


def dump_kg2_node_info(file_name: str, write_mode: str, is_test: bool):
	"""
	Dump node id, name, full_name, and category of all nodes in KG2.
	:param file_name: name of file to save to (TSV)
	:param write_mode: 'w' for overwriting the file, 'a' for appending to the file at the end (or creating a new on if it DNE)
	:param is_test: True if this is a test, False otherwise
	:return: None
	"""
	query = f"match (n) return properties(n) as p, labels(n) as l {'limit 20' if is_test else ''}"
	res = _run_cypher_query(query)
	with open(file_name, write_mode, encoding="utf-8") as fid:
		for item in res:
			prop_dict = item['p']
			labels = item['l']
			try:
				label = list(set(labels) - {'Base'}).pop()
			except:
				label = ""
			try:
				fid.write('%s\t' % prop_dict['id'])
			except:
				fid.write('\t')
			try:
				fid.write('%s\t' % remove_tab_newlines.sub(" ", prop_dict['name']))  # better approach
			except:
				fid.write('\t')
			try:
				fid.write('%s\t' % remove_tab_newlines.sub(" ", prop_dict['full_name']))
			except:
				fid.write('\t')
			try:
				fid.write('%s\n' % label)
			except:
				fid.write('\n')
	print(f"Successfully created file '{file_name}'.")
	return


def _run_cypher_query(cypher_query: str) -> List[Dict[str, any]]:
	# This function sends a cypher query to the KG2 neo4j and returns results
	rtxc = RTXConfiguration()
	rtxc.live = "KG2"
	try:
		driver = GraphDatabase.driver(rtxc.neo4j_bolt, auth=(rtxc.neo4j_username, rtxc.neo4j_password))
		with driver.session() as session:
			print(f"Sending cypher query to KG2 neo4j")
			query_results = session.run(cypher_query).data()
			print(f"Got {len(query_results)} results back from neo4j")
		driver.close()
	except Exception:
		tb = traceback.format_exc()
		error_type, error, _ = sys.exc_info()
		print(f"Encountered an error interacting with KG2 neo4j. {tb}")
		return []
	else:
		return query_results


def dump_kg2_equivalencies(output_file_name: str, is_test: bool):
	# This function creates a TSV file of node pairs linked by a 'same_as' relationship in KG2
	cypher_query = f"match (n1)-[:`biolink:same_as`]->(n2) return distinct n1.id, n2.id {'limit 20' if is_test else ''}"
	equivalent_node_pairs = _run_cypher_query(cypher_query)
	if equivalent_node_pairs:
		with open(output_file_name, "w+") as output_file:
			csv_writer = csv.writer(output_file, delimiter='\t')
			csv_writer.writerow(list(equivalent_node_pairs[0].keys()))  # Add header row
			distinct_pairs = {tuple(sorted([node_pair["n1.id"], node_pair["n2.id"]])) for node_pair in equivalent_node_pairs}
			csv_writer.writerows(list(distinct_pairs))
		print(f"Successfully created file '{output_file_name}'.")
	else:
		print(f"Sorry, couldn't get equivalency data. No file created.")


def dump_kg2_synonym_field(output_file_name: str, is_test: bool):
	# This function creates a JSON file of KG2 nodes and their synonyms as listed in the node "synonym" property
	cypher_query = f"match (n) where n.synonym is not null return n.id, n.synonym {'limit 20' if is_test else ''}"
	results = _run_cypher_query(cypher_query)
	if results:
		synonym_map = dict()
		with open(output_file_name, 'w+') as output_file:
			for row in results:
				curie = row['n.id']
				synonym_map[curie] = row['n.synonym']
			json.dump(synonym_map, output_file)
		print(f"Successfully created file '{output_file_name}'.")
	else:
		print(f"Sorry, couldn't get synonym data. No file created.")


def main():
	arg_parser = argparse.ArgumentParser()
	arg_parser.add_argument('--test', dest='test', action='store_true', default=False)
	args = arg_parser.parse_args()
	is_test = args.test

	dump_kg2_node_info('kg2_node_info.tsv', 'w', is_test)
	dump_kg2_equivalencies('kg2_equivalencies.tsv', is_test)
	dump_kg2_synonym_field('kg2_synonyms.json', is_test)
	print("Done dumping KG2 node data!")


if __name__ == "__main__":
	main()
