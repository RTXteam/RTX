#!/bin/env python3

import os
import re
import sqlite3
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-o", "--output", type=str, help="Output database path", default="autocomplete.sqlite", required=False)
parser.add_argument("-i", "--input", type=str, help="Input file path", default="../../data/KGmetadata/NodeNamesDescriptions_KG2.tsv", required=False)
arguments = parser.parse_args()

database_name = arguments.output
try:
    os.remove(database_name)
except:
    pass

#create a data structure
conn = sqlite3.connect(database_name)
conn.text_factory = str
c = conn.cursor()

print(f"Creating tables")
#c.execute(f"CREATE TABLE {tablename}(curie TEXT, name TEXT, type TEXT, rank INTEGER)")
c.execute(f"CREATE TABLE terms(term VARCHAR(255) COLLATE NOCASE)")
c.execute(f"CREATE TABLE cached_fragments(fragment VARCHAR(255) COLLATE NOCASE)")
c.execute(f"CREATE TABLE cached_fragment_terms(fragment_id INT, term VARCHAR(255) COLLATE NOCASE)")

rank = 1
row_count = 0
uc_terms = {}

with open(arguments.input, 'r', encoding="latin-1", errors="replace") as nodeData:
    print("Loading node names")
    for line in nodeData:
        curie, name, type = line[:-1].split("\t")
        #c.execute("INSERT INTO term(curie,name,type,rank) VALUES(?,?,?,?)" % (tablename), (curie,name,type,rank,))

        for term in [ name, curie ]:

            uc_term = term.upper()
            if uc_term not in uc_terms:
                c.execute("INSERT INTO terms(term) VALUES(?)", (term,))
                uc_terms[uc_term] = 1

        row_count += 1
        if row_count == int(row_count/1000000) * 1000000:
            print(f"{row_count}...", end='', flush=True)
            #break

print()
print(f"Creating indexes")
c.execute(f"CREATE INDEX idx_terms_term ON terms(term)")
c.execute(f"CREATE INDEX idx_cached_fragments_fragment ON cached_fragments(fragment)")

conn.commit()
conn.close()
