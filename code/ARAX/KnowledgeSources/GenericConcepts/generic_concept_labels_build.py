"""
Attach training labels to the generic-concept feature table (issue-2654).

Reads the feature parquet produced by generic_concept_features_build.py and
adds a `label` column:

    label =  1   positive: node is generic
    label =  0   pseudo-negative: sampled from structurally clearly-NON-generic
                 nodes (a "reliable negative" pool, so we do not poison the
                 negatives with unlabeled generics)
    label = -1   unlabeled: everything else (kept so the same file can be scored)

Positives come from two sources:
  1. The curated blocklist (general_concepts.json), matched against each node's
     equivalent_identifiers -- NOT just its primary id. The KG is node-normalized,
     so ~77% of blocklist CURIEs live in equivalent_identifiers, not the id.
  2. An optional supplemental id list (SUPPLEMENTAL_POS): one node id per line.
     This is where LLM-confirmed generic nodes get folded in to grow the seed set
     without circularity (they are confirmed by NAME, which is not a model feature).

This is a positive-unlabeled setup: positives are clean, the rest is unlabeled.
"""
import json
import re
import random
from pathlib import Path

import pandas as pd

KG_DIR = "/home/hodgesf/Desktop/code/database/tier0-20260621/knowledge_graph"
NODES_FILE = f"{KG_DIR}/nodes.jsonl"
FEATURES_FILE = "/home/hodgesf/Desktop/code/generic_concept_features.parquet"
BLOCKLIST_FILE = str(Path(__file__).resolve().parent.parent / "general_concepts.json")
SUPPLEMENTAL_POS: str | None = "/home/hodgesf/Desktop/code/confirmed_generics.txt"  # audit-confirmed generics -> extra positives
HARD_NEGATIVES: str | None = "/home/hodgesf/Desktop/code/hard_negatives.txt"  # audit false positives -> forced negatives
OUTPUT_FILE = "/home/hodgesf/Desktop/code/generic_concept_training.parquet"

NEG_PER_POS = 10        # random pseudo-negatives per positive, ON TOP OF the curated
                        # hard negatives. Curated-only (0) inverts the model: with only
                        # high-degree hard negatives it flags every low-degree obscure
                        # specific as generic. Random draw supplies the low-degree
                        # specific negatives that anchor the boundary.
SEED = 2654


def load_blocklist(path: str) -> tuple[set[str], set[str], list[re.Pattern]]:
    block = json.load(open(path, encoding="utf-8"))
    curies = {c.lower() for c in block["curies"]}
    synonyms = {s.lower() for s in block["synonyms"]}
    patterns = [re.compile(p, re.IGNORECASE) for p in block["patterns"]]
    return curies, synonyms, patterns


def scan_nodes(nodes_file: str,
               curies: set[str],
               synonyms: set[str],
               patterns: list[re.Pattern]) -> tuple[set[str], dict[str, str]]:
    """Single nodes pass returning (positive ids, id->name).

    A node is positive if any of its equivalent_identifiers (or its id) is a
    blocklist CURIE, or its name matches a blocklist synonym/pattern. Names are
    collected for the eventual LLM audit / eyeballing."""
    positives: set[str] = set()
    names: dict[str, str] = {}
    with open(nodes_file, encoding="utf-8") as fp:
        for line in fp:
            rec = json.loads(line)
            nid = rec["id"]
            names[nid] = rec.get("name") or ""
            eqs = [e.lower() for e in rec.get("equivalent_identifiers", [])]
            eqs.append(nid.lower())
            name = names[nid].lower()
            # Positives are blocklist ITEMS present in the graph: a blocklist CURIE
            # in the node's equivalent_identifiers/id, or an exact blocklist-synonym
            # name match. Regex `patterns` are intentionally NOT used here -- they are
            # rule-based fuzzy matches that previously pulled in specific pathways as
            # false positives. Curated generics come in via SUPPLEMENTAL_POS.
            if curies.intersection(eqs):
                positives.add(nid)
            elif name and name in synonyms:
                positives.add(nid)
    return positives, names


def main() -> None:
    rng = random.Random(SEED)

    curies, synonyms, patterns = load_blocklist(BLOCKLIST_FILE)
    print("Scanning nodes for blocklist positives...")
    positives, names = scan_nodes(NODES_FILE, curies, synonyms, patterns)
    print(f"  blocklist positives: {len(positives):,}")

    if SUPPLEMENTAL_POS:
        extra = {ln.strip() for ln in open(SUPPLEMENTAL_POS, encoding="utf-8") if ln.strip()}
        positives |= extra
        print(f"  + supplemental positives: {len(extra):,}  (total {len(positives):,})")

    hard_neg: set[str] = set()
    if HARD_NEGATIVES:
        hard_neg = {ln.strip() for ln in open(HARD_NEGATIVES, encoding="utf-8") if ln.strip()}
        hard_neg -= positives  # a confirmed generic never becomes a hard negative
        print(f"  hard negatives (audit false positives): {len(hard_neg):,}")

    df = pd.read_parquet(FEATURES_FILE)
    df["name"] = df["id"].map(names)

    is_pos = df["id"].isin(positives)
    # Pseudo-negatives: sample uniformly at random from ALL non-positives, with no
    # feature-based filter. Selecting negatives by a feature (e.g. low child-count)
    # would bake that feature's bias into the labels -- the same leakage we avoid on
    # the positive side. True generics are rare in the graph, so random draw yields
    # only negligible (~0.1-0.5%) contamination of the negatives.
    neg_pool = df.loc[~is_pos & ~df["id"].isin(hard_neg), "id"]
    n_neg = min(NEG_PER_POS * int(is_pos.sum()), len(neg_pool))
    neg_ids = set(rng.sample(list(neg_pool), n_neg)) | hard_neg  # random + curated hard negatives

    df["label"] = -1
    df.loc[is_pos, "label"] = 1
    df.loc[df["id"].isin(neg_ids), "label"] = 0

    df.to_parquet(OUTPUT_FILE, index=False)
    counts = df["label"].value_counts()
    print(f"\nWrote {len(df):,} rows to {OUTPUT_FILE}")
    print(f"  positives (1): {counts.get(1, 0):,}")
    print(f"  negatives (0): {counts.get(0, 0):,}")
    print(f"  unlabeled (-1): {counts.get(-1, 0):,}")


if __name__ == "__main__":
    main()
