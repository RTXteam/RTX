import json 
import os 
from collections import Counter, defaultdict
from stitch import local_babel as lb
import pandas as pd


NODES_FILE = os.path.expanduser("~/Desktop/code/database/tier0-20260621/knowledge_graph/nodes.jsonl")
BABEL = os.path.expanduser("~/Desktop/code/large_files/babel-20250901-p3.sqlite")
GENERAL_CONCEPTS = os.path.expanduser("~/Desktop/code/RTX/code/ARAX/KnowledgeSources/general_concepts_old.json")

normalized_concepts = defaultdict(set)

with open(GENERAL_CONCEPTS, encoding="utf-8") as handle: 
    curies = json.load(handle)["curies"]

results = lb.map_curies_to_preferred_curies(BABEL, tuple(curies))

for preferred, _clique, source in results: 
    normalized_concepts[source].add(preferred)

unresolved = [c for c in curies if c not in normalized_concepts]
candidates = {c.upper(): c for c in unresolved if c.upper() != c}
if candidates: 
    retry = lb.map_curies_to_preferred_curies(BABEL, tuple(candidates))
    for preferred, _clique, source in retry:
        normalized_concepts[candidates[source]].add(preferred)


unresolved = [c for c in curies if c not in normalized_concepts]

wanted = {c for preferred in normalized_concepts.values() for c in preferred}
wanted |= set(curies)


positives = []
with open(NODES_FILE, encoding="utf-8") as handle: 
    for line in handle: 
        node = json.loads(line)
        eqs = set(node.get("equivalent_identifiers", []))
        eqs.add(node["id"])
        matched = wanted & eqs 
        if matched: 
            positives.append({
                "id": node["id"],
                "name": node.get("name", ""),
                "category": node["category"],
                "matched_curies": sorted(matched)
            })

positives_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "data", "positive_generic.parquet")
pd.DataFrame.from_records(positives).to_parquet(positives_file, index=False)

print(f"input CURIEs:     {len(curies):,}")
print(f"  resolved:       {len(normalized_concepts):,}")
print(f"  unresolved:     {len(unresolved):,}")
print(f"wanted CURIEs:    {len(wanted):,}")
print(f"tier0 positives:  {len(positives):,}")

hit = {c for rec in positives for c in rec["matched_curies"]}
missed = wanted - hit 
print(Counter(c.split(":")[0] for c in missed).most_common(15))