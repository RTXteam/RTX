#!/usr/bin/env python3
"""
A script to convert massive JSON-lines files to TSV files with a tqdm progress meter.
Usage examples:
    python convert_jsonl_to_tsv.py --type nodes nodes.jsonl nodes.tsv
    python convert_jsonl_to_tsv.py --type edges edges.jsonl edges.tsv
"""

import json
import csv
import argparse
from tqdm import tqdm


def join_array(arr):
    """
    Convert a JSON list to a string joined by a special delimiter.
    If the input is not a list, simply return str(arr).
    (If you prefer a different delimiter, change 'ǂ' below.)
    """
    if isinstance(arr, list):
        return "ǂ".join(str(x) for x in arr)
    return str(arr)


def process_nodes(infile_path, outfile_path):
    """
    Process nodes.jsonl and write out nodes.tsv.

    Assumes that each JSON object has keys:
       id, name, category, all_names, all_categories, iri, equivalent_curies,
       and optionally description and publications.

    The header columns are:
       id, name, category, all_names, all_categories, iri, description,
       equivalent_curies, publications, :LABEL

    The :LABEL field is computed here as simply the value of the category field.
    """
    header = [
        "id",
        "name",
        "category",
        "all_names",
        "all_categories",
        "iri",
        "description",
        "equivalent_curies",
        "publications",
        ":LABEL"
    ]

    with open(infile_path, "r", encoding="utf-8") as fin, \
            open(outfile_path, "w", newline="", encoding="utf-8") as fout:
        writer = csv.writer(fout, delimiter="\t")
        writer.writerow(header)

        # Wrap the file iterator with tqdm to display a progress bar.
        for line in tqdm(fin, desc="Processing nodes", unit="line"):
            line = line.strip()
            if not line:
                continue
            try:
                node = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Extract and massage the fields.
            node_id = node.get("id", "")
            name = node.get("name", "")
            category = node.get("category", "")
            all_names = join_array(node.get("all_names", []))
            all_categories = join_array(node.get("all_categories", []))
            iri = node.get("iri", "")
            description = node.get("description", "")
            equivalent_curies = join_array(node.get("equivalent_curies", []))
            publications = join_array(node.get("publications", []))
            label = f"{category}"

            writer.writerow([
                node_id,
                name,
                category,
                all_names,
                all_categories,
                iri,
                description,
                equivalent_curies,
                publications,
                label
            ])


def process_edges(infile_path, outfile_path):
    """
    Process edges.jsonl and write out edges.tsv.

    Assumes that each JSON object has keys:
       subject, object, predicate, primary_knowledge_source,
       kg2_ids, domain_range_exclusion, knowledge_level, agent_type, id,
       and optionally publications, publications_info, qualified_predicate,
       qualified_object_aspect, qualified_object_direction.

    For the optional fields, if the value is a list it is joined;
    if it is a string it is used as is.
    Defaults are provided if a field is missing.

    The header columns are:
       subject, object, predicate, primary_knowledge_source, publications,
       publications_info, kg2_ids, qualified_predicate, qualified_object_aspect,
       qualified_object_direction, domain_range_exclusion, knowledge_level,
       agent_type, id, :TYPE, :START_ID, :END_ID

    The :TYPE column is set to the predicate,
    and :START_ID and :END_ID are taken from subject and object.
    """
    header = [
        "subject",
        "object",
        "predicate",
        "primary_knowledge_source",
        "publications",
        "publications_info",
        "kg2_ids",
        "qualified_predicate",
        "qualified_object_aspect",
        "qualified_object_direction",
        "domain_range_exclusion",
        "knowledge_level",
        "agent_type",
        "id",
        ":TYPE",
        ":START_ID",
        ":END_ID"
    ]

    with open(infile_path, "r", encoding="utf-8") as fin, \
            open(outfile_path, "w", newline="", encoding="utf-8") as fout:
        writer = csv.writer(fout, delimiter="\t")
        writer.writerow(header)

        # Wrap the file iterator with tqdm for progress.
        for line in tqdm(fin, desc="Processing edges", unit="line"):
            line = line.strip()
            if not line:
                continue
            try:
                edge = json.loads(line)
            except json.JSONDecodeError:
                continue

            subject = edge.get("subject", "")
            object_ = edge.get("object", "")
            predicate = edge.get("predicate", "")
            primary_knowledge_source = edge.get("primary_knowledge_source", "")

            # For these optional fields, use join_array so that if the value is a list,
            # it will be joined; if it's a string, it will be left as is.
            publications = join_array(edge.get("publications", "{}"))
            publications_info = join_array(edge.get("publications_info", ""))
            kg2_ids = join_array(edge.get("kg2_ids", []))
            qualified_predicate = join_array(edge.get("qualified_predicate", ""))
            qualified_object_aspect = join_array(edge.get("qualified_object_aspect", ""))
            qualified_object_direction = join_array(edge.get("qualified_object_direction", ""))

            domain_range_exclusion = str(edge.get("domain_range_exclusion", ""))
            knowledge_level = edge.get("knowledge_level", "")
            agent_type = edge.get("agent_type", "")
            edge_id = edge.get("id", "")

            type_field = predicate
            start_id = subject
            end_id = object_

            writer.writerow([
                subject,
                object_,
                predicate,
                primary_knowledge_source,
                publications,
                publications_info,
                kg2_ids,
                qualified_predicate,
                qualified_object_aspect,
                qualified_object_direction,
                domain_range_exclusion,
                knowledge_level,
                agent_type,
                edge_id,
                type_field,
                start_id,
                end_id
            ])


def main():
    parser = argparse.ArgumentParser(
        description="Convert massive JSON-lines files (nodes or edges) to TSV files with a progress meter."
    )
    parser.add_argument("input", help="Input JSON-lines file")
    parser.add_argument("output", help="Output TSV file")
    parser.add_argument("--type", choices=["nodes", "edges"], required=True,
                        help="The type of file to process: 'nodes' or 'edges'")
    args = parser.parse_args()

    if args.type == "nodes":
        process_nodes(args.input, args.output)
    elif args.type == "edges":
        process_edges(args.input, args.output)


if __name__ == "__main__":
    main()
