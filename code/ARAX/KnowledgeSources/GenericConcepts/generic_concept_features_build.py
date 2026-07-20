import json 
import math
import pandas as pd 
import sys
from collections import defaultdict, Counter

nodes_file = "/home/hodgesf/Desktop/code/database/tier0-20260621/knowledge_graph/nodes.jsonl"
edges_file = "/home/hodgesf/Desktop/code/database/tier0-20260621/knowledge_graph/edges.jsonl"

# The biolink "category" list is inconsistently ordered across nodes (some
# specificity-first, some alphabetical), so category[0] is not reliably the most
# specific type. Pick the most specific by skipping umbrella, union ("...Or..."),
# and mixin pseudo-classes.
_GENERIC_CATS = {
    "biolink:NamedThing", "biolink:Entity", "biolink:BiologicalEntity",
    "biolink:OntologyClass", "biolink:ThingWithTaxon",
    "biolink:PhysicalEssence", "biolink:PhysicalEssenceOrOccurrent",
    "biolink:Occurrent", "biolink:PhysicalEntity",
}

def most_specific_category(cats: list[str]) -> str:
    for c in cats:
        if c in _GENERIC_CATS or "Or" in c or c.endswith("Mixin"):
            continue
        return c
    return cats[0] if cats else ""


#------- NODES ---------#
own_cat: dict[str, str] = {}
ic: dict[str, float] = {}
name: dict[str, str] = {} 

with open(nodes_file, encoding="utf-8") as nf: 
    for line in nf: 
        rec = json.loads(line)
        nid = rec["id"]
        own_cat[nid] = most_specific_category(rec["category"])
        name[nid] = rec.get("name", "")
        v = rec.get("information_content")
        if v is not None: 
            ic[nid] = v


#-------- EDGES ---------#

degree = defaultdict(int)
neighbors = defaultdict(set)
neigh_cats = defaultdict(Counter)
pred_counts = defaultdict(Counter)
child_count = defaultdict(int)
predicate_histogram = Counter()

with open(edges_file, encoding="utf-8") as ef: 
    for line in ef: 
        rec = json.loads(line)
        s, o, p = rec["subject"], rec["object"], rec["predicate"]

        predicate_histogram[p] += 1

        if s not in own_cat or o not in own_cat: 
            continue 

        degree[s] += 1
        degree[o] += 1
        neighbors[s].add(sys.intern(o))
        neighbors[o].add(sys.intern(s))
        neigh_cats[s][own_cat[o]] += 1
        neigh_cats[o][own_cat[s]] += 1
        pred_counts[s][p] += 1
        pred_counts[o][p] += 1

        if p == "biolink:subclass_of": 
            child_count[o] += 1

def entropy(counter: Counter) -> float: 
    total = sum(counter.values())
    if total == 0: 
        return 0.0
    return -sum((c / total) * math.log2(c / total) for c in counter.values())

rows = []
for nid, cat in own_cat.items(): 
    nc = neigh_cats.get(nid, Counter())
    rows.append({
        "id": nid,
        "category": cat, 
        "degree": degree.get(nid, 0), 
        "unique_neighbors": len(neighbors.get(nid, ())),
        "distinct_neighbor_cats": len(nc),
        "neighbor_cat_entropy": entropy(nc),
        "predicate_entropy": entropy(pred_counts.get(nid, Counter())),
        "hierarchical_child_count": child_count.get(nid, 0),
        "information_content": ic.get(nid), 
        "ic_missing": nid not in ic,
    })

output_file = "/home/hodgesf/Desktop/code/generic_concept_features.parquet"
pd.DataFrame(rows).to_parquet(output_file, index = False)

print(f"\nWrote {len(rows):,} rows to {output_file}")
print("\nTop predicates:")
for pred, n in predicate_histogram.most_common(25):
    print(f"  {n:>12,}  {pred}")
print(f"\nsubclass_of edges: {predicate_histogram.get('biolink:subclass_of', 0):,}")