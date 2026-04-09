#!/usr/bin/env python3
"""Benchmark resolving 1000 names through NodeSynonymizer in small batches."""
import os
import sqlite3
import sys
import time

from tqdm import tqdm

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")

sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'NodeSynonymizer']))
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from node_synonymizer import NodeSynonymizer

# Grab 1000 names from the staging table
NGD_DIR = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery', 'Overlay', 'ngd'])
db_path = os.path.join(NGD_DIR, 'conceptname_to_pmids.sqlite')

TOTAL_NAMES = 1000

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT concept_name FROM staging LIMIT ?", (TOTAL_NAMES,))
# Strip whitespace in case the staging table still has dirty data
names = [row[0].strip() for row in cursor.fetchall() if row[0] and row[0].strip()]
conn.close()
print(f"Pulled {len(names)} clean names from staging\n")

synonymizer = NodeSynonymizer(autocomplete=False)
print(f"Name resolver URL: {synonymizer.name_resolver_url}")
print(f"Node normalizer URL: {synonymizer.api_base_url}\n")

# Test multiple small batch sizes since the API works fine at small sizes
for batch_size in [1, 5, 10, 25, 50]:
    name_batches = [names[i:i + batch_size]
                    for i in range(0, len(names), batch_size)]
    num_batches = len(name_batches)

    print(f"--- batch_size={batch_size} ({num_batches} sequential calls) ---")
    results = {}
    errors = 0
    start = time.time()

    for batch in tqdm(name_batches, desc=f"  batch={batch_size}", unit="call"):
        try:
            result = synonymizer.get_canonical_curies(names=batch)
            if result:
                results.update(result)
        except Exception as e:
            errors += 1
            print(f"  error: {e}")

    elapsed = time.time() - start
    recognized = sum(1 for v in results.values() if v and v.get('preferred_curie'))
    nulls = sum(1 for v in results.values() if v is None)

    print(f"  Total: {elapsed:.1f}s | {len(names)/elapsed:.0f} names/sec | "
          f"{elapsed/len(names)*1000:.1f}ms/name")
    print(f"  Recognized: {recognized}/{len(names)} ({recognized/len(names)*100:.1f}%)")
    print(f"  Nulls: {nulls} | Errors: {errors}\n")
