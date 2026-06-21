# Data & Model Documentation

People Analytics dashboard — Pernod Ricard USA portfolio project.
This document explains **where the data comes from**, **every field it contains**, and **how
each model and score is built**. It is the technical companion to the dashboard; for the
interview walkthrough see `PRESENTATION_SCRIPT.md`.

---

## 1. The big picture

The dashboard runs on **one analytical dataset of 14,999 employees**. That dataset is built in
two steps:

```
Data/HR.csv  ──►  src/build_dataset.py  ──►  outputs/people_analytics.csv  ──►  src/model.py  ──►  outputs/scored.csv
 (real churn data)     (adds talent + pay + survey layers)                       (adds risk, drivers, priority, action)
```

1. **Backbone — real data.** A well-known public HR churn dataset (15,000 rows) provides the
   ground truth: who actually left, their satisfaction, performance, workload and tenure.
2. **Augmentation — realistic layers.** The public file lacks the talent-review, reward and
   engagement-survey layers a real People Analytics team works with. `build_dataset.py` adds
   them **deterministically (seeded)** and anchors them to the dataset's own signals, so the
   story is coherent and fully reproducible.
3. **Scoring.** `model.py` trains the attrition model, explains it, and computes the
   **Retention Priority Score** for every active employee.

> **Why augment?** The goal is to demonstrate the *integration* of attrition + talent + reward +
> engagement into one decision — the capability the team actually uses. The augmentation is
> labelled honestly throughout (see §6, Limitations).

---

## 2. Data sources

| File | Rows | Role |
|---|---|---|
| `Data/HR.csv` | 15,000 | **Backbone.** Real churn dataset. Target = `left` (1/0). Source of satisfaction, performance, workload, tenure, projects, department, salary band. |
| `Data/HR_Data_MNC_Data Science Lovers.csv` | ~2M | Reference for headcount/benchmark realism. Not loaded into the app. |
| `Data/HRDataset_v14.csv` | 312 | Schema reference for real-world HR fields (term reason, engagement, manager). Too small to model. |

Only the backbone feeds the live dashboard. The other two informed the schema and the realism
of the augmentation.

---

## 3. How the augmentation works

Everything is generated with a fixed random seed (`SEED = 42`), so the dataset is identical on
every run. Each added layer is tied to a real signal already in the data — nothing is random
noise.

| Layer | How it is derived | Anchored to |
|---|---|---|
| **Identity** (name, employee ID) | Generated labels (`PRUSA-00001`, …) | — (makes the list tangible) |
| **Performance rating (1–5)** | The 0–1 evaluation mapped to a realistic, top-heavy 1–5 scale | `performance_raw` |
| **Potential (1–5)** | Higher for strong performers, recently promoted, engaged people; lower with long tenure | performance + promotion + engagement − tenure |
| **9-box & talent call** | Performance band × potential band → talent group | performance × potential |
| **Market benchmark & compa-ratio** | A market salary per band & department; some key talent is deliberately underpaid | salary band, department, performance |
| **Engagement survey (27 questions)** | 27 question scores across 6 themes, correlated with engagement; pay theme tracks compa-ratio, workload theme tracks hours | `engagement_index` (+ compa, hours) |
| **Free-text comment** | One theme-tagged comment per person, matched to their engagement tier | `engagement_index` |
| **Lifecycle** (hire/termination date, term reason, regretted) | Dates inferred from tenure; leavers split voluntary/involuntary; "regretted" = a good person who chose to leave | tenure, talent call, `left` |

---

## 4. Data dictionary (`outputs/scored.csv`, 67 columns)

### Identity & organisation
| Field | Meaning |
|---|---|
| `employee_id` | Unique ID (`PRUSA-#####`) |
| `name` | Employee name |
| `department` | Function (Sales, Finance, People & Experience, Technical, Customer Support, Management, IT, Product, Marketing, R&D) |
| `salary_band` | low / medium / high |

### Behaviour & performance (from the real backbone)
| Field | Meaning |
|---|---|
| `engagement_index` | 0–1 satisfaction — the ground-truth engagement driver |
| `performance_raw` | 0–1 performance proxy (last evaluation) |
| `performance_rating` | 1–5 performance rating (derived) |
| `projects` | Number of projects |
| `avg_monthly_hours` | Average monthly hours worked |
| `tenure_years` | Years of service |
| `work_accident` | 1 if a work accident is on record |
| `promoted_last_5y` | 1 if promoted in the last 5 years |

### Talent review
| Field | Meaning |
|---|---|
| `potential` | 1–5 potential rating |
| `nine_box` | 9-box cell, e.g. `High / Mid` (performance / potential) |
| `talent_call` | **Accelerate** (top talent) / **Stretch** (high potential) / **Grow in role** (solid majority) |

### Reward
| Field | Meaning |
|---|---|
| `market_benchmark` | Estimated market salary for the role (USD) |
| `salary` | Actual salary (USD) |
| `compa_ratio` | `salary ÷ market_benchmark`. **1.00 = on market; below 0.90 = underpaid** |

