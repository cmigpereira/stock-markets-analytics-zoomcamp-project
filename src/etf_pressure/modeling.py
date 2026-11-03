"""Expanding-window validation, purged labels, and a matched alternative-data ablation."""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import brier_score_loss, precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeClassifier

from etf_pressure.features import BASE, DUMMIES, FLOW


def make_model(kind, numeric, depth):
    prep = ColumnTransformer(
        [
            ("numeric", SimpleImputer(strategy="median"), numeric),
            ("category", OneHotEncoder(handle_unknown="ignore", sparse_output=False), DUMMIES),
        ]
    )
    if kind == "decision_tree":
        estimator = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=100, random_state=42)
    elif kind == "random_forest":
        estimator = RandomForestClassifier(
            n_estimators=140, max_depth=depth, min_samples_leaf=50, n_jobs=4, random_state=42
        )
    else:
        estimator = GradientBoostingClassifier(
            n_estimators=140,
            max_depth=depth,
            learning_rate=0.04,
            subsample=0.8,
            min_samples_leaf=50,
            random_state=42,
        )
    return Pipeline([("features", prep), ("model", estimator)])


def scores(y, p):
    return {
        "auc": float(roc_auc_score(y, p)) if len(np.unique(y)) > 1 else None,
        "brier": float(brier_score_loss(y, p)),
        "precision_at_055": float(precision_score(y, p >= 0.55, zero_division=0)),
        "observations": int(len(y)),
    }


def training_rows(labeled, cutoff):
    """A training outcome must already be known strictly before the next block."""
    return labeled[(labeled.date < cutoff) & (labeled.exit_date < cutoff)]


def train(frame, output="artifacts"):
    """2021–23 train, two expanding 2024 folds, 2025+ untouched test.

    Fit final models through 2024 only. Labels crossing each cutoff are purged.
    The dashboard's latest signals intentionally use these frozen research models.
    """
    directory = Path(output)
    directory.mkdir(parents=True, exist_ok=True)
    labeled = frame[frame.target_win.notna()].copy()
    if labeled.date.min() >= pd.Timestamp("2024-01-01") or labeled.date.max() < pd.Timestamp("2025-06-01"):
        raise ValueError("Research requires pre-2024 training, 2024 validation, and 2025+ test data")
    folds = [("2024-01-01", "2024-07-01"), ("2024-07-01", "2025-01-01")]
    experiments, models = [], {}
    test = labeled[labeled.date >= "2025-01-01"].copy()
    predictions = test.copy()
    # Tuning uses 2024 only, independently for each model and feature set.
    for kind in ["decision_tree", "random_forest", "gradient_boosting"]:
        for variant, numeric in [("price", BASE), ("flow", BASE + FLOW)]:
            candidates = []
            for depth in [3, 5]:
                fold_scores = []
                for cutoff, end in folds:
                    fit = training_rows(labeled, cutoff)
                    val = labeled[(labeled.date >= cutoff) & (labeled.date < end) & (labeled.exit_date < end)]
                    estimator = make_model(kind, numeric, depth)
                    estimator.fit(fit, fit.target_win.astype(int))
                    p = estimator.predict_proba(val)[:, 1]
                    fold_scores.append(scores(val.target_win.astype(int), p))
                candidates.append(
                    {
                        "depth": depth,
                        "brier": float(np.mean([s["brier"] for s in fold_scores])),
                        "folds": fold_scores,
                    }
                )
            best = min(candidates, key=lambda x: x["brier"])
            fit = training_rows(labeled, "2025-01-01")
            estimator = make_model(kind, numeric, best["depth"])
            estimator.fit(fit, fit.target_win.astype(int))
            name = f"{kind}_{variant}"
            p = estimator.predict_proba(test)[:, 1]
            predictions[f"p_{name}"] = p
            experiments.append(
                {
                    "name": name,
                    "variant": variant,
                    "kind": kind,
                    "depth": best["depth"],
                    "validation_brier": best["brier"],
                    **scores(test.target_win.astype(int), p),
                    "tuning": candidates,
                }
            )
            models[name] = estimator
            print(f"Model {name}: validation Brier {best['brier']:.4f}", flush=True)
    # Choose the model family with flow using validation only, never test performance.
    winner = min((e for e in experiments if e["variant"] == "flow"), key=lambda e: e["validation_brier"])
    kind = winner["kind"]
    predictions["p_flow"] = predictions[f"p_{kind}_flow"]
    predictions["p_price"] = predictions[f"p_{kind}_price"]
    latest = frame[frame.date.eq(frame.date.max())].copy()
    latest["p_flow"] = models[f"{kind}_flow"].predict_proba(latest)[:, 1]
    latest["p_price"] = models[f"{kind}_price"].predict_proba(latest)[:, 1]
    latest["eligible"] = latest.selloff.eq(1) & latest.p_flow.ge(0.55)
    for name, estimator in models.items():
        joblib.dump(estimator, directory / f"{name}.joblib")
    predictions.to_parquet(directory / "predictions.parquet", index=False)
    latest.to_parquet(directory / "latest.parquet", index=False)
    report = {
        "selected_family": kind,
        "threshold": 0.55,
        "train_label_cutoff": "2025-01-01",
        "test_start": "2025-01-01",
        "experiments": experiments,
        "constant_baseline": scores(test.target_win.astype(int), np.full(len(test), fit.target_win.mean())),
    }
    (directory / "models.json").write_text(json.dumps(report, indent=2))
    chosen = models[f"{kind}_flow"]
    importance = pd.DataFrame(
        {
            "feature": chosen["features"].get_feature_names_out(),
            "importance": chosen["model"].feature_importances_,
        }
    )
    importance.sort_values("importance", ascending=False).to_csv(directory / "importance.csv", index=False)
    return predictions, report
