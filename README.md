# People Analytics — Retention Priority Dashboard

A decision-first People Analytics dashboard that turns workforce data into **retention
action**. Built as a portfolio project for the *VIE Analyst, People Analytics* role at
Pernod Ricard USA, around the way the team actually works: talent reviews, regretted
attrition, the 9-box, compa-ratio, and engagement surveys.

> **The spine — a single Retention Priority Score:**
> `P(attrition)  ×  Talent value (9-box)  ×  Pay risk (low compa-ratio)`
> → a ranked, named list of the people leadership cannot afford to lose, each with the
> *why* (top risk drivers) and a suggested *action*.

The model is not the product. The **decision** is: *who* to act on, *why*, and *what to do* —
with every headline one click from its evidence.

![Executive Overview](docs/overview.png)

## What it answers

| Page | Leadership question |
|---|---|
| **Executive Overview** | Is the workforce healthy? How much attrition is *regretted*? Where does risk sit? |
| **Turnover Model** | What drives people to leave — and *are the good people the ones leaving*? |
| **Tenure & Lifecycle** | *When* in the journey do we lose people? Where is the mid-tenure cliff? |
| **Retention Priority** | Who do we act on now, and what do we do for each person? |
| **Pay Equity** | Are we paying our best people fairly? Who is underpaid *and* high-value (double risk)? |
| **Succession** | If we lose someone, who steps in? Internal successors by profile similarity. |

![Retention Priority list with employee profile](docs/priority.png)

## Approach

**Data.** Backbone is the public `Data/HR.csv` (14,999 employees, real `left` target). On
top of it, `src/build_dataset.py` adds — deterministically and seeded — the talent-review
and reward layers a real People team works with but that the public file lacks: a 27-question
engagement survey (6 dimensions), a 1–5 potential rating, the 9-box and talent call
(Accelerate / Stretch / Grow in role), numeric salary with a market benchmark and compa-ratio,
and lifecycle dates. The dataset's original satisfaction level is kept as the ground-truth
engagement driver, so the augmentation stays anchored to real signal.

**Model.** A gradient-boosting classifier (`HistGradientBoostingClassifier`) predicts
attrition (ROC-AUC ≈ 0.99 on a held-out test set — this dataset is highly separable). Global
drivers come from permutation importance. Per-employee "why" is a **transparent local
attribution** (no SHAP dependency): the factors where a person deviates most, in the
risk-increasing direction, weighted by how much each factor drives attrition overall.

**The honest check.** Predicting churn isn't enough — healthy churn (low performers leaving)
needs no action. The Turnover Model page verifies that **Accelerate / Stretch talent leave at
meaningful rates**, which is exactly what the priority list exists to stop.

**Succession matching.** When a role opens, the Succession page proposes internal
replacements by **profile similarity** — k-nearest-neighbours over performance, potential,
workload, tenure and function — then re-ranks candidates by readiness (performance × potential)
and retention (1 − flight risk), so a strong match who is themselves a flight risk isn't
offered as a safe successor. Each candidate comes with shared traits ("why they fit") and
development gaps.

![Turnover Model — drivers and the regretted-attrition check](docs/model.png)

![Pay Equity — the double-risk quadrant](docs/pay.png)

![Succession — ranked internal successors by profile similarity](docs/succession.png)

## Run it

```bash
python -m venv .venv && source .venv/Scripts/activate   # Git Bash on Windows
pip install -r requirements.txt

python src/build_dataset.py     # Data/HR.csv -> outputs/people_analytics.csv
python src/model.py             # train + score    -> outputs/scored.csv, metrics.json
streamlit run app/streamlit_app.py
```

## Structure

```
src/build_dataset.py   # augmented dataset (talent, survey, reward layers)
src/features.py        # shared business derivations (9-box, talent call, compa, survey schema)
src/model.py           # training, permutation importance, local drivers, priority score
app/streamlit_app.py   # entry point (page config, theme, navigation, logo + legend)
app/views.py           # the six pages
app/succession.py      # k-NN successor matching
app/theme.py           # design system: tokens, CSS, Plotly template, HTML helpers
app/assets/logo.png    # Pernod Ricard logo (sidebar)
PRODUCT.md / DESIGN.md # strategic + visual design context
```

## Honest limitations

- The survey, potential, compa-ratio and lifecycle dates are **synthetic augmentation** on a
  real attrition backbone — they illustrate the analytical method, not Pernod Ricard's actual
  numbers. All generation is seeded and reproducible.
- The 0.99 AUC reflects how separable this particular dataset is; on real HR data, expect lower.
- "Headcount evolution" reads flows from a cross-section (departures are spread over 24 months);
  it is descriptive, not a fitted forecast.

## Design

Premium corporate dark theme grounded in the real Pernod Ricard identity — **French navy** +
**summer blue** (trust, competence), with a warm **gold** reserved for value (priority, money,
the figures leaders read first), and the official logo in the sidebar. Serif (Fraunces) for
editorial moments, humanist sans (Hanken Grotesk) for all data. Diverging risk scales are
amber↔teal (colour-blind-safe). Interactive controls on every page (headcount window, tenure
cohort, pay what-if). See `DESIGN.md`.

## Documentation

- [`DATA_AND_MODEL.md`](DATA_AND_MODEL.md) — data sources, full data dictionary, models & scores.
- [`PRESENTATION_SCRIPT.md`](PRESENTATION_SCRIPT.md) — interview walkthrough, page by page.
- [`DESIGN.md`](DESIGN.md) · [`PRODUCT.md`](PRODUCT.md) — design system and product brief.

## Deploy (Streamlit Community Cloud)

The scored data (`outputs/scored.csv`, `outputs/metrics.json`) is committed, so the app runs with
no build step. Push to GitHub, then create an app at
[share.streamlit.io](https://share.streamlit.io) pointing at **`app/streamlit_app.py`** on `main`.
