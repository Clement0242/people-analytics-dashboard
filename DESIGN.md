# Design

A premium, editorial dark theme for an executive People Analytics dashboard — the composed
confidence of the **Pernod Ricard corporate identity**, not a SaaS tool. Deep French-navy
surface (the brand's own blue, "trust + competence"), summer blue as the interactive accent,
a warm gold/champagne reserved for value (money, priority, the figures leaders read first),
serif for editorial moments, humanist sans for all functional UI and data. The sidebar carries
a stylised "conviviality sun" mark in brand colours.

## Color

Strategy: **Committed-dark, two-accent.** The deep French-navy surface *is* the identity
(grounded in the real brand navy `#002957` / `#123F75`). **Blue** (summer blue `#76A0CD`) is
the *interactive* accent — selection, nav, links, neutral chart series. **Gold** is the *value*
accent — priority, money, signature figures; warm gold on navy makes the numbers pop, which is
the point of the dashboard. Diverging risk uses amber↔teal (colour-blind-safe), never red/green.
OKLCH is the source of truth; hex mirrors are for Streamlit's `config.toml`.

| Token | OKLCH | Hex | Role |
|---|---|---|---|
| `--bg` | `oklch(0.20 0.045 258)` | `#0C1A2D` | App background (deep French-navy black) |
| `--surface` | `oklch(0.25 0.05 258)` | `#122339` | Panels, cards, sidebar |
| `--surface-2` | `oklch(0.31 0.055 258)` | `#1B3149` | Elevated / hover / selected rows |
| `--border` | `oklch(0.38 0.045 258)` | `#2A405C` | Hairline dividers |
| `--border-strong` | `oklch(0.49 0.05 256)` | `#43597A` | Emphasised borders, focus ring base |
| `--ink` | `oklch(0.96 0.006 240)` | `#EEF3F8` | Primary text (cool off-white) |
| `--ink-muted` | `oklch(0.78 0.02 250)` | `#A8B6C8` | Secondary text, labels (8.5:1 on bg) |
| `--ink-faint` | `oklch(0.62 0.025 250)` | `#7888A0` | Tertiary — large text / non-essential only (4.9:1) |
| `--blue` | `oklch(0.72 0.10 250)` | `#76A6D6` | Interactive accent: selection, nav, links, neutral series |
| `--blue-strong` | `oklch(0.81 0.09 248)` | `#9CC4E8` | Hover / emphasis interactive |
| `--gold` | `oklch(0.80 0.12 84)` | `#E0B45E` | Value accent: priority, money, current value |
| `--gold-strong` | `oklch(0.86 0.13 86)` | `#F0CC74` | Hover / signature figure |
| `--copper` | `oklch(0.66 0.13 52)` | `#C9824C` | Secondary warm accent (sparingly) |
| `--risk-high` | `oklch(0.72 0.15 55)` | `#E48A48` | High attrition / underpaid (amber) |
| `--risk-mid` | `oklch(0.80 0.09 82)` | `#DBBE7E` | Mid risk |
| `--safe` | `oklch(0.74 0.10 190)` | `#4FB8AE` | Healthy / retained / fairly paid (teal) |

Semantic states (product vocabulary): hover = `--surface-2`; focus ring / selected nav = 2px
inset `--blue` *as a background tint, never a side-stripe border*; signature figures = `--gold`;
disabled = `--ink-faint`. Accent never appears on inactive states. All body/label colours verified
≥4.5:1 on their background.

## Typography

Pairing on the serif↔sans contrast axis. **Serif is editorial-only.**

- **Display — Fraunces** (variable, optical size): page H1 titles, section headers, and the *one*
  signature figure per page. Never on labels, buttons, table data, or axes.
- **UI & data — Hanken Grotesk** (humanist sans): everything functional — body, labels, buttons,
  table cells, KPI values, chart text. Use `font-variant-numeric: tabular-nums` for all figures.

Fixed rem scale (product, ratio ~1.2), not fluid:

| Step | Size / weight | Font | Use |
|---|---|---|---|
| display-l | 2.5rem / 340 | Fraunces | Page title |
| display-m | 1.75rem / 380 | Fraunces | Signature figure |
| heading | 1.125rem / 600 | Hanken | Section / card header |
| body | 0.95rem / 400 | Hanken | Default text |
| label | 0.8rem / 600, +0.01em | Hanken | Field labels, table headers |
| micro | 0.72rem / 500 | Hanken | Captions, footnotes |

`text-wrap: balance` on display headings. No uppercase tracked eyebrows.

## Layout & Spacing

4px base scale: `4 · 8 · 12 · 16 · 24 · 32 · 48 · 64`. Vary spacing for rhythm; section gap 32,
intra-card gap 12–16. Radius: 8px panels, 6px controls, 4px chips (never pill). Content max ~1200px
centered. Dark UI elevation = border + a soft low shadow `0 1px 2px rgb(0 0 0 / .4)`, not glow.
Sidebar nav (Streamlit native) reskinned as the second neutral layer (`--surface`).

KPIs live in a flex row that wraps (`flex-wrap`), not an identical card grid — each metric sized
to its content and importance, the signature figure largest. Avoid the hero-metric template.

## Components

- **Sidebar brand:** a neutral mark, the 9-box grid itself (gold top-right cell = Accelerate).
  No company logo: the app is a public, independent case study.
- **Sidebar nav:** Material-symbol icon per page; muted by default, hover = `--surface-2`,
  active = blue-tinted fill + 3px inset blue accent + blue-strong label. A small "Navigate" label
  sets the section.

Streamlit-native components reskinned, not reinvented (product register: earned familiarity).
- **Metric tiles**: label (micro, muted) over value (Hanken tabular, large) over delta (teal/amber).
- **Data tables** (`st.dataframe`): dark surface, hairline rows, gold for the priority column,
  amber/teal chips for risk band. Tabular figures, right-aligned numbers.
- **Charts** (Plotly): transparent background, `--ink-muted` axes/grid at low opacity, gold/copper/
  teal series only — no rainbow categoricals. Diverging scales amber↔teal.
- **Chips/badges**: talent call (Accelerate/Stretch/Grow), risk band — filled tint + readable ink.
- States required on every interactive element: default, hover, focus, active, disabled.

## Motion

150–250 ms, ease-out (`cubic-bezier(0.22, 1, 0.36, 1)`). State and feedback first: row/tile hover
lift, tab and nav change. One restrained entrance: KPI tiles, title and lead `rise` (fade + 8px
up) on first paint, lightly staggered (≤200 ms total) — enough to feel alive on a screen-share,
not choreography. Plotly figures carry a 350 ms transition so interactive controls (the pay
what-if slider, the lifecycle cohort toggle, the headcount window) animate their charts rather
than snapping. `@media (prefers-reduced-motion: reduce)`: all animation/transition disabled.

## Interactivity

The dashboard is driven, not static — each page has a leader-facing control:
- **Executive Overview** — headcount window toggle (12 / 24 / 36 months).
- **Tenure & Lifecycle** — cohort focus radio that highlights a tenure band in the cliff chart
  and re-scopes the watch-list roster.
- **Retention Priority** — department / talent / band filters + searchable, selectable table that
  opens a full retention profile.
- **Pay Equity** — *what-if* slider: set a target compa-ratio and the remediation cost, KPIs and
  action list reprice live.
- **Succession** — incumbent selector driving the k-NN successor search.

## Implementation notes (Streamlit)

- `.streamlit/config.toml` `[theme]` carries the hex mirrors (base=dark) so native widgets are
  on-theme even before CSS loads.
- A single injected `<style>` block imports Fraunces + Hanken Grotesk from Google Fonts and defines
  the tokens as CSS variables on `:root`, then overrides Streamlit's classes. oklch() used directly
  in CSS (modern browser); hex only where config.toml requires it.
- Plotly figures get a shared `template` built from these tokens so every chart matches.
