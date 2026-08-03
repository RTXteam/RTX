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

TRAIN_FILE = os.path.expanduser(
    "~/Desktop/code/generic_concept_training.parquet")
CANDIDATES_FILE = os.path.expanduser(
    "~/Desktop/code/generic_candidates.csv")

# Left out of the logistic fit, which has no way to read a string. XGBoost
# takes it directly through enable_categorical.
CATEGORICAL_FEATURES = ["category"]
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


def report_signs(features: pd.DataFrame, labels: pd.Series) -> None:
    """
    Print the direction each numeric feature pushes.

    Input:
        features: labelled design matrix.
        labels: 0/1 labels.

    Output:
        None. Writes to stdout. A positive coefficient means larger values
        argue for generic. Any feature whose sign contradicts what it is
        supposed to measure is worth investigating before trusting the
        boosted model, which reports only unsigned importances.
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


def evaluate(features: pd.DataFrame, labels: pd.Series,
             model: XGBClassifier) -> None:
    """
    Print cross-validated precision and recall.

    Input:
        features: labelled design matrix.
        labels: 0/1 labels.
        model: an unfitted classifier.

    Output:
        None. Writes to stdout. Scores come from cross_val_predict, so no
        row is scored by a model that saw it. PR-AUC rather than ROC-AUC
        because the classes are deliberately unbalanced and ROC-AUC reads
        optimistically when negatives dominate.
    """
    folds = StratifiedKFold(n_splits=N_FOLDS, shuffle=True,
                            random_state=SEED)
    scores = cross_val_predict(model, features, labels, cv=folds,
                               method="predict_proba")[:, 1]
    print(f"\nPR-AUC: {average_precision_score(labels, scores):.4f}")

    precision, recall, thresholds = precision_recall_curve(labels, scores)
    header = (f"{'precision target':<20}{'threshold':>11}"
              f"{'precision':>11}{'recall':>10}")
    print(f"\n{header}\n{'-' * len(header)}")
    for target in PRECISION_TARGETS:
        reached = np.where(precision[:-1] >= target)[0]
        if not len(reached):
            print(f"{target:<20.2f}{'not reached':>11}")
            continue
        i = reached[0]
        print(f"{target:<20.2f}{thresholds[i]:>11.3f}"
              f"{precision[i]:>11.3f}{recall[i]:>10.3f}")


def report_importances(model: XGBClassifier) -> None:
    """
    Print what the fitted model leaned on.

    Input:
        model: a fitted classifier.

    Output:
        None. Writes to stdout. Importances are unsigned, so read them
        alongside the linear coefficients above to know which way each
        feature points.
    """
    header = f"{'feature importance':<32}{'gain':>10}"
    print(f"\n{header}\n{'-' * len(header)}")
    for name, importance in sorted(zip(FEATURES, model.feature_importances_),
                                   key=lambda pair: -pair[1]):
        print(f"{name:<32}{importance:>10.3f}")


def dump_candidates(table: pd.DataFrame, model: XGBClassifier) -> None:
    """
    Score every node and write the confident unlabeled ones out.

    Input:
        table: every row, labelled or not.
        model: a fitted classifier.

    Output:
        None. Writes CANDIDATES_FILE and a count to stdout. Only unlabeled
        rows are written: the 1s and 0s are already decided, and these are
        the nodes whose names need reading to grow the seed set.
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


def main() -> None:
    table, features, labels = load()
    positives = int((labels == 1).sum())
    negatives = int((labels == 0).sum())
    print(f"labelled rows: {len(labels):,}   "
          f"positives: {positives:,}   negatives: {negatives:,}")

    report_signs(features, labels)

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

    evaluate(features, labels, model)
    model.fit(features, labels)
    report_importances(model)
    dump_candidates(table, model)


if __name__ == "__main__":
    main()
