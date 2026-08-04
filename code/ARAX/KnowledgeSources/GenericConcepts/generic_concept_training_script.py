"""
Train and evaluate the generic-concept classifier (issue-2654).

Fits XGBoost on the labelled rows of the training parquet, reports
cross-validated precision and recall, then scores every unlabeled node and
writes the confident ones out for review by name.

A logistic regression is fitted first purely to read the sign of each
feature. It is not the model: it exists so that a feature pulling the wrong
way is visible before the boosted trees hide it inside an importance score,
which is unsigned.

Input:
    TRAIN_FILE: feature table with a label column, from the labels build.

Output:
    CANDIDATES_FILE: unlabeled nodes the model ranks generic.
    Evaluation printed to stdout.
"""

import datetime
import json
import os

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, precision_recall_curve
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRAIN_FILE = os.path.expanduser(
    "~/Desktop/code/generic_concept_training.parquet")
CANDIDATES_FILE = os.path.expanduser(
    "~/Desktop/code/generic_candidates.csv")
ROUNDS_FILE = os.path.join(BASE_DIR, "data", "training_rounds.tsv")

# Biolink category is deliberately absent. Supplied as a split variable it
# became the second-strongest feature by round 6 of the review loop, and the
# model started classifying by category rather than by concept: 24.5% of every
# BiologicalProcess node in the graph ended up blocked. Category still reaches
# the model through predicted_ic and cos_to_category_centroid, which use it as
# context rather than as an axis to split on.
CATEGORICAL_FEATURES = []
NUMERIC_FEATURES = [
    "degree",
    "unique_neighbors",
    "distinct_neighbor_cats",
    "neighbor_cat_entropy",
    "predicate_entropy",
    "hierarchical_child_count",
    "information_content",
    "predicted_ic",
    "cos_to_category_centroid",
    "ic_minus_predicted_ic",
]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

PRECISION_TARGETS = (0.99, 0.95, 0.90, 0.80)
CANDIDATE_THRESHOLD = 0.8
N_FOLDS = 5
SEED = 2654


def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """
    Read the training table and split off the labelled rows.

    Input:
        None. Reads TRAIN_FILE.

    Output:
        Every row, the labelled design matrix, and its labels. The
        categorical column is cast to pandas category dtype, which is what
        XGBoost's enable_categorical consumes; missing numeric values are
        left as they are, because XGBoost learns a branch direction for
        them rather than needing them filled.
    """
    table = pd.read_parquet(TRAIN_FILE)
    for column in CATEGORICAL_FEATURES:
        table[column] = table[column].astype("category")

    labelled = table[table["label"] >= 0]
    return table, labelled[FEATURES], labelled["label"]


def next_round(path: str) -> int:
    """
    Work out which round this run is.

    Input:
        path: the append-only round log.

    Output:
        The number of rounds already recorded, so the first run is 0. Read
        off the file rather than tracked separately, which keeps the log the
        single source of truth for how far the loop has gone.
    """
    if not os.path.exists(path):
        return 0
    with open(path, encoding="utf-8") as handle:
        return max(0, sum(1 for _ in handle) - 1)


