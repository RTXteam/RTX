#!/usr/bin/env python3
"""Create the autocomplete SQLite database from a TSV of names and IDs."""

import os
import sqlite3
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-o", "--output", required=True, help="Output database path")
parser.add_argument("-i", "--input", required=True, help="Input TSV path")
args = parser.parse_args()

# Normalize paths
args.output = os.path.abspath(args.output)
args.input = os.path.abspath(args.input)

# Ensure output directory exists
os.makedirs(os.path.dirname(args.output), exist_ok=True)

# Ensure input file exists
if not os.path.exists(args.input):
    raise FileNotFoundError(f"Input not found: {args.input}")

database_name = args.output

# Remove existing DB if present
try:
    os.remove(database_name)
except FileNotFoundError:
    pass

# Create SQLite DB
conn = sqlite3.connect(database_name)
conn.text_factory = str
c = conn.cursor()

print("Creating tables")
c.execute("CREATE TABLE terms(term VARCHAR(255) COLLATE NOCASE)")
c.execute("CREATE TABLE cached_fragments(fragment VARCHAR(255) COLLATE NOCASE)")
c.execute("CREATE TABLE cached_fragment_terms(fragment_id INT, term VARCHAR(255) COLLATE NOCASE)")

row_count = 0
uc_terms = {}

print("Loading node names")
with open(args.input, 'r', encoding="latin-1", errors="replace") as nodeData:
    for line in nodeData:
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 2:
            continue
        curie, name = parts[0], parts[1]

        for term in (name, curie):
            if not term:
                continue
            uc_term = term.upper()
            if uc_term not in uc_terms:
                c.execute("INSERT INTO terms(term) VALUES(?)", (term,))
                uc_terms[uc_term] = 1

        row_count += 1
        if row_count % 1_000_000 == 0:
            print(f"{row_count}...", end="", flush=True)

print("\nCreating indexes")
c.execute("CREATE INDEX idx_terms_term ON terms(term)")
c.execute("CREATE INDEX idx_cached_fragments_fragment ON cached_fragments(fragment)")

conn.commit()
conn.close()
