"""Succession & replacement matching.

When a role opens (a departure or a move), suggest the internal employees whose
profile most resembles the role's incumbent, then re-rank by readiness and by how
retainable each candidate is. The technique is similarity matching:

  1. Build a standardised feature vector per active employee (performance, potential,
     workload, tenure, level, engagement) plus a weighted one-hot of function, so
     same-function people sit close together but cross-function moves stay possible.
  2. k-Nearest-Neighbours (Euclidean) finds the profiles closest to the incumbent.
  3. A Successor Score blends profile match, readiness (performance × potential) and
     retention (1 − flight risk) — a strong match who is themselves about to leave is
     not a successor.

Returns, per candidate, a match %, a readiness label, the shared traits ("why") and
the gaps (for a development plan).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

# Role-relevant numeric features (what the job needs / who the person is).
SIM_NUMERIC = [
    "performance_rating", "potential", "projects", "avg_monthly_hours",
    "tenure_years", "survey_score",
]
SALARY_ORDINAL = {"low": 0.0, "medium": 1.0, "high": 2.0}
DEPT_WEIGHT = 2.2   # how strongly to prefer same-function candidates


def build_index(active: pd.DataFrame):
    """Fit the similarity index once over active employees.

    Returns (NearestNeighbors, feature matrix, scaler-aligned frame index).
    """
    num = active[SIM_NUMERIC].astype(float).copy()
    num["level"] = active["salary_band"].map(SALARY_ORDINAL).values
    z = StandardScaler().fit_transform(num)

    dept = pd.get_dummies(active["department"]).astype(float).values * DEPT_WEIGHT
    matrix = np.hstack([z, dept])

    nn = NearestNeighbors(n_neighbors=min(40, len(active)), metric="euclidean")
    nn.fit(matrix)
    return nn, matrix, active.index.to_numpy()


def _readiness(perf: float, pot: float) -> tuple[str, float]:
    """Talent-review readiness label + a 0-100 readiness value."""
    val = (perf + pot) / 10 * 100
    if perf >= 4 and pot >= 4:
        return "Ready now", val
    if perf >= 3 and pot >= 3:
        return "Ready in 1–2 years", val
    return "Development needed", val


def _shared_traits(t: pd.Series, c: pd.Series) -> list[str]:
    out = []
    if t["department"] == c["department"]:
        out.append(f"Same function ({c['department']})")
    if abs(int(c["performance_rating"]) - int(t["performance_rating"])) <= 1:
        out.append(f"Comparable performance ({int(c['performance_rating'])}/5)")
    if c["potential"] >= t["potential"]:
        out.append(f"Equal or higher potential ({int(c['potential'])}/5)")
    if abs(c["tenure_years"] - t["tenure_years"]) <= 2:
        out.append(f"Similar tenure ({int(c['tenure_years'])} yrs)")
    if t["salary_band"] == c["salary_band"]:
        out.append("Same level")
    return out[:4] or ["Closest available profile"]


def _gaps(t: pd.Series, c: pd.Series) -> list[str]:
    out = []
    if c["performance_rating"] < t["performance_rating"]:
        out.append(f"Performance below incumbent ({int(c['performance_rating'])} vs {int(t['performance_rating'])})")
    if c["potential"] < t["potential"]:
        out.append(f"Lower potential ({int(c['potential'])} vs {int(t['potential'])})")
    if c["department"] != t["department"]:
        out.append(f"Cross-function move (from {c['department']})")
    if c["tenure_years"] + 1 < t["tenure_years"]:
        out.append("Less experience in the organisation")
    return out[:3]


def find_successors(target_id: str, active: pd.DataFrame, nn, matrix,
                    pos_index, k: int = 5) -> tuple[pd.Series, pd.DataFrame]:
    """Top-k internal successors for the incumbent `target_id`."""
    loc = int(np.where(active["employee_id"].to_numpy() == target_id)[0][0])
    target = active.iloc[loc]

    dist, idx = nn.kneighbors(matrix[loc : loc + 1])
    dist, idx = dist[0], idx[0]
    keep = idx != loc                       # drop the incumbent themselves
    dist, idx = dist[keep], idx[keep]

    # Distance -> match %, scaled within this candidate pool.
    match = 100 * (1 - dist / (dist.max() + 1e-9))

    rows = []
    for d_match, j in zip(match, idx):
        c = active.iloc[j]
        label, ready_val = _readiness(c["performance_rating"], c["potential"])
        retain = (1 - c["p_attrition"]) * 100
        score = 0.45 * d_match + 0.35 * ready_val + 0.20 * retain
        rows.append({
            "employee_id": c["employee_id"], "name": c["name"],
            "department": c["department"], "talent_call": c["talent_call"],
            "performance_rating": int(c["performance_rating"]),
            "potential": int(c["potential"]),
            "match": round(d_match, 1), "readiness": label,
            "flight_risk": round(c["p_attrition"] * 100, 0),
            "successor_score": round(score, 1),
            "why": _shared_traits(target, c), "gaps": _gaps(target, c),
        })
    out = (pd.DataFrame(rows).sort_values("successor_score", ascending=False)
           .head(k).reset_index(drop=True))
    return target, out
