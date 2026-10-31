# Interview Presentation Script

How to present and analyse the People Analytics dashboard live, in simple, professional English.
Speak slowly, lead with the **decision**, and let each screen answer one business question.
When asked how the predictions are made, say it uses **AI / machine learning** — you do not need
to go deeper than that.

**Total time:** ~8–10 minutes presenting, then questions.

---

## 0. Opening (30 seconds)

> "Thank you. I built a People Analytics dashboard on public HR data to show how I would help
> the team turn workforce data into **retention decisions**.
>
> The whole tool answers one question for a leader: **who are we most likely to lose, why, and
> what should we do about it?** Let me walk you through it."

Keep it short. Then share your screen and start on the first page.

---

## 1. Executive Overview — "the state of the workforce"

**What to say:**
> "This is the one-screen summary a leader would open first. We have about **11,400 active
> employees**. Annual attrition is around **24%**. The number I care about most is here:
> **20% of the people who leave are our key talent** — that's what we call *regretted attrition*,
> the good people we did not want to lose."

**What to point at:**
- The headline sentence at the top (it states the decision in plain language).
- The KPI tiles — note the gold "signature" figure draws the eye to what matters.
- The **headcount chart** — "you can switch the window: 12, 24 or 36 months" (click it once to
  show it is interactive).
- The **9-box talent map** — "this is how we segment talent: performance against potential."
- The **attrition-by-function** chart — "this tells us *where* to start the conversation."

**The analysis (your insight):**
> "Right away we can see attrition is not spread evenly. **People & Experience, Finance and
> Technical** run the highest. So before any model, we already know where to look first."

---

## 2. Turnover Model — "what drives people to leave"

**What to say:**
> "Behind the dashboard is an **AI / machine-learning model** that scores every employee on how
> likely they are to leave. The point of this page is to show two things: that the model **works**,
> and **what drives the risk**."

**What to point at:**
- The "leavers caught" / accuracy tiles — "in simple terms, when it flags someone, it is very
  rarely wrong, and it catches almost everyone who actually left."
- The **risk-band chart** — "the riskiest group leaves far more often than the safest. The
  ranking is real, so we can focus effort on the top of the list."
- The **drivers chart** — "the biggest drivers are **low engagement**, then **tenure**,
  **working hours** and **workload**. These are things leaders can actually act on."

**The analysis — the honest check (this is your strongest moment):**
> "The most important question is not 'can we predict churn' — it's **'are we losing the right
> people or the wrong ones?'** If only weak performers left, that would be healthy. But look:
> **our Accelerate and Stretch talent leave at meaningful rates.** That is the problem this whole
> tool is built to fix."

---

## 3. Tenure & Lifecycle — "when do we lose people?"

**What to say:**
> "Retention is also a question of **timing**. This page looks at attrition across the employee
> journey."

**What to point at:**
- The **cliff chart** — "attrition is low early on, then it **peaks hard around the 5-year mark**,
  and almost disappears after 6 years. We call this the **mid-tenure cliff**."
- The **key-talent-vs-rest chart** — "and it is not healthy churn: we lose key talent in that
  same window."
- The **cohort selector** in the sidebar — "I can focus on any tenure group and see exactly who
  to watch."

**The analysis:**
> "This is actionable: the best time to act is **before** year four — onboarding, growth
> conversations and pay reviews land best in years two and three. Retention is a timing problem
> as much as a people problem."

---

## 4. Retention Priority — "who to act on now" (the heart of the tool)

**What to say:**
> "This is the page a leader would use every week. It is a single ranked list of the people we
> should focus on, built from three things they already think about: **how likely someone is to
> leave**, **how valuable their talent is**, and **whether they are underpaid**."

**What to point at:**
- The ranked table — "highest priority at the top."
- The filters in the sidebar — "I can filter by function, talent group or priority band, or
  search a name."
- **Click one person** to open their profile:
  - "Here is the *why* — their top risk drivers."
  - "Their engagement survey, theme by theme."
  - "Their pay position versus market."
  - "And a **suggested action** — for this person, a pay review / a development move / a manager
    check-in."

