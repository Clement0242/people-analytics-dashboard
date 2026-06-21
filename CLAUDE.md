# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A **People Analytics** portfolio project built to support an application/interview for the
*VIE Analyst, People Analytics* role at Pernod Ricard USA (New York). The interview is in
**English**, so all deliverables — code, dataset column names, the app, and the README —
must be written in **English**. (Conversation with the maintainer happens in French.)

The project recreates, on public Kaggle-style HR data, the people-analytics capabilities
the team actually uses (gathered from notes with a current jobholder). The central deliverable
is a **Retention Priority Score** that fuses three business dimensions into one actionable,
leader-facing output:

```
Retention Priority = P(attrition)  ×  Talent value (9-box)  ×  Pay risk (low compa-ratio)
```

The point is *not* a black-box model — it is the **integration** of attrition + talent + reward
+ engagement into a ranked list of **regretted-attrition flight risks** with the *why* (top
drivers) and a suggested *action* next to each person.

## People-analytics glossary (use these English terms)

These are the standard terms the modules implement; keep naming consistent with them.

| Concept | Meaning in this project |
|---|---|
| **Regretted attrition** | A *good* employee leaving (vs *non-regretted*). The thing leadership wants to prevent. |
| **Talent segmentation** | Talent-review labels: `Accelerate` / `Stretch` / `Grow in role`. Accelerate + Stretch = the people you must not lose. |
| **9-box grid** | Performance × Potential matrix; the talent segment is derived from it. |
| **Flight risk of key talent** | Predicted-to-leave AND in Accelerate/Stretch. |
| **Pay equity / compa-ratio** | `salary / market benchmark`. < ~0.9 = underpaid; underpaid high-performers = double risk. |
| **Engagement survey** | 27 questions on a 1–5 scale + free-text comments; driver analysis links it to attrition. |
| **Headcount forecasting** | Workforce planning: projecting hires (in) and departures (out). |

A core analytical check (explicitly requested by the jobholder): **verify that the people
predicted/observed to leave really are the high performers** — i.e. quantify regretted vs
non-regretted attrition, don't just predict churn.

## Data (`Data/`)

Three independent datasets with different schemas (not joinable). The backbone for the
turnover model is **HR.csv**.

- **`HR.csv`** — 15,000 rows. The classic HR-analytics churn set and the **backbone** of the
  model. Target = `left` (1/0). Key columns: `satisfaction_level` (0–1, the ground-truth
  engagement driver), `last_evaluation` (0–1, performance proxy), `number_project`,
  `average_montly_hours`, `time_spend_company` (tenure), `Work_accident`,
  `promotion_last_5years`, `sales` (= department), `salary` (low/medium/high band).
- **`HR_Data_MNC_Data Science Lovers.csv`** — ~2M rows. Has `Hire_Date`, `Status`
  (Active/Resigned), `Performance_Rating` (1–5), `Salary_INR`, `Department`, `Job_Title`,
  `Location`. Use for **headcount forecasting** and salary-benchmark/compa-ratio work
  (sample it; do not load 2M rows into the app). Spaces in the filename — quote it.
- **`HRDataset_v14.csv`** — 312 rows. Too small to model, but a realistic **schema reference**:
  `TermReason` (voluntary/involuntary → regretted vs not), `EngagementSurvey`, `EmpSatisfaction`,
  `PerformanceScore`, `ManagerName`, `Salary`, `Termd` (target). Note: header has a BOM and
  several free-text/categorical fields with trailing spaces — strip on load.

### Synthetic augmentation

HR.csv lacks layers the jobholder described, so `build_dataset.py` augments it (deterministically,
seeded) onto the 15k backbone — **`satisfaction_level` stays the ground-truth driver**:
- **27 survey questions (1–5)** correlated with `satisfaction_level`.
- **Potential** rating correlated with performance + promotion + low tenure → enables the 9-box.
- **Talent call** (Accelerate/Stretch/Grow in role) derived from the 9-box.
- **Numeric salary + market benchmark** (from the salary band & role) → **compa-ratio**.
- **Name / Employee ID** so the priority list is tangible.

## Intended architecture

No code exists yet; build in this order (each step is the foundation for the next):

```
src/build_dataset.py   # HR.csv -> augmented dataset (run first)  -> outputs/
src/features.py        # 9-box, talent call, compa-ratio derivations
src/model.py           # training + SHAP drivers + Retention Priority scoring
app/streamlit_app.py   # 4 pages (see below)
notebooks/01_exploration.ipynb  # EDA — shows the analytical approach for the interview
outputs/               # augmented dataset, trained model, figures (gitignore large files)
```

Streamlit app pages: **(1) Executive Overview** (turnover, regretted vs non-regretted,
headcount, 9-box distribution) · **(2) Turnover Model** (AUC/ROC, global drivers, the
"are the leavers actually the good ones?" check) · **(3) Retention Priority List** (ranked
actionable table, filters by department/talent call) · **(4) Pay Equity** (compa-ratio,
underpaid high-performers).

## Commands

Environment: **Python 3.14** (`python --version` → 3.14.6). Create a venv before installing.

```bash
# setup
python -m venv .venv && source .venv/Scripts/activate   # Git Bash on Windows
pip install -r requirements.txt

# pipeline (run in order)
python src/build_dataset.py        # writes augmented dataset to outputs/
python src/model.py                # trains model + writes scored output to outputs/

# dashboard
streamlit run app/streamlit_app.py
```

(`requirements.txt`, `src/`, and `app/` don't exist yet — create them as the project is built.)

## Conventions

- **English** for everything produced (identifiers, columns, UI strings, README) — interview is in English.
- Augmentation and any sampling must be **seeded** so results are reproducible across runs.
- This folder lives inside the larger `C:/Users/cverdier/Documents` git repo; it is **not** its
  own repo. Scope commits accordingly.
