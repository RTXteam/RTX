#!/bin/env python3

import os
import re
import sqlite3

database_name = 'autocomplete.sqlite'
try:
    os.remove(database_name)
except:
    pass

#create a data structure
conn = sqlite3.connect(database_name)
conn.text_factory = str
c = conn.cursor()

tablename = "term"
print(f"Creating table {tablename}")
#c.execute(f"CREATE TABLE {tablename}(curie TEXT, name TEXT, type TEXT, rank INTEGER)")
c.execute(f"CREATE TABLE {tablename}(term VARCHAR(255))")

rank = 1
row_count = 0
uc_terms = {}

with open("../../data/KGmetadata/NodeNamesDescriptions_KG2.tsv", 'r', encoding="latin-1", errors="replace") as nodeData:
    print("Loading node names")
    for line in nodeData:
        curie, name, type = line[:-1].split("\t")
        #c.execute("INSERT INTO %s(curie,name,type,rank) VALUES(?,?,?,?)" % (tablename), (curie,name,type,rank,))

        for term in [ name, curie ]:

            uc_term = term.upper()
            if uc_term not in uc_terms:
                c.execute("INSERT INTO %s(term) VALUES(?)" % (tablename), (term,))
                uc_terms[uc_term] = 1

        row_count += 1
        if row_count == int(row_count/1000000) * 1000000:
            print(f"{row_count}...", end='', flush=True)

print()
print(f"Creating index idx_{tablename}_term")
c.execute(f"CREATE INDEX idx_{tablename}_term ON {tablename}(term)")

conn.commit()
conn.close()
