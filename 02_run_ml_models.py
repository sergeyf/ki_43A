# -*- coding: utf-8 -*-
"""
Created on Wed Jan 13 14:39:19 2021

@author: sergey feldman
"""
from multiprocessing import freeze_support
import pickle
import numpy as np
from evaluate_utils import sklearn_pipeline_evaluator, lightgbm_hyperopt_evaluator, autogluon_evaluator
from linear_models import ridge_pipeline, ridge_grid
from linear_models import elasticnet_pipeline, elasticnet_grid
from linear_models import svr_pipeline, svr_grid
from splitting_utils import get_cv
from constants import RANDOM_STATE, N_SPLITS
from sklearn.dummy import DummyRegressor


def run_all_models(X, y, groups=None, additional_text_to_print=""):
    # define cross-validation splits ahead of time so we can reuse it and save it
    # currently the "groups" variable isn't used but it is useful for stratified splitting
    # in case, for example, that you have two rows per subject and you want to make sure
    # all the rows for a subject are either in train OR val OR test but not split up among them
    outer_cv = get_cv("regression", groups=groups is not None, n_splits=N_SPLITS, random_state=RANDOM_STATE)
    if groups is None:
        outer_cv = outer_cv.split(X, y)
    else:
        outer_cv = outer_cv.split(X, y, groups=groups)
    outer_cv = list(outer_cv)

    results = {}

    # this is a naive model. if you can't beat this, your ML doesn't work
    # it has no hyperparameters
    results["Constant Regressor"] = sklearn_pipeline_evaluator(
        X,
        y,
        DummyRegressor(),
        {},
        groups=groups,
        outer_cv=outer_cv,
        learning_task="regression",
    )

    # regularized linear regression
    # has a single hyperparameter
    results["Ridge Regression"] = sklearn_pipeline_evaluator(
        X,
        y,
        ridge_pipeline,
        ridge_grid,
        groups=groups,
        outer_cv=outer_cv,
        learning_task="regression",
    )

    # more advanced regularized linear regression
    # has a single hyperparameter but can be expanded to 2 if there's enough data
    results["ElasticNet"] = sklearn_pipeline_evaluator(
        X,
        y,
        elasticnet_pipeline,
        elasticnet_grid,
        groups=groups,
        outer_cv=outer_cv,
        learning_task="regression",
    )

    # a different advanced regularized linear regression
    # has a single hpyerpararameter
    results["Support Vector Regression"] = sklearn_pipeline_evaluator(
        X,
        y,
        svr_pipeline,
        svr_grid,
        groups=groups,
        outer_cv=outer_cv,
        learning_task="regression",
    )

    # ensemble of gradient boosted decision trees
    # has 11 hyperparamers and a good configuration of them is found by
    # bayesian search
    results["LightGBM"] = lightgbm_hyperopt_evaluator(
        X,
        y,
        groups=groups,
        outer_cv=outer_cv,
        learning_task="regression",
        lightgbm_objective="mae",
        lightgbm_metric="mae",
    )

    # ensemble of lots of models
    # no hyperparametrs
    # you have to specify how much time you want it to spend improving models in constants.py
    results["AutoGluon"] = autogluon_evaluator(
        X, y, groups=groups, learning_task="regression", autogluon_eval_metric="mean_absolute_error"
    )

    # print the mean absolute error for each model
    print(f"{additional_text_to_print} Mean Absolute Error:")
    print("--------------------------------------------------")
    for model_name, r in results.items():
        print(
            f"{model_name} (mean | standard deviation) --",
            np.round(-np.mean(r["test_score"]), 2),
            "|",
            np.round(np.std(r["test_score"]), 2),
        )
    print("--------------------------------------------------'\n")

    # return all the models and results
    return results, outer_cv


if __name__ == "__main__":
    # this prevents some obscure windows bugs...
    freeze_support()

    # load data
    with open("data/processed_data.pickle", "rb") as f:
        df_6m, input_covariates_6m, df_24m, input_covariates_24m = pickle.load(f)

    # define X and y for 6m predictions
    X_6m = df_6m[input_covariates_6m].values
    y_6m_raw = df_6m["mullen_6m_raw_average"].values

    # run models for 6m
    raw_6m_results, raw_6m_outer_cv = run_all_models(
        X_6m, y_6m_raw, groups=None, additional_text_to_print="Raw Mullen (6m)"
    )

    # define X and y for 24m predictions
    X_24m = df_24m[input_covariates_24m].values
    y_24m_raw = df_24m["mullen_24m_raw_average"].values

    # run models for 24m
    raw_24m_results, raw_24m_outer_cv = run_all_models(
        X_24m, y_24m_raw, groups=None, additional_text_to_print="Raw Mullen (24m)"
    )

    # save results and models
    with open("data/ml_results_raw.pickle", "wb") as f:
        pickle.dump((raw_6m_results, raw_6m_outer_cv, raw_24m_results, raw_24m_outer_cv), f)
