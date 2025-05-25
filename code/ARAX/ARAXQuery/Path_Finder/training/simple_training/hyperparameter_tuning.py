import logging

import optuna
import xgboost as xgb
from sklearn.metrics import ndcg_score

from data_loader import load_data


def custom_ndcg_scorer(estimator, X, y):
    preds = estimator.predict(X)
    return ndcg_score([y], [preds])


def split_with_group(group, x, y):
    training_size = int(len(group) * 0.9)
    x_training_size = 0
    for i in range(0, training_size, 1):
        x_training_size += group[i]

    return (x[: x_training_size],
            x[x_training_size:],
            y[: x_training_size],
            y[x_training_size:],
            group[:training_size],
            group[training_size:])


def tune_hyperparameters():
    x, y, group = load_data()

    X_train, X_valid, y_train, y_valid, group_train, group_valid = split_with_group(group, x, y)

    def objective(trial):
        logging.info("objective")
        params = {
            'objective': 'rank:pairwise',
            'eval_metric': 'ndcg',
            'eta': trial.suggest_float('eta', 0.01, 0.3, log=True),
            'max_depth': trial.suggest_int('max_depth', 3, 10),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
            'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
            'gamma': trial.suggest_float('gamma', 0, 5)
        }

        dtrain = xgb.DMatrix(X_train, label=y_train)
        dvalid = xgb.DMatrix(X_valid, label=y_valid)

        dtrain.set_group(group_train)
        dvalid.set_group(group_valid)

        bst = xgb.train(params, dtrain, num_boost_round=200,
                        evals=[(dvalid, 'validation')],
                        early_stopping_rounds=20, verbose_eval=False)

        preds = bst.predict(dvalid)
        score = ndcg_score([y_valid], [preds])

        return score

    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=50)

    logging.info(f"Best params: {study.best_params}")
    logging.info(f"Best NDCG score: {study.best_value}")
