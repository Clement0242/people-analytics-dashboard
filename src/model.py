"""Train the attrition model, explain it, and compute the Retention Priority Score.

No SHAP dependency (keeps the stack light): global drivers come from permutation
importance; the per-employee "why" asks the model itself -- how much would this
person's predicted risk fall if one factor were at the company median? The factors
with the largest drop are their drivers.

Evaluation is deliberately strict. The public HR.csv contains 3,008 exact duplicate
rows: a random split puts the twin of ~29 % of test rows in the training set, which
flatters the score. The split here is grouped by identical profile, and the operating
threshold is chosen on out-of-fold predictions of the training set, never on the test.

Run:  python src/model.py
  ->  outputs/scored.csv   (per-employee probability, drivers, priority, action)
  ->  outputs/metrics.json (model quality + global importance + ROC curve)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    average_precision_score, confusion_matrix, f1_score, roc_auc_score, roc_curve,
)
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, cross_val_predict, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

import features as F

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "outputs" / "people_analytics.csv"
SCORED = ROOT / "outputs" / "scored.csv"
METRICS = ROOT / "outputs" / "metrics.json"

# Cost of losing each talent group -> weights the priority score.
TALENT_WEIGHT = {"Accelerate": 1.0, "Stretch": 0.65, "Grow in role": 0.30}


# Columns of the original public file: identical values = the same duplicated record.
SOURCE_COLUMNS = ["engagement_index", "performance_raw", "projects", "avg_monthly_hours",
                  "tenure_years", "work_accident", "promoted_last_5y", "department",
                  "salary_band", F.TARGET]


def make_pipe() -> Pipeline:
    return Pipeline([
        ("prep", ColumnTransformer(
            [("cat", OneHotEncoder(handle_unknown="ignore"), F.CATEGORICAL_FEATURES)],
            remainder="passthrough",
        )),
        ("clf", HistGradientBoostingClassifier(
            max_iter=300, learning_rate=0.08, max_leaf_nodes=31,
            l2_regularization=1.0, random_state=F.SEED,
        )),
    ])


def train(df: pd.DataFrame):
    X = df[F.NUMERIC_FEATURES + F.CATEGORICAL_FEATURES]
    y = df[F.TARGET].to_numpy()
    groups = pd.factorize(df[SOURCE_COLUMNS].astype(str).agg("|".join, axis=1))[0]

    # Naive random split, reported only to show how much the duplicates flatter it.
    a, b = train_test_split(np.arange(len(df)), test_size=0.25, stratify=y, random_state=F.SEED)
    naive = make_pipe().fit(X.iloc[a], y[a])
    naive_auc = roc_auc_score(y[b], naive.predict_proba(X.iloc[b])[:, 1])
    twins = float(np.isin(groups[b], groups[a]).mean())

    tr, te = next(GroupShuffleSplit(1, test_size=0.25, random_state=F.SEED).split(X, y, groups))
    X_tr, X_te, y_tr, y_te = X.iloc[tr], X.iloc[te], y[tr], y[te]
    pipe = make_pipe()
    # Operating threshold = best F1 on out-of-fold predictions of the TRAINING set.
    oof = cross_val_predict(pipe, X_tr, y_tr, groups=groups[tr], cv=GroupKFold(5),
                            method="predict_proba")[:, 1]
    pipe.fit(X_tr, y_tr)
    proba_te = pipe.predict_proba(X_te)[:, 1]

    auc = roc_auc_score(y_te, proba_te)
    pr_auc = average_precision_score(y_te, proba_te)
    fpr, tpr, thr = roc_curve(y_te, proba_te)
    grid = np.linspace(0.1, 0.9, 81)
    f1s = [f1_score(y_tr, oof >= t) for t in grid]
    thr_star = float(grid[int(np.argmax(f1s))])
    cm = confusion_matrix(y_te, proba_te >= thr_star)

    perm = permutation_importance(
        pipe, X_te, y_te, scoring="roc_auc", n_repeats=6, random_state=F.SEED
    )
    importance = dict(zip(X.columns, perm.importances_mean))

    # Risk direction of each numeric feature (sign of its correlation with attrition).
    corr = {c: float(np.corrcoef(X_tr[c], y_tr)[0, 1]) for c in F.NUMERIC_FEATURES}

    metrics = {
        "n_total": int(len(df)),
        "n_train": int(len(X_tr)),
        "n_test": int(len(X_te)),
        "roc_auc": round(float(auc), 4),
        "naive_roc_auc": round(float(naive_auc), 4),
        "duplicate_rows": int(len(df) - len(np.unique(groups))),
        "test_rows_with_twin_naive": round(twins, 3),
        "split": "grouped by identical source record (GroupShuffleSplit, 25 % test)",
        "pr_auc": round(float(pr_auc), 4),
        "base_rate": round(float(y.mean()), 4),
        "threshold": round(thr_star, 3),
        "confusion": {"tn": int(cm[0, 0]), "fp": int(cm[0, 1]),
                      "fn": int(cm[1, 0]), "tp": int(cm[1, 1])},
        "roc_curve": {"fpr": [round(float(v), 4) for v in fpr[:: max(1, len(fpr) // 200)]],
                      "tpr": [round(float(v), 4) for v in tpr[:: max(1, len(tpr) // 200)]]},
        "global_importance": {k: round(float(v), 5) for k, v in
                              sorted(importance.items(), key=lambda kv: -kv[1])},
        "feature_corr": {k: round(v, 4) for k, v in corr.items()},
    }
    return pipe, metrics, importance, corr, groups


DRIVER_LABELS = {  # (label when the person is below the median, label when above)
    "engagement_index": ("Low engagement", "High engagement"),
    "performance_raw": ("Low performance", "High performance"),
    "projects": ("Few projects", "Heavy project load"),
    "avg_monthly_hours": ("Low hours", "Long hours"),
    "tenure_years": ("Short tenure", "Long tenure"),
    "work_accident": ("No work accident", "Work accident"),
    "promoted_last_5y": ("No recent promotion", "Recent promotion"),
    "potential": ("Low potential", "High potential"),
    "compa_ratio": ("Pay below market", "Pay above market"),
    "survey_score": ("Low survey sentiment", "High survey sentiment"),
}


def local_drivers(pipe, df: pd.DataFrame, k: int = 3, min_drop: float = 0.02):
    """Top-k drivers per employee, asked of the model itself.

    For each factor, the factor is set to the company median (the rest of the
    profile unchanged) and the drop in predicted risk is measured. The factors
    with the largest drop are what pushes this person's risk up.
    """
    cols = F.NUMERIC_FEATURES + F.CATEGORICAL_FEATURES
    X = df[cols]
    base = pipe.predict_proba(X)[:, 1]
    drops, names = [], []
    for c in F.NUMERIC_FEATURES:
        med = float(X[c].median())
        Xc = X.copy()
        Xc[c] = med
        drops.append(base - pipe.predict_proba(Xc)[:, 1])
        lo, hi = DRIVER_LABELS[c]
        names.append(np.where(X[c].to_numpy() < med, lo, hi))
    drops = np.column_stack(drops)
    names = np.column_stack(names)
    order = np.argsort(-drops, axis=1)[:, :k]
    out = []
    for i, idx in enumerate(order):
        picked = [str(names[i, j]) for j in idx if drops[i, j] >= min_drop]
        out.append(picked or ["No dominant factor"])
    return out


def suggested_action(row) -> str:
    drv = row["drivers"]
    if row["compa_ratio"] < F.UNDERPAID_THRESHOLD or "Pay below market" in drv:
        return "Pay review — below market"
    if "No recent promotion" in drv or row["survey_Career & Growth"] < 2.6:
        return "Career & development move"
    if ("Long hours" in drv or "Heavy project load" in drv or row["avg_monthly_hours"] > 245
            or row["survey_Workload & Wellbeing"] < 2.6):
        return "Workload rebalance"
    if "Low engagement" in drv or row["survey_Leadership & Manager"] < 2.6:
        return "Manager check-in"
    return "Retention conversation"


def main() -> None:
    df = pd.read_csv(DATA)
    pipe, metrics, importance, corr, groups = train(df)

    # Every employee is scored by a model that never saw them (5-fold, grouped by
    # identical record): scoring the training rows in-sample would give the active
    # employees a risk of ~0 simply because the model learnt that they stayed.
    X = df[F.NUMERIC_FEATURES + F.CATEGORICAL_FEATURES]
    y = df[F.TARGET].to_numpy()
    df["p_attrition"] = np.zeros(len(df))
    df["drivers"] = [[] for _ in range(len(df))]
    for k_tr, k_te in GroupKFold(5).split(X, y, groups):
        m = make_pipe().fit(X.iloc[k_tr], y[k_tr])
        part = df.iloc[k_te]
        df.loc[df.index[k_te], "p_attrition"] = m.predict_proba(X.iloc[k_te])[:, 1]
        drv = local_drivers(m, part)
        for i, d in zip(df.index[k_te], drv):
            df.at[i, "drivers"] = d
    df["p_attrition"] = df["p_attrition"].round(4)
    df["driver_1"] = [d[0] if len(d) > 0 else "" for d in df["drivers"]]
    df["driver_2"] = [d[1] if len(d) > 1 else "" for d in df["drivers"]]
    df["driver_3"] = [d[2] if len(d) > 2 else "" for d in df["drivers"]]

    # Retention Priority Score (active employees only — you can't retain a leaver).
    talent_w = df["talent_call"].map(TALENT_WEIGHT).to_numpy()
    pay_factor = 1 + np.clip(0.95 - df["compa_ratio"].to_numpy(), 0, 0.30) * 2
    raw = df["p_attrition"].to_numpy() * talent_w * pay_factor
    active = (df["status"] == "Active").to_numpy()
    # Scaled to the highest active score (no clipping: a clipped scale ties the very
    # people the list exists to rank).
    df["priority_score"] = np.where(active, 100 * raw / raw[active].max(), np.nan).round(1)
    # Bands by rank, i.e. by capacity: a People team can hold a few dozen retention
    # conversations a quarter, not hundreds. High = top 0.5 % of active employees,
    # Medium = the next 2.5 %.
    rank = pd.Series(df["priority_score"]).rank(ascending=False, method="first")
    n_act = int(active.sum())
    df["priority_band"] = np.select(
        [rank <= round(0.005 * n_act), rank <= round(0.03 * n_act)], ["High", "Medium"], "Low")
    df.loc[~active, "priority_band"] = np.nan
    df["suggested_action"] = df.apply(
        lambda r: suggested_action(r) if r["status"] == "Active" else "", axis=1)

    df.drop(columns=["drivers"]).to_csv(SCORED, index=False)
    METRICS.write_text(json.dumps(metrics, indent=2))

    print(f"Wrote {SCORED.relative_to(ROOT)} and {METRICS.relative_to(ROOT)}")
    print(f"  ROC-AUC {metrics['roc_auc']} grouped split (naive random split "
          f"{metrics['naive_roc_auc']}, {metrics['duplicate_rows']} duplicate rows)  |  PR-AUC {metrics['pr_auc']}  "
          f"|  base rate {metrics['base_rate']:.1%}")
    top = list(metrics["global_importance"].items())[:5]
    print("  Top drivers: " + ", ".join(f"{k} ({v:.3f})" for k, v in top))
    hi_active = df.loc[active & (df["priority_band"] == "High")]
    print(f"  High-priority active employees: {len(hi_active):,} "
          f"(of which key talent: {hi_active['talent_call'].isin(F.REGRETTED_CALLS).sum():,})")


if __name__ == "__main__":
    main()