def append_round(path: str, row: dict) -> None:
    """
    Add one row to the round log, writing a header if the file is new.

    Input:
        path: the append-only round log.
        row: column name to value, in column order.

    Output:
        None. Appends rather than rewrites so a crashed or interrupted round
        cannot cost the history of the ones before it.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    write_header = not os.path.exists(path)
    with open(path, "a", encoding="utf-8") as handle:
        if write_header:
            handle.write("\t".join(row) + "\n")
        handle.write("\t".join(str(value) for value in row.values()) + "\n")


def report_signs(features: pd.DataFrame, labels: pd.Series) -> dict[str, float]:
    """
    Print the direction each numeric feature pushes.

    Input:
        features: labelled design matrix.
        labels: 0/1 labels.

    Output:
        Feature name to coefficient, and the same table on stdout. A positive
        coefficient means larger values argue for generic. Any feature whose
        sign contradicts what it is supposed to measure is worth investigating
        before trusting the boosted model, which reports only unsigned
        importances.
    """
    model = make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        LogisticRegression(class_weight="balanced", max_iter=1_000))
    model.fit(features[NUMERIC_FEATURES], labels)

    coefficients = model.named_steps["logisticregression"].coef_[0]
    header = f"{'linear coefficient':<32}{'weight':>10}"
    print(f"\n{header}\n{'-' * len(header)}")
    for name, weight in sorted(zip(NUMERIC_FEATURES, coefficients),
                               key=lambda pair: -pair[1]):
        print(f"{name:<32}{weight:>+10.3f}")

    return {name: round(float(weight), 4)
            for name, weight in zip(NUMERIC_FEATURES, coefficients)}


def evaluate(features: pd.DataFrame, labels: pd.Series,
             model: XGBClassifier) -> tuple[float, dict[float, dict]]:
    """
    Print cross-validated precision and recall.

    Input:
        features: labelled design matrix.
        labels: 0/1 labels.
        model: an unfitted classifier.

    Output:
        PR-AUC and the operating point reached for each precision target,
        and the same table on stdout. Scores come from cross_val_predict, so
        no row is scored by a model that saw it. PR-AUC rather than ROC-AUC
        because the classes are deliberately unbalanced and ROC-AUC reads
        optimistically when negatives dominate.
    """
    folds = StratifiedKFold(n_splits=N_FOLDS, shuffle=True,
                            random_state=SEED)
    scores = cross_val_predict(model, features, labels, cv=folds,
                               method="predict_proba")[:, 1]
    pr_auc = float(average_precision_score(labels, scores))
    print(f"\nPR-AUC: {pr_auc:.4f}")

    precision, recall, thresholds = precision_recall_curve(labels, scores)
    header = (f"{'precision target':<20}{'threshold':>11}"
              f"{'precision':>11}{'recall':>10}")
    print(f"\n{header}\n{'-' * len(header)}")

    points: dict[float, dict] = {}
    for target in PRECISION_TARGETS:
        reached = np.where(precision[:-1] >= target)[0]
        if not len(reached):
            print(f"{target:<20.2f}{'not reached':>11}")
            points[target] = {}
            continue
        i = reached[0]
        print(f"{target:<20.2f}{thresholds[i]:>11.3f}"
              f"{precision[i]:>11.3f}{recall[i]:>10.3f}")
        points[target] = {"threshold": round(float(thresholds[i]), 4),
                          "precision": round(float(precision[i]), 4),
                          "recall": round(float(recall[i]), 4)}
    return pr_auc, points


def report_importances(model: XGBClassifier) -> dict[str, float]:
    """
    Print what the fitted model leaned on.

    Input:
        model: a fitted classifier.

    Output:
        Feature name to gain, and the same table on stdout. Importances are
        unsigned, so read them alongside the linear coefficients above to
        know which way each feature points.
    """
    header = f"{'feature importance':<32}{'gain':>10}"
    print(f"\n{header}\n{'-' * len(header)}")
    for name, importance in sorted(zip(FEATURES, model.feature_importances_),
                                   key=lambda pair: -pair[1]):
        print(f"{name:<32}{importance:>10.3f}")

    return {name: round(float(importance), 4)
            for name, importance in zip(FEATURES, model.feature_importances_)}


def dump_candidates(table: pd.DataFrame, model: XGBClassifier) -> int:
    """
    Score every node and write the confident unlabeled ones out.

    Input:
        table: every row, labelled or not.
        model: a fitted classifier.

    Output:
        How many candidates were written. Writes CANDIDATES_FILE and a count
        to stdout. Only unlabeled rows are written: the 1s and 0s are already
        decided, and these are the nodes whose names need reading to grow the
        seed set.
    """
    table["score"] = model.predict_proba(table[FEATURES])[:, 1]
    candidates = table[(table["label"] == -1)
                       & (table["score"] > CANDIDATE_THRESHOLD)]
    candidates = candidates.sort_values("score", ascending=False)

    candidates[["id", "name", "category", "score", "predicted_ic",
                "information_content", "hierarchical_child_count"]].to_csv(
        CANDIDATES_FILE, index=False)
    print(f"\nwrote {len(candidates):,} candidates scoring above "
          f"{CANDIDATE_THRESHOLD} to {CANDIDATES_FILE}")
    return len(candidates)


def main() -> None:
    table, features, labels = load()
    positives = int((labels == 1).sum())
    negatives = int((labels == 0).sum())
    print(f"labelled rows: {len(labels):,}   "
          f"positives: {positives:,}   negatives: {negatives:,}")

    coefficients = report_signs(features, labels)

    model = XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=negatives / positives,
        enable_categorical=True,
        tree_method="hist",
        eval_metric="aucpr")

    pr_auc, points = evaluate(features, labels, model)
    model.fit(features, labels)
    importances = report_importances(model)
    n_candidates = dump_candidates(table, model)

    row = {
        "round": next_round(ROUNDS_FILE),
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "labelled": len(labels),
        "positives": positives,
        "negatives": negatives,
        "pr_auc": round(pr_auc, 4),
    }
    for target in PRECISION_TARGETS:
        tag = f"{int(target * 100)}"
        point = points[target]
        row[f"threshold_p{tag}"] = point.get("threshold", "")
        row[f"precision_p{tag}"] = point.get("precision", "")
        row[f"recall_p{tag}"] = point.get("recall", "")
    row["candidates"] = n_candidates
    row["coefficients"] = json.dumps(coefficients)
    row["importances"] = json.dumps(importances)

    append_round(ROUNDS_FILE, row)
    print(f"logged round {row['round']} to {ROUNDS_FILE}")


if __name__ == "__main__":
    main()
