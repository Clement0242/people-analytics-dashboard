"""Train the attrition model, explain it, and compute the Retention Priority Score.

No SHAP dependency (keeps the stack light on Python 3.14): global drivers come from
permutation importance; per-employee "why" is a transparent local attribution -- the
factors where a person deviates most, in the risk-increasing direction, weighted by how
much each factor drives attrition overall.

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
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

import features as F

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "outputs" / "people_analytics.csv"
SCORED = ROOT / "outputs" / "scored.csv"
METRICS = ROOT / "outputs" / "metrics.json"

# Cost of losing each talent group -> weights the priority score.
TALENT_WEIGHT = {"Accelerate": 1.0, "Stretch": 0.65, "Grow in role": 0.30}


def train(df: pd.DataFrame):
    X = df[F.NUMERIC_FEATURES + F.CATEGORICAL_FEATURES]
    y = df[F.TARGET].to_numpy()
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.25, stratify=y, random_state=F.SEED
    )
    pipe = Pipeline([
        ("prep", ColumnTransformer(
            [("cat", OneHotEncoder(handle_unknown="ignore"), F.CATEGORICAL_FEATURES)],
            remainder="passthrough",
        )),
        ("clf", HistGradientBoostingClassifier(
            max_iter=300, learning_rate=0.08, max_leaf_nodes=31,
            l2_regularization=1.0, random_state=F.SEED,
        )),
    ])
    pipe.fit(X_tr, y_tr)
    proba_te = pipe.predict_proba(X_te)[:, 1]

    auc = roc_auc_score(y_te, proba_te)
    pr_auc = average_precision_score(y_te, proba_te)
    fpr, tpr, thr = roc_curve(y_te, proba_te)
    # Operating threshold = best F1 on the test set.
    grid = np.linspace(0.1, 0.9, 81)
    f1s = [f1_score(y_te, proba_te >= t) for t in grid]
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
    return pipe, metrics, importance, corr


def local_drivers(df: pd.DataFrame, importance: dict, corr: dict, k: int = 3):
    """Top-k risk-increasing factors per employee (transparent local attribution)."""
    num = df[F.NUMERIC_FEATURES].astype(float)
    z = (num - num.mean()) / num.std(ddof=0)
    sign = np.array([np.sign(corr[c]) or 1.0 for c in F.NUMERIC_FEATURES])
    w = np.array([max(importance.get(c, 0.0), 0.0) for c in F.NUMERIC_FEATURES])
    w = w / w.sum() if w.sum() else np.ones_like(w) / len(w)
    contrib = (z.to_numpy() * sign) * w                      # adverse, weighted
    labels = np.array([F.FEATURE_LABELS[c] for c in F.NUMERIC_FEATURES])

    order = np.argsort(-contrib, axis=1)[:, :k]
    drivers = []
    for i, idx in enumerate(order):
        picked = [labels[j] for j in idx if contrib[i, j] > 0]
        drivers.append(picked or ["No dominant factor"])
    return drivers


def suggested_action(row) -> str:
    drv = row["drivers"]
    if row["compa_ratio"] < F.UNDERPAID_THRESHOLD or "Pay vs market" in drv:
        return "Pay review — below market"
    if "No recent promotion" in drv or row["survey_Career & Growth"] < 2.6:
        return "Career & development move"
    if row["avg_monthly_hours"] > 245 or row["survey_Workload & Wellbeing"] < 2.6:
        return "Workload rebalance"
    if "Low engagement" in drv or row["survey_Leadership & Manager"] < 2.6:
        return "Manager check-in"
    return "Retention conversation"


def main() -> None:
    df = pd.read_csv(DATA)
    pipe, metrics, importance, corr = train(df)

    df["p_attrition"] = pipe.predict_proba(
        df[F.NUMERIC_FEATURES + F.CATEGORICAL_FEATURES])[:, 1].round(4)
    df["drivers"] = local_drivers(df, importance, corr)
    df["driver_1"] = [d[0] if len(d) > 0 else "" for d in df["drivers"]]
    df["driver_2"] = [d[1] if len(d) > 1 else "" for d in df["drivers"]]
    df["driver_3"] = [d[2] if len(d) > 2 else "" for d in df["drivers"]]

    # Retention Priority Score (active employees only — you can't retain a leaver).
    talent_w = df["talent_call"].map(TALENT_WEIGHT).to_numpy()
    pay_factor = 1 + np.clip(0.95 - df["compa_ratio"].to_numpy(), 0, 0.30) * 2
    raw = df["p_attrition"].to_numpy() * talent_w * pay_factor
    active = (df["status"] == "Active").to_numpy()
    hi = np.quantile(raw[active], 0.999)
    df["priority_score"] = np.where(active, np.clip(100 * raw / hi, 0, 100), np.nan).round(1)
    df["priority_band"] = pd.cut(
        df["priority_score"], [-0.1, 33, 66, 100.1], labels=["Low", "Medium", "High"])
    df["suggested_action"] = df.apply(
        lambda r: suggested_action(r) if r["status"] == "Active" else "", axis=1)

    df.drop(columns=["drivers"]).to_csv(SCORED, index=False)
    METRICS.write_text(json.dumps(metrics, indent=2))

    print(f"Wrote {SCORED.relative_to(ROOT)} and {METRICS.relative_to(ROOT)}")
    print(f"  ROC-AUC {metrics['roc_auc']}  |  PR-AUC {metrics['pr_auc']}  "
          f"|  base rate {metrics['base_rate']:.1%}")
    top = list(metrics["global_importance"].items())[:5]
    print("  Top drivers: " + ", ".join(f"{k} ({v:.3f})" for k, v in top))
    hi_active = df.loc[active & (df["priority_band"] == "High")]
    print(f"  High-priority active employees: {len(hi_active):,} "
          f"(of which key talent: {hi_active['talent_call'].isin(F.REGRETTED_CALLS).sum():,})")


if __name__ == "__main__":
    main()