**The analysis:**
> "The goal is that a leader looks at one row and immediately knows **who, why, and what to do** —
> and can trust it, because every number drills down to the evidence behind it."

---

## 5. Pay Equity — "are we paying our best people fairly?"

**What to say:**
> "Pay is one of the biggest, most fixable drivers. About **19% of active employees sit below
> market.** The ones that worry me are here: **underpaid *and* high-value** — that's a double
> flight risk."

**What to point at:**
- The pay distribution and the "double-risk quadrant" — "top-left is strong performers paid below
  market. Act here first."
- The **what-if slider** in the sidebar (show this — it's memorable):
  > "I can set a fair-pay target and the **cost updates live**. Bringing our underpaid key talent
  > up to 95% of market costs roughly **a few million dollars a year** — a concrete number a
  > leader can take to a budget conversation."
- The action list — "named people, the gap to fair pay, ranked by size."

**The analysis:**
> "This turns a vague worry — 'are we fair?' — into a **priced, named action list.**"

---

## 6. Succession — "if we lose them, who steps in?"

**What to say:**
> "Finally, the flip side of risk: readiness. For any role, the tool finds the internal people
> whose profile is closest to the person in it."

**What to point at:**
- Pick the top flight risk (it loads by default).
- The ranked successors — "each one shows **why they fit**, their **development gaps**, and a
  **readiness** label: ready now, or one to two years away."

**The analysis:**
> "And it factors in retention — a great match who is themselves a flight risk is **not** a safe
> successor. So we see both the risk and the bench strength in one place."

---

## 7. Closing (20 seconds)

> "So the thread through the whole tool is simple: **predict who is at risk, confirm they are the
> people we value, explain why, price the fix, and name a successor.** It turns workforce data
> into decisions a leader can act on this week. I'd love to hear your questions."

---

## Anticipated questions & how to answer

**"How accurate is the model?"**
> "ROC-AUC 0.98 on employees it never saw. The public file repeats 3,000 records, so I
> grouped the split by record — a naive split would have shown 0.992. Public data is
> unusually clean; in production I'd expect a lower number and validate over time. For me the
> model is a means to the decision, not the headline."

**"Is this real Pernod Ricard data?"**
> "No — it's a public HR dataset. I added realistic talent, pay and survey layers on top, all
> reproducible, to show how the pieces come together. The numbers illustrate the method, not the
> company."

**"How does the priority score work?"**
> "It combines three things a leader already weighs: how likely someone is to leave, how valuable
> their talent is, and whether they are underpaid. One number, ranked."

**"What is regretted attrition?"**
> "It's when a *good* person — high performer, high potential — chooses to leave. That's the loss
> we most want to prevent, and the tool is built to catch it early."

**"What would you do next with more time / real data?"**
> "Connect it to live HR systems, add manager-level views, track the score over time, and most
> importantly **measure whether the suggested actions actually reduce attrition** — close the loop."

**"What's the business value?"**
> "It focuses limited retention budget on the few people who matter most, with a reason and an
> action next to each name — instead of reacting after they've already resigned."

---

## Quick reference — numbers to know

| Metric | Value |
|---|---|
| Active employees | ~11,400 |
| Annual attrition | ~24% |
| Regretted (key talent share of leavers) | ~20% |
| High-priority flight risks | ~37 (24 of them key talent) |
| Below market (compa-ratio < 0.90) | ~19% |
| Top drivers | engagement, tenure, hours, workload |
| Tenure cliff | peaks around year 5 |

---

## Delivery tips

- **Lead with the sentence, not the chart.** Every page has a headline — read it, then point to
  the chart that proves it.
- **Show one interaction per page** (the window toggle, the cohort selector, the pay slider, a
  profile click). It proves the tool is live, not a slide.
- **Use their words:** regretted attrition, talent call, 9-box, compa-ratio, flight risk.
- **Stay honest about limits.** Saying "this is optimistic on public data" builds more trust than
  claiming perfection.
- **End on the decision**, every time: who, why, what to do.
