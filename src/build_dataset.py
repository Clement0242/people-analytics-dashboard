"""Build the augmented People Analytics dataset.

Backbone: Data/HR.csv (15k rows, real churn target). On top of it we add the
talent-review and reward layers a real People Analytics team works with but that
the public file lacks -- all deterministic (seeded) and anchored to the dataset's
own ground-truth driver, `engagement_index` (the original satisfaction level).

Run:  python src/build_dataset.py   ->  outputs/people_analytics.csv
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

import features as F

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "Data" / "HR.csv"
OUT = ROOT / "outputs" / "people_analytics.csv"
TODAY = date(2026, 6, 19)

FIRST_NAMES = (
    "Olivia Liam Emma Noah Ava Ethan Sophia Mason Isabella Lucas Mia Logan Amelia "
    "James Harper Benjamin Evelyn Henry Abigail Alexander Camille Theo Ines Hugo Lea "
    "Gabriel Chloe Nathan Manon Adrien Sarah Julien Laura Maxime Clara Antoine Jade "
    "Diego Sofia Mateo Valentina Andres Lucia Marco Giulia Kenji Yuki Aisha Omar"
).split()
LAST_NAMES = (
    "Martin Bernard Dubois Thomas Robinson Petit Durand Leroy Moreau Simon Laurent "
    "Lefebvre Michel Garcia Rodriguez Martinez Lopez Gonzalez Smith Johnson Williams "
    "Brown Jones Miller Davis Rossi Russo Ferrari Esposito Bianchi Nguyen Tanaka Sato "
    "Kim Park Hassan Ali Khan Costa Silva Santos Oliveira Schmidt Muller Weber Fischer"
).split()

COMMENT_BANK = {
    "low": [
        ("I don't see a path forward here and my workload is unsustainable.", "Workload & Wellbeing"),
        ("My contribution isn't recognised and the pay no longer reflects the market.", "Reward & Recognition"),
        ("No clear development plan; I've been in the same role too long.", "Career & Growth"),
        ("Hard to stay motivated without support from my manager.", "Leadership & Manager"),
    ],
    "mid": [
        ("Things are fine but I'd like more clarity on how to grow.", "Career & Growth"),
        ("Good team, though recognition could be more consistent.", "Reward & Recognition"),
        ("Workload spikes are tough but manageable for now.", "Workload & Wellbeing"),
        ("I appreciate the culture; I'd value better tools to do my job.", "Enablement & Tools"),
    ],
    "high": [
        ("Great manager and a real sense of belonging on the team.", "Belonging & Conviviality"),
        ("I feel trusted, challenged, and well supported to grow.", "Career & Growth"),
        ("Proud of what we build together -- genuinely convivial place.", "Belonging & Conviviality"),
        ("Fair recognition and the tools I need to perform.", "Reward & Recognition"),
    ],
}


def _to_rating_1_5(latent: np.ndarray, props: list[float]) -> np.ndarray:
    """Map a latent score to 1-5 using cumulative population proportions
    (a realistic top-heavy-rare talent distribution, not uniform)."""
    cuts = np.quantile(latent, np.cumsum(props)[:-1])
    return (np.searchsorted(cuts, latent) + 1).astype(int)


def build() -> pd.DataFrame:
    rng = np.random.default_rng(F.SEED)
    df = pd.read_csv(RAW).rename(columns=F.RENAME)
    n = len(df)
    df["department"] = df["department"].map(F.DEPARTMENT_LABELS)

    # --- Identity ---------------------------------------------------------
    df.insert(0, "employee_id", [f"PRUSA-{i:05d}" for i in range(1, n + 1)])
    df.insert(1, "name", [
        f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}" for _ in range(n)
    ])

    # --- Performance rating (1-5) from the 0-1 evaluation -----------------
    perf_latent = df["performance_raw"].to_numpy() + rng.normal(0, 0.06, n)
    df["performance_rating"] = _to_rating_1_5(perf_latent, [0.12, 0.28, 0.33, 0.20, 0.07])

    # --- Potential (1-5): perf + recent promotion + engagement, less tenure
    pot_latent = (
        0.55 * df["performance_raw"]
        + 0.80 * df["promoted_last_5y"]
        + 0.20 * df["engagement_index"]
        - 0.035 * df["tenure_years"]
        + rng.normal(0, 0.25, n)
    ).to_numpy()
    df["potential"] = _to_rating_1_5(pot_latent, [0.15, 0.35, 0.30, 0.15, 0.05])

    # --- 9-box and talent call -------------------------------------------
    df["nine_box"] = F.nine_box_cell(df["performance_rating"], df["potential"])
    df["talent_call"] = F.talent_call(df["performance_rating"], df["potential"])

    # --- Compensation: benchmark, compa-ratio, salary ---------------------
    midpoint = df["salary_band"].map(F.BAND_MIDPOINT).to_numpy()
    dept_mult = df["department"].map(F.DEPT_PAY_MULT).to_numpy()
    df["market_benchmark"] = np.round(
        midpoint * dept_mult * (1 + 0.02 * (df["performance_rating"] - 3))
        * (1 + rng.normal(0, 0.03, n)), -2
    ).astype(int)

    compa = rng.normal(1.0, 0.09, n)
    # Story seed: a share of key talent is quietly underpaid vs market.
    key = df["talent_call"].isin(F.REGRETTED_CALLS).to_numpy()
    underpay_hit = key & (rng.random(n) < 0.35)
    compa[underpay_hit] -= rng.uniform(0.06, 0.22, underpay_hit.sum())
    df["compa_ratio"] = np.clip(compa, 0.65, 1.45).round(3)
    df["salary"] = np.round(df["market_benchmark"] * df["compa_ratio"], -2).astype(int)

    # --- Engagement survey: 27 questions across 6 dimensions --------------
    eng5 = 1 + 4 * df["engagement_index"].to_numpy()          # engagement on a 1-5 base
    dim_offset = {
        "Leadership & Manager": 0.0,
        "Career & Growth": -0.30 + 0.80 * df["promoted_last_5y"].to_numpy(),
        "Reward & Recognition": -0.40 + 1.60 * (df["compa_ratio"].to_numpy() - 1.0),
        "Workload & Wellbeing": -0.70 * (df["avg_monthly_hours"].to_numpy() > 245),
        "Belonging & Conviviality": 0.15,
        "Enablement & Tools": -0.10,
    }
    q_idx, dim_means = 1, {}
    for dim, k in F.SURVEY_DIMENSIONS.items():
        cols = []
        for _ in range(k):
            q = np.clip(np.round(eng5 + dim_offset[dim] + rng.normal(0, 0.45, n)), 1, 5)
            col = f"q{q_idx:02d}"
            df[col] = q.astype(int)
            cols.append(col)
            q_idx += 1
        dim_means[f"survey_{dim}"] = df[cols].mean(axis=1).round(2)
    for col, vals in dim_means.items():
        df[col] = vals
    survey_cols = [f"q{i:02d}" for i in range(1, 28)]
    df["survey_score"] = df[survey_cols].mean(axis=1).round(2)

    # --- Free-text comment (theme-tagged) ---------------------------------
    tier = pd.cut(df["engagement_index"], [0, 0.45, 0.70, 1.01],
                  labels=["low", "mid", "high"]).astype(str)
    comments, themes = [], []
    for t in tier:
        text, theme = COMMENT_BANK[t][rng.integers(0, len(COMMENT_BANK[t]))]
        comments.append(text)
        themes.append(theme)
    df["comment_text"] = comments
    df["comment_theme"] = themes

    # --- Lifecycle: hire / termination / regretted ------------------------
    hire_offset = (df["tenure_years"].to_numpy() * 365
                   + rng.integers(0, 365, n)).astype(int)
    df["hire_date"] = [TODAY - timedelta(days=int(d)) for d in hire_offset]
    df["status"] = np.where(df[F.TARGET] == 1, "Departed", "Active")

    departed = df[F.TARGET] == 1
    # Spread departures over the last 24 months (the cross-section has no dates;
    # a 2-year window gives a realistic flow rather than a 12-month cliff).
    term_days = rng.integers(1, 731, n)
    term_date = [TODAY - timedelta(days=int(d)) for d in term_days]
    df["termination_date"] = np.where(departed, term_date, None)
    reason = np.where(rng.random(n) < 0.78, "Voluntary", "Involuntary")
    df["term_reason"] = np.where(departed, reason, None)
    df["regretted"] = (
        departed
        & df["talent_call"].isin(F.REGRETTED_CALLS)
        & (df["term_reason"] == "Voluntary")
    )

    return df


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df = build()
    df.to_csv(OUT, index=False)
    dep = df[F.TARGET] == 1
    print(f"Wrote {OUT.relative_to(ROOT)}  ({len(df):,} rows, {df.shape[1]} cols)")
    print(f"  Attrition rate        : {dep.mean():.1%}")
    print(f"  Regretted attrition   : {df['regretted'].mean():.1%} of all "
          f"({df.loc[dep, 'regretted'].mean():.1%} of leavers)")
    print(f"  Talent calls          : "
          + ", ".join(f"{k} {v}" for k, v in df['talent_call'].value_counts().items()))
    print(f"  Underpaid (compa<0.90): {(df['compa_ratio'] < F.UNDERPAID_THRESHOLD).mean():.1%}")
    print(f"  Mean survey score     : {df['survey_score'].mean():.2f} / 5")


if __name__ == "__main__":
    main()
