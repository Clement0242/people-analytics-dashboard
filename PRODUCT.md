# Product

## Register

product

## Users

Primary: **People & Experience leaders and senior decision-makers** at Pernod Ricard USA —
people who run talent reviews, own headcount, and decide where to spend retention effort.
They are time-poor, business-minded, and read for the *decision*, not the methodology. They
see the dashboard over a **screen-share on a video call**, narrated live by the analyst.

Secondary: the **People Analytics analyst** (the maintainer) who presents it and answers
"how did you get this number?" on the spot. The interface must let them drill from a headline
to the evidence in one or two clicks.

## Product Purpose

A People Analytics dashboard that turns workforce data into **retention decisions**. Its
spine is a single **Retention Priority Score** fusing three signals leaders already reason
about — probability of attrition, talent value (9-box / talent call), and pay risk
(compa-ratio) — into a ranked, named list of **regretted-attrition flight risks**, each with
the *why* (top drivers) and a suggested *action*.

Success = a leader looks at one screen and knows **who** to act on, **why**, and **what** to
do — and trusts it, because every headline drills to its evidence. The model is not the
product; the *decision* is.

## Brand Personality

Premium, composed, editorial — the quiet confidence of a Pernod Ricard luxury label, not a
SaaS dashboard. Three words: **considered, premium, decisive.** Voice is plain and senior:
short sentences, no jargon theatre, numbers that earn their place. Conviviality read as
*warmth and human focus* — this is about people, not headcount as inventory.

## Anti-references

- **Generic Streamlit demo look** — raw default widgets, gray-on-gray, no identity. The single
  thing to defeat.
- **Playful / startup energy** — bright primaries, emoji confetti, casual copy. Wrong for a
  director audience.
- Power BI corporate-fade (rainbow pies, clinical white, rows of identical KPI cards).
- AI slop: identical card grids, decorative gradients, uppercase tracked eyebrows on every section.

## Design Principles

1. **Decision over dashboard.** Every screen answers a leadership question in its first line;
   charts support the sentence, they are not the point.
2. **Headline drills to evidence.** No claim without a one-click path to the data behind it —
   this is how the analyst survives "how do you know?".
3. **Restraint is the premium signal.** Deep, calm surface; gold/copper used sparingly for the
   things that matter (risk, money). Color is meaning, never decoration.
4. **Honest analytics.** Show regretted *vs* non-regretted, show model limits — the credibility
   comes from not overselling. Verify the good people are the ones leaving before recommending action.
5. **Human, not inventory.** Named people, suggested humane actions; never reduce employees to a churn probability alone.

## Accessibility & Inclusion

Presented over screen-share, so legibility at standard screen sizes is the bar: body text
≥4.5:1 contrast on the dark surface, large headline figures well above 3:1. Diverging risk
scales use amber↔teal (not red/green) to stay color-blind-safe. Full keyboard navigation via
Streamlit defaults; honor `prefers-reduced-motion` in any custom animation.
