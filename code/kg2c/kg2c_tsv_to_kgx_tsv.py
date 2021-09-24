#!/usr/bin/env python3

''' Loads the KG2c TSV files nodes_c.tsv and edges_c.tsv (and the header files)
and writes out a nodes.tsv and edges.tsv in Translator KGX TSV format

    Usage: python3 kg2c_tsv_to_kgx_tsv.py
'''

import json
import sys

__author__ = 'Stephen Ramsey'
__copyright__ = 'Oregon State University'
__credits__ = ['Stephen Ramsey']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

max_edges = None  ## set to 100 for a test build

kg2c_special_delimiter = 'ǂ'

edge_fields_skip = {":START_ID",
                    ":END_ID",
                    ":TYPE"}

node_fields_skip = {":LABEL"}

edge_fields = []
edge_field_ids_drop = set()
edge_field_ids_listtype = set()
edge_fields_to_ids = dict()
node_fields_rename = {'category': 'specific_category',
                      'all_categories': 'category'}
node_fields_order = ['id', 'category', 'name', 'iri', 'description', 'publications', 'specific_category', 'equivalent_curies', 'all_names']

with open("edges_c_header.tsv", "r") as input_file:
    lines = input_file.readlines()
    if len(lines) != 1:
        sys.exit("one line of input expected in edges_c_header.tsv")
    field_id = 0
    for field in lines[0].rstrip().split("\t"):
        if field not in edge_fields_skip:
            if field.endswith(":string[]"):
                edge_field_ids_listtype.add(field_id)
            edge_fields.append(field.replace(":string[]", ""))
            edge_fields_to_ids[field] = field_id
        else:
            edge_field_ids_drop.add(field_id)
        field_id += 1

node_fields = []
node_field_ids_drop = set()
node_field_ids_listtype = set()
node_fields_to_ids = dict()

with open("nodes_c_header.tsv", "r") as input_file:
    lines = input_file.readlines()
    if len(lines) != 1:
        sys.exit("one line of input expected in nodes_c_header.tsv")
    field_id = 0
    for field in lines[0].rstrip().split("\t"):
        if field not in node_fields_skip:
            if field.endswith(":string[]"):
                node_field_ids_listtype.add(field_id)
            field_name_final = field.replace(":ID", "").replace(":string[]", "")
            node_fields.append(field_name_final)
            node_fields_to_ids[field_name_final] = field_id
        else:
            node_field_ids_drop.add(field_id)
        field_id += 1

if max_edges is None:
    node_ids_to_select = None
else:
    edge_counter = 0
    node_ids_to_select = set()

output_data = [edge_fields]
with open("edges_c.tsv", "r") as input_file:
    for line in input_file:
        output_fields = []
        field_id = 0
        for field in line.rstrip().split("\t"):
            if field_id not in edge_field_ids_drop:
                if field_id not in edge_field_ids_listtype:
                    output_fields.append(field)
                else:
                    output_fields.append("|".join(field.split(kg2c_special_delimiter)))
            else:
                pass
            field_id += 1
        output_data.append(output_fields)
        if max_edges is not None:
            for field_name in {"subject", "object"}:
                node_ids_to_select.add(output_fields[edge_fields_to_ids[field_name]])
            edge_counter += 1
            if edge_counter >= max_edges:
                break

with open("edges.tsv", "w") as output_file:
    for sublist in output_data:
        print("\t".join(sublist), file=output_file)

node_fields_renamed = [node_fields_rename.get(node_field, node_field) for node_field in node_fields]
sorted_node_fields = [node_fields_renamed.index(field) for field in node_fields_order]

output_data = [node_fields_renamed]
nodes_found = set()
with open("nodes_c.tsv", "r") as input_file:
    for line in input_file:
        output_fields = []
        field_id = 0
        for field in line.rstrip().split("\t"):
            if field_id not in node_field_ids_drop:
                if field_id not in node_field_ids_listtype:
                    output_fields.append(field)
                else:
                    output_fields.append("|".join(field.split(kg2c_special_delimiter)))
            else:
                pass
            field_id += 1
        if max_edges is not None:
            id = output_fields[node_fields_to_ids["id"]]
            if id in node_ids_to_select:
                keep_node = True
                nodes_found.add(id)
            else:
                keep_node = False
        else:
            keep_node = True
        if keep_node:
            output_data.append(output_fields)
        if max_edges is not None:
            if nodes_found == node_ids_to_select:
                break
            
with open("nodes.tsv", "w") as output_file:
    for sublist in output_data:
        print("\t".join([sublist[i] for i in sorted_node_fields]), file=output_file)

#print(json.dumps(output_data, indent=4, sort_keys=True))
#     for line in edges_header_file:
#         if edge_counter >= max_edges:
#             break
#         edge_counter += 1