### Engagement survey
| Field | Meaning |
|---|---|
| `q01`–`q27` | 27 survey questions, 1–5 |
| `survey_<dimension>` | Average score for each of 6 themes (Leadership & Manager, Career & Growth, Reward & Recognition, Workload & Wellbeing, Belonging & Conviviality, Enablement & Tools) |
| `survey_score` | Overall survey average (1–5) |
| `comment_text`, `comment_theme` | Free-text comment + its theme |

### Lifecycle
| Field | Meaning |
|---|---|
| `hire_date`, `termination_date` | Employment dates |
| `status` | Active / Departed |
| `attrition` | **Target.** 1 if the person left |
| `term_reason` | Voluntary / Involuntary |
| `regretted` | True = a good person (Accelerate/Stretch) who left voluntarily — **regretted attrition** |

### Model outputs (added by `model.py`)
| Field | Meaning |
|---|---|
| `p_attrition` | Predicted probability of leaving (0–1) |
| `driver_1/2/3` | The top 3 risk factors for that person, in plain language |
| `priority_score` | **Retention Priority Score** (0–100), active employees only |
| `priority_band` | High / Medium / Low |
| `suggested_action` | Recommended next step (pay review, career move, workload, manager check-in…) |

---

## 5. The models & scores

### 5.1 Attrition model — "who is likely to leave?"
- **What it is:** a gradient-boosting classifier (scikit-learn `HistGradientBoostingClassifier`)
  trained to predict `attrition` from 12 features (engagement, performance, projects, hours,
  tenure, work accident, promotion, potential, compa-ratio, survey score, department, salary band).
- **How it's trained:** 75% train / 25% test split, stratified on the target, fixed seed.
- **Quality on the held-out test set:**

  | Metric | Value | Reading |
  |---|---|---|
  | ROC-AUC | **0.99** | Ranks leavers vs stayers almost perfectly |
  | PR-AUC | **0.99** | Strong even though only ~24% leave |
  | Recall | **94%** | Catches 94% of people who actually left |
  | Precision | **99%** | When it flags someone, it is almost always right |
  | Base rate | **24%** | Company attrition in the data |

- **Targeting power:** the riskiest 20% of employees by predicted score contain the large
  majority of everyone who actually left — so retention effort can be concentrated, not sprayed.

### 5.2 Global drivers — "what makes people leave?"
Computed with **permutation importance** (how much the model's accuracy drops when each feature
is shuffled). The dominant drivers are **low engagement**, then **tenure**, **monthly hours**
and **project load** — the levers leaders can actually act on.

### 5.3 Local drivers — "why this person?"
For each employee, a transparent attribution shows the **top 3 factors where they deviate most
in the risk-increasing direction**, weighted by how much each factor drives attrition overall.
No black box: every "why" can be traced back to the person's own numbers.

### 5.4 Retention Priority Score — the spine of the product
A single 0–100 score that fuses the three signals leaders already reason about:

```
Retention Priority  =  P(attrition)  ×  Talent value  ×  Pay risk
```

- **P(attrition):** the model's probability.
- **Talent value:** weight by talent call — Accelerate 1.0, Stretch 0.65, Grow in role 0.30
  (you fight hardest for the people you can least afford to lose).
- **Pay risk:** a multiplier that rises as compa-ratio falls below 0.95 (underpaid = extra risk).

The raw score is scaled to 0–100 and split into **High / Medium / Low** bands. It is computed
for **active employees only** — you cannot retain someone who has already left.

### 5.5 Suggested action
A simple rules layer turns each person's drivers into a humane next step: *pay review* (below
market), *career & development move* (no recent promotion / weak growth scores), *workload
rebalance* (high hours / low wellbeing), *manager check-in* (low engagement / weak leadership
scores), or a general *retention conversation*.

### 5.6 Succession matching — "if we lose them, who steps in?"
For any role, a **nearest-neighbours** model finds the internal employees whose profile most
resembles the incumbent (performance, potential, workload, tenure, level, function). Each
candidate gets a **Successor Score** that blends profile match, readiness (performance ×
potential) and retention — a great match who is themselves a flight risk is *not* a safe
successor.

---

## 6. Honesty & limitations

This is a **portfolio project on public data**, and it says so:

- **Augmented layers.** Talent, pay and survey data are realistic but synthetic, anchored to the
  real signals. They demonstrate the *integration*, not real Pernod Ricard numbers.
- **The 0.99 AUC is optimistic.** On this clean public dataset the signal is unusually strong,
  and some augmented features are derived from the same drivers as the target. In production I
  would expect a lower score, watch carefully for **data leakage**, and validate over time
  rather than on a single split.
- **Cross-sectional dates.** The data has no real timeline; hire/termination dates are inferred
  from tenure to make headcount and lifecycle views possible.
- **The point is the decision, not the model.** The value is the ranked, explained, actionable
  retention list — and the honest check that the people leaving really are the good ones
  (regretted attrition), not just a churn probability.

---

## 7. How to reproduce

```bash
python -m venv .venv && source .venv/Scripts/activate   # Git Bash on Windows
pip install -r requirements.txt
python src/build_dataset.py     # Data/HR.csv -> outputs/people_analytics.csv
python src/model.py             # -> outputs/scored.csv + outputs/metrics.json
streamlit run app/streamlit_app.py
```

Everything is seeded, so the numbers above reproduce exactly.
