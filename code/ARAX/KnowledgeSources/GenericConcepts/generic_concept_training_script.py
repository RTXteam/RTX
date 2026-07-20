import pandas as pd 
import xgboost
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression 
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import average_precision_score, precision_recall_curve

TRAIN_FILE = "/home/hodgesf/Desktop/code/generic_concept_training.parquet"

FEATURES = [
    "degree",
    "distinct_neighbor_cats", 
    "neighbor_cat_entropy", 
    "predicate_entropy", 
    "hierarchical_child_count", 
    "information_content", 
    "ic_missing",
]

df = pd.read_parquet(TRAIN_FILE)

labeled = df[df["label"] >= 0].copy()
X = labeled[FEATURES]
y = labeled["label"]

logit = make_pipeline(
    SimpleImputer(strategy="median"),
    StandardScaler(),
    LogisticRegression(class_weight="balanced", max_iter = 1000)
)

logit.fit(X,y)
coefs = logit.named_steps["logisticregression"].coef_[0]
for name, c in sorted(zip(FEATURES, coefs), key=lambda t: -t[1]):
    print(f"  {c:+.3f} {name}")

pos = int((y == 1).sum())
neg = int((y == 0).sum())

model = XGBClassifier(
    n_estimators = 300, 
    max_depth = 4, 
    learning_rate = 0.05, 
    subsample=0.8, 
    colsample_bytree=0.8, 
    scale_pos_weight= neg / pos, 
    eval_metric="aucpr"
)

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=2654)
oof = cross_val_predict(model, X, y, cv=cv, method="predict_proba")[:, 1]
print("PR-AUC:", round(average_precision_score(y, oof), 4))

prec, rec, thr = precision_recall_curve(y, oof)
ok = np.where(prec[:-1] >= 0.95)[0]
if len(ok):
    i = ok[0]
    print(f"threshold {thr[i]:.3f}: precision {prec[i]:.3f}, recall {rec[i]:.3f}")
else:
    print("no threshold reaches 0.95 precision")

model.fit(X, y)   # refit on all labeled data

print("feature importances:")
for name, imp in sorted(zip(FEATURES, model.feature_importances_), key=lambda t: -t[1]):
    print(f"  {imp:.3f}  {name}")

df["score"] = model.predict_proba(df[FEATURES])[:, 1]
# Write EVERY unlabeled (-1) node the model ranks generic with confidence > 0.8.
# These are the nodes to review by name; labeled 1s/0s are already decided.
candidates = df[(df["label"] == -1) & (df["score"] > 0.8)].sort_values(
    "score", ascending=False)
candidates[["id", "name", "category", "score",
            "hierarchical_child_count", "information_content"]].to_csv(
    "/home/hodgesf/Desktop/code/generic_candidates.csv", index=False)
print(f"wrote {len(candidates)} candidates (unlabeled, score > 0.8)")