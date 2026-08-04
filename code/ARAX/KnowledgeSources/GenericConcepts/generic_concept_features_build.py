import json
import math
import os
import sys
from collections import defaultdict, Counter

import numpy as np
import pandas as pd

nodes_file = "/home/hodgesf/Desktop/code/database/tier0-20260621/knowledge_graph/nodes.jsonl"
edges_file = "/home/hodgesf/Desktop/code/database/tier0-20260621/knowledge_graph/edges.jsonl"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NODES_TABLE = os.path.join(BASE_DIR, "data", "nodes_table.parquet")
PREDICTED_IC = os.path.join(BASE_DIR, "data", "predicted_ic_full.parquet")
NODE_EMBEDDINGS = os.path.expanduser(
    "~/Desktop/code/large_files/node_embeddings.npy")
CHUNK_SIZE = 50_000


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


def category_centroid_similarity(ids: pd.Series, categories: pd.Series,
                                 embeddings: np.ndarray) -> pd.DataFrame:
    codes, levels = pd.factorize(categories)
    sums = np.zeros((len(levels), embeddings.shape[1]))
    counts = np.zeros(len(levels))

    for start in range(0, len(codes), CHUNK_SIZE):
        block = np.asarray(embeddings[start:start + CHUNK_SIZE],
                           dtype=np.float64)
        block_codes = codes[start:start + CHUNK_SIZE]
        for code in np.unique(block_codes):
            member = block_codes == code
            sums[code] += block[member].sum(axis=0)
            counts[code] += member.sum()

    centroids = sums / counts[:, None]
    centroids /= np.linalg.norm(centroids, axis=1, keepdims=True)
    centroids = centroids.astype(np.float32)

    similarity = np.empty(len(codes), dtype=np.float32)
    for start in range(0, len(codes), CHUNK_SIZE):
        stop = start + CHUNK_SIZE
        block = np.asarray(embeddings[start:stop], dtype=np.float32)
        similarity[start:stop] = np.einsum(
            "ij,ij->i", block, centroids[codes[start:stop]])

    return pd.DataFrame({"id": ids.to_numpy(),
                         "cos_to_category_centroid": similarity})


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
    })

features = pd.DataFrame(rows)

nodes = pd.read_parquet(NODES_TABLE,
                        columns=["id", "most_specific_category"])
embeddings = np.load(NODE_EMBEDDINGS, mmap_mode="r")
centroid = category_centroid_similarity(
    nodes["id"], nodes["most_specific_category"], embeddings)

features = features.merge(pd.read_parquet(PREDICTED_IC), on="id", how="left")
features = features.merge(centroid, on="id", how="left")
features["ic_minus_predicted_ic"] = (features["information_content"]
                                     - features["predicted_ic"])

output_file = "/home/hodgesf/Desktop/code/generic_concept_features.parquet"
features.to_parquet(output_file, index=False)

print(f"\nWrote {len(features):,} rows to {output_file}")
print("\nColumns:")
for column in features.columns:
    filled = features[column].notna().mean()
    print(f"  {column:<28}{filled:>7.1%} populated")
print("\nTop predicates:")
for pred, n in predicate_histogram.most_common(25):
    print(f"  {n:>12,}  {pred}")
print(f"\nsubclass_of edges: {predicate_histogram.get('biolink:subclass_of', 0):,}")