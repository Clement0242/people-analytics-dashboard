"""Business derivations shared across the pipeline and the app.

Keeps the talent-review vocabulary (9-box, talent call), the engagement-survey
schema, and the compensation logic in one place so the dataset builder, the model,
and the dashboard all speak the same language.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# --- Reproducibility -------------------------------------------------------
SEED = 42

# --- Schema constants ------------------------------------------------------
TARGET = "attrition"

# Clean business names for the raw HR.csv columns.
RENAME = {
    "satisfaction_level": "engagement_index",   # 0-1, ground-truth engagement driver
    "last_evaluation": "performance_raw",        # 0-1, performance proxy
    "number_project": "projects",
    "average_montly_hours": "avg_monthly_hours",
    "time_spend_company": "tenure_years",
    "Work_accident": "work_accident",
    "left": TARGET,
    "promotion_last_5years": "promoted_last_5y",
    "sales": "department",
    "salary": "salary_band",
}

DEPARTMENT_LABELS = {
    "sales": "Sales",
    "accounting": "Finance",
    "hr": "People & Experience",
    "technical": "Technical",
    "support": "Customer Support",
    "management": "Management",
    "IT": "IT",
    "product_mng": "Product",
    "marketing": "Marketing",
    "RandD": "R&D",
}

# Model feature set (numeric + the categoricals we one-hot in model.py).
NUMERIC_FEATURES = [
    "engagement_index",
    "performance_raw",
    "projects",
    "avg_monthly_hours",
    "tenure_years",
    "work_accident",
    "promoted_last_5y",
    "potential",
    "compa_ratio",
    "survey_score",
]
CATEGORICAL_FEATURES = ["department", "salary_band"]

# Human-readable labels for driver explanations on the priority list.
FEATURE_LABELS = {
    "engagement_index": "Low engagement",
    "performance_raw": "Performance",
    "projects": "Project load",
    "avg_monthly_hours": "Monthly hours",
    "tenure_years": "Tenure",
    "work_accident": "Work accident history",
    "promoted_last_5y": "No recent promotion",
    "potential": "Potential",
    "compa_ratio": "Pay vs market",
    "survey_score": "Survey sentiment",
}

# --- Engagement survey schema (27 questions across 6 dimensions) ------------
SURVEY_DIMENSIONS = {
    "Leadership & Manager": 5,
    "Career & Growth": 5,
    "Reward & Recognition": 4,
    "Workload & Wellbeing": 5,
    "Belonging & Conviviality": 4,
    "Enablement & Tools": 4,
}  # 5+5+4+5+4+4 = 27

# --- Talent call (9-box -> 3 talent-review groups) -------------------------
# Performance band x Potential band -> talent call.
#   Accelerate  = top talent, the people leadership must not lose.
#   Stretch     = high-potential growth candidates worth investing in.
#   Grow in role = the solid majority, developed in place.
TALENT_CALLS = ["Grow in role", "Stretch", "Accelerate"]
REGRETTED_CALLS = {"Accelerate", "Stretch"}


def _band(series: pd.Series) -> pd.Series:
    """1-5 rating -> Low (1-2) / Mid (3) / High (4-5)."""
    return pd.cut(series, bins=[0, 2, 3, 5], labels=["Low", "Mid", "High"])


def talent_call(perf_rating: pd.Series, potential: pd.Series) -> pd.Series:
    """Map the 9-box cell to a talent call."""
    pb, qb = _band(perf_rating).astype(str), _band(potential).astype(str)
    call = np.full(len(perf_rating), "Grow in role", dtype=object)
    # Stretch: high potential not yet at the top, or strong performers with mid potential.
    stretch = (
        ((qb == "High") & (pb.isin(["Low", "Mid"])))
        | ((qb == "Mid") & (pb == "High"))
    )
    call[stretch.to_numpy()] = "Stretch"
    # Accelerate: high potential and strong performance.
    accelerate = (qb == "High") & (pb == "High")
    call[accelerate.to_numpy()] = "Accelerate"
    return pd.Series(call, index=perf_rating.index)


def nine_box_cell(perf_rating: pd.Series, potential: pd.Series) -> pd.Series:
    """'Perf x Potential' label, e.g. 'High / Mid', for the 9-box grid."""
    return _band(perf_rating).astype(str) + " / " + _band(potential).astype(str)


# --- Compensation ----------------------------------------------------------
# Market midpoints (USD) by salary band, lightly modulated by department.
BAND_MIDPOINT = {"low": 58_000, "medium": 88_000, "high": 138_000}
DEPT_PAY_MULT = {
    "Sales": 1.05, "Finance": 1.02, "People & Experience": 0.98, "Technical": 1.06,
    "Customer Support": 0.92, "Management": 1.15, "IT": 1.08, "Product": 1.10,
    "Marketing": 1.00, "R&D": 1.07,
}
UNDERPAID_THRESHOLD = 0.90   # compa-ratio below this = underpaid vs market
