"""
Attach training labels to the generic-concept feature table (issue-2654).

Reads the feature parquet from generic_concept_features_build.py and adds a
`label` column:

    label =  1   positive: a curated generic concept
    label =  0   pseudo-negative: sampled uniformly from everything else
    label = -1   unlabeled: kept so the same file can be scored

Positives come from normalize_concepts.py, which normalises the hand-built
list through Babel and keeps whatever survives the join to tier0. This is a
positive-unlabeled setup: the positives are clean, the rest is unlabeled
rather than negative, and the pseudo-negatives are a sample drawn from that
unlabeled mass.

Input:
    FEATURES_FILE: one row per node, written by the feature build.
    POSITIVES: curated generic concepts.
    NODES_TABLE: node names, so candidates can be reviewed by name.

Output:
    OUTPUT_FILE: the feature table with name and label attached.
"""

import os
import random

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FEATURES_FILE = os.path.expanduser(
    "~/Desktop/code/generic_concept_features.parquet")
POSITIVES = os.path.join(BASE_DIR, "data", "positive_generic.parquet")
NODES_TABLE = os.path.join(BASE_DIR, "data", "nodes_table.parquet")
OUTPUT_FILE = os.path.expanduser(
    "~/Desktop/code/generic_concept_training.parquet")

# Pseudo-negatives per positive. Sampling none of them inverts the model:
# trained against curated hard negatives alone it learns that any low-degree
# obscure node is generic. The random draw supplies the ordinary specific
# nodes that anchor the boundary.
NEG_PER_POS = 10
SEED = 2654


def label(features: pd.DataFrame, positives: set[str],
          rng: random.Random) -> pd.DataFrame:
    """
    Add the label column in place and return the frame.

    Input:
        features: one row per node, keyed on id.
        positives: ids of curated generic concepts.
        rng: seeded source for the pseudo-negative draw.

    Output:
        The same frame with a label column. Pseudo-negatives are drawn
        uniformly from every non-positive with no feature-based filter:
        selecting them by a feature, say low child count, would bake that
        feature's bias straight into the labels. Generics are rare enough
        in the graph that a uniform draw contaminates the negatives only
        negligibly.
    """
    is_positive = features["id"].isin(positives)
    pool = features.loc[~is_positive, "id"]
    n_negative = min(NEG_PER_POS * int(is_positive.sum()), len(pool))
    negatives = set(rng.sample(list(pool), n_negative))

    features["label"] = -1
    features.loc[is_positive, "label"] = 1
    features.loc[features["id"].isin(negatives), "label"] = 0
    return features


def main() -> None:
    rng = random.Random(SEED)

    features = pd.read_parquet(FEATURES_FILE)
    positives = set(pd.read_parquet(POSITIVES, columns=["id"])["id"])
    names = pd.read_parquet(NODES_TABLE, columns=["id", "name"])
    features = features.merge(names, on="id", how="left")

    features = label(features, positives, rng)
    features.to_parquet(OUTPUT_FILE, index=False)

    counts = features["label"].value_counts()
    matched = int(counts.get(1, 0))
    print(f"\nWrote {len(features):,} rows to {OUTPUT_FILE}")
    print(f"  positives (1):  {matched:>9,}")
    print(f"  negatives (0):  {counts.get(0, 0):>9,}")
    print(f"  unlabeled (-1): {counts.get(-1, 0):>9,}")

    # A shortfall means the positives file names nodes the feature build
    # never saw, which would point at the two passes disagreeing about the
    # graph rather than at anything to do with labelling.
    if matched != len(positives):
        print(f"\n  warning: {len(positives) - matched:,} of "
              f"{len(positives):,} curated positives are absent from "
              "the feature table")


if __name__ == "__main__":
    main()
