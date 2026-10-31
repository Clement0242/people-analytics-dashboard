"""Design system for the dashboard — premium corporate dark theme.

Premium executive dark theme anchored on the real Pernod Ricard identity:
French navy + summer blue (trust, competence, the merger of two houses) with a
warm gold/champagne accent for the things that carry value — money, priority,
the figures leaders read first. Blue is the interactive accent (selection, nav,
neutral series); gold is the value accent (priority, money, signature numbers);
amber<->teal is the colour-blind-safe risk diverging scale.

Holds the colour tokens, the injected CSS (fonts, tokens, Streamlit overrides,
custom component classes, motion), a shared Plotly template, and small HTML
helpers so every page speaks the same visual language.
"""
from __future__ import annotations

import base64
import math
from functools import lru_cache
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

ASSETS = Path(__file__).resolve().parent / "assets"


@lru_cache(maxsize=4)
def _data_uri(name: str) -> str:
    """Base64 data URI for an asset, so it embeds in injected HTML."""
    data = (ASSETS / name).read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode()

# --- Colour tokens (hex mirrors of the OKLCH source in DESIGN.md) ----------
# Navy ramp (the corporate identity surface)
BG = "#0C1A2D"            # deep French-navy black — app background
SURFACE = "#122339"        # panels, cards, sidebar
SURFACE2 = "#1B3149"       # elevated / hover / selected rows
BORDER = "#2A405C"         # hairline dividers
BORDER_STRONG = "#43597A"  # emphasised borders, focus ring base
# Ink ramp (cool off-white)
INK = "#EEF3F8"            # primary text
INK_MUTED = "#A8B6C8"      # secondary text, labels (8.5:1 on bg)
INK_FAINT = "#7888A0"      # tertiary — large / non-essential only (4.9:1)
# Accents
BLUE = "#76A6D6"           # summer blue — primary interactive accent
BLUE_STRONG = "#9CC4E8"    # hover / emphasis interactive
GOLD = "#E0B45E"           # value accent: priority, money, current value
GOLD_STRONG = "#F0CC74"    # signature figure / hover
COPPER = "#C9824C"         # secondary warm accent (sparingly)
# Risk diverging (colour-blind safe: amber <-> teal, never red/green)
RISK_HIGH = "#E48A48"      # high attrition / underpaid (amber)
RISK_MID = "#DBBE7E"       # mid risk
SAFE = "#4FB8AE"           # healthy / retained / fairly paid (teal)

# Chart series order: gold (value) -> blue (neutral) -> teal -> copper -> muted
SERIES = [GOLD, BLUE, SAFE, COPPER, INK_MUTED]
TALENT_COLOR = {"Accelerate": GOLD_STRONG, "Stretch": SAFE, "Grow in role": INK_MUTED}

# Neutral mark: the 9-box grid, the talent map the dashboard is built around.
def _sun_svg() -> str:
    cells = []
    for r in range(3):
        for c in range(3):
            fill = GOLD if (r, c) == (0, 2) else (BLUE if r + (2 - c) <= 1 else SURFACE2)
            cells.append(f'<rect x="{4 + c * 14}" y="{4 + r * 14}" width="12" height="12" '
                         f'rx="2.5" fill="{fill}" />')
    return ('<svg width="44" height="44" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" '
            f'aria-hidden="true">{"".join(cells)}</svg>')


_SUN = _sun_svg()

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,340;9..144,380;9..144,600&family=Hanken+Grotesk:wght@400;500;600;700&display=swap');

:root {{
  --bg:{BG}; --surface:{SURFACE}; --surface-2:{SURFACE2};
  --border:{BORDER}; --border-strong:{BORDER_STRONG};
  --ink:{INK}; --ink-muted:{INK_MUTED}; --ink-faint:{INK_FAINT};
  --blue:{BLUE}; --blue-strong:{BLUE_STRONG};
  --gold:{GOLD}; --gold-strong:{GOLD_STRONG}; --copper:{COPPER};
  --risk-high:{RISK_HIGH}; --risk-mid:{RISK_MID}; --safe:{SAFE};
  --serif:'Fraunces',Georgia,serif;
  --sans:'Hanken Grotesk','Segoe UI',system-ui,sans-serif;
  --ease:cubic-bezier(0.22,1,0.36,1);
  --shadow:0 1px 2px rgb(0 0 0 / .45);
  --shadow-lg:0 10px 30px -12px rgb(0 0 0 / .6);
}}

html, body, .stApp, [class*="css"] {{ font-family:var(--sans); }}
.stApp {{ background:
   radial-gradient(1100px 620px at 78% -8%, rgba(118,166,214,.10), transparent 60%),
   radial-gradient(900px 560px at -6% 4%, rgba(224,180,94,.055), transparent 55%),
   var(--bg);
  color:var(--ink); }}
.block-container {{ padding-top:2.2rem; padding-bottom:3rem; max-width:1280px; }}

/* Strip Streamlit chrome for a clean executive canvas */
[data-testid="stHeader"] {{ background:transparent; }}
#MainMenu, footer, [data-testid="stStatusWidget"],
[data-testid="stToolbar"], [data-testid="stAppDeployButton"],
[data-testid="stDecoration"] {{ display:none !important; }}

/* Sidebar = second neutral layer; kept always-open (exec dashboard over screen-share) */
[data-testid="stSidebar"] {{ background:var(--surface); border-right:1px solid var(--border); }}
[data-testid="stSidebar"][aria-expanded="false"] {{ display:none; }}
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {{ display:none !important; }}
[data-testid="stSidebar"] .block-container {{ padding-top:1.4rem; }}
[data-testid="stSidebarNav"] {{ margin-top:2px; }}
[data-testid="stSidebarNav"] ul {{ gap:3px; padding-top:2px; }}
[data-testid="stSidebarNav"] a {{ border-radius:9px; padding:9px 12px; gap:12px;
  color:var(--ink-muted) !important;
  transition:background .18s var(--ease), color .18s var(--ease), box-shadow .18s var(--ease); }}
[data-testid="stSidebarNav"] a span {{ font-weight:500; color:inherit !important; }}
[data-testid="stSidebarNav"] a [data-testid="stIconMaterial"] {{ color:inherit !important;
  font-size:20px; opacity:.92; }}
[data-testid="stSidebarNav"] a:hover {{ background:var(--surface-2); color:var(--ink) !important; }}
[data-testid="stSidebarNav"] a[aria-current="page"] {{
  background:linear-gradient(90deg, rgba(118,166,214,.18), rgba(118,166,214,.06));
  color:var(--blue-strong) !important; box-shadow:inset 3px 0 0 var(--blue); }}
[data-testid="stSidebarNav"] a[aria-current="page"] span {{ font-weight:600; }}
[data-testid="stSidebarNav"] a[aria-current="page"] [data-testid="stIconMaterial"] {{ opacity:1; }}
/* small nav section label */
.nav-label {{ font-size:.66rem; font-weight:700; letter-spacing:.13em; text-transform:uppercase;
  color:var(--ink-faint); padding:2px 6px 6px; }}

/* Brand mark */
.brand {{ padding:2px 0 16px; border-bottom:1px solid var(--border); margin-bottom:12px; }}
.brand .plate {{ background:#fff; border-radius:11px; padding:15px 17px;
  box-shadow:0 4px 16px -4px rgb(0 0 0 / .45); }}
.brand .plate img {{ width:100%; height:auto; display:block; }}
.brand .sub {{ font-size:.68rem; font-weight:600; color:var(--blue); letter-spacing:.14em;
  text-transform:uppercase; text-align:center; margin-top:11px; }}

/* Editorial headers */
.display-title {{ font-family:var(--serif); font-weight:340; font-size:2.45rem; line-height:1.07;
  color:var(--ink); text-wrap:balance; margin:.1rem 0 .35rem;
  animation:rise .5s var(--ease) both; }}
.lead {{ font-size:1.02rem; line-height:1.55; color:var(--ink-muted); max-width:74ch; margin:0 0 1.4rem;
  animation:rise .5s var(--ease) .04s both; }}
.lead b {{ color:var(--gold); font-weight:600; }}
.lead .teal {{ color:var(--safe); font-weight:600; }}
.lead .blue {{ color:var(--blue-strong); font-weight:600; }}

/* KPI tiles — flex-wrap row, sized to importance (not an identical grid) */
.kpi-row {{ display:flex; flex-wrap:wrap; gap:14px; margin:.2rem 0 1.6rem; }}
.kpi {{ position:relative; overflow:hidden; background:
   linear-gradient(180deg, rgba(255,255,255,.022), transparent 70%), var(--surface);
  border:1px solid var(--border); border-radius:12px;
  padding:15px 19px; flex:1 1 168px; box-shadow:var(--shadow);
  transition:border-color .2s var(--ease), transform .2s var(--ease);
  animation:rise .5s var(--ease) both; }}
.kpi:nth-child(2){{animation-delay:.05s}} .kpi:nth-child(3){{animation-delay:.10s}}
.kpi:nth-child(4){{animation-delay:.15s}} .kpi:nth-child(5){{animation-delay:.20s}}
.kpi:hover {{ border-color:var(--border-strong); transform:translateY(-2px); }}
.kpi.signature {{ flex:1.5 1 232px; border-color:rgba(224,180,94,.32);
  background:linear-gradient(180deg, rgba(224,180,94,.07), transparent 72%), var(--surface); }}
.kpi.signature::after {{ content:''; position:absolute; inset:0 0 auto 0; height:2px;
  background:linear-gradient(90deg, var(--gold), transparent); }}
.kpi .label {{ font-size:.71rem; font-weight:600; letter-spacing:.05em; text-transform:uppercase;
  color:var(--ink-muted); }}
.kpi .value {{ font-size:2rem; font-weight:700; font-variant-numeric:tabular-nums;
  color:var(--ink); line-height:1.15; margin-top:5px; }}
.kpi.signature .value {{ font-family:var(--serif); font-weight:380; font-size:2.7rem; color:var(--gold-strong); }}
.kpi .delta {{ font-size:.8rem; margin-top:3px; font-variant-numeric:tabular-nums; }}
.kpi .delta.down {{ color:var(--risk-high); }}
.kpi .delta.up {{ color:var(--safe); }}
.kpi .delta.flat {{ color:var(--ink-faint); }}

/* Panels */
.panel-h {{ font-size:1.06rem; font-weight:600; color:var(--ink); margin:1.2rem 0 .15rem; }}
.panel-sub {{ font-size:.83rem; color:var(--ink-muted); margin:0 0 .7rem; max-width:78ch; line-height:1.5; }}

/* Insight callout — a single framed takeaway sentence */
.insight {{ display:flex; gap:13px; align-items:flex-start;
  background:linear-gradient(180deg, rgba(118,166,214,.08), transparent), var(--surface);
  border:1px solid var(--border); border-radius:11px; padding:14px 17px; margin:.3rem 0 1.2rem; }}
.insight .ic {{ flex:none; width:30px; height:30px; border-radius:8px; display:grid; place-items:center;
  background:rgba(224,180,94,.14); color:var(--gold-strong); font-size:1rem; }}
.insight .tx {{ font-size:.95rem; line-height:1.5; color:var(--ink); }}
.insight .tx b {{ color:var(--gold); }}

/* Empty state — friendly placeholder when a filter returns nothing */
.empty {{ display:flex; gap:13px; align-items:center; justify-content:center; flex-direction:column;
  text-align:center; background:var(--surface); border:1px dashed var(--border-strong);
  border-radius:12px; padding:34px 24px; margin:.4rem 0 1rem; }}
.empty .ic {{ width:42px; height:42px; border-radius:11px; display:grid; place-items:center;
  background:var(--surface-2); color:var(--blue-strong); font-size:1.3rem; }}
.empty .tx {{ font-size:.92rem; line-height:1.5; color:var(--ink-muted); max-width:46ch; }}

/* Legend & glossary (sidebar) — keys the colour + term semantics */
.legend {{ font-size:.78rem; color:var(--ink-muted); line-height:1.55; }}
.legend .row {{ display:flex; align-items:center; gap:8px; margin:5px 0; }}
.legend .sw {{ flex:none; width:11px; height:11px; border-radius:3px; }}
.legend .term {{ margin-top:9px; }}
.legend .term b {{ color:var(--ink); font-weight:600; }}

/* Chips */
.chip {{ display:inline-block; padding:2px 10px; border-radius:6px; font-size:.73rem;
  font-weight:600; line-height:1.5; }}
.chip.accelerate {{ background:rgba(240,204,116,.16); color:var(--gold-strong); border:1px solid rgba(240,204,116,.38); }}
.chip.stretch {{ background:rgba(79,184,174,.13); color:var(--safe); border:1px solid rgba(79,184,174,.32); }}
.chip.grow {{ background:rgba(168,182,200,.10); color:var(--ink-muted); border:1px solid var(--border); }}
.chip.high {{ background:rgba(228,138,72,.18); color:var(--risk-high); border:1px solid rgba(228,138,72,.34); }}
.chip.medium {{ background:rgba(219,190,126,.14); color:var(--risk-mid); border:1px solid rgba(219,190,126,.30); }}
.chip.low {{ background:rgba(168,182,200,.09); color:var(--ink-muted); border:1px solid var(--border); }}
.chip.blue {{ background:rgba(118,166,214,.15); color:var(--blue-strong); border:1px solid rgba(118,166,214,.34); }}
.driver {{ display:inline-block; padding:3px 11px; margin:3px 6px 3px 0; border-radius:6px;
  font-size:.78rem; background:var(--surface-2); border:1px solid var(--border);
  color:var(--ink); }}
.driver::before {{ content:''; display:inline-block; width:6px; height:6px; border-radius:50%;
  background:var(--risk-high); margin-right:7px; vertical-align:middle; }}
.driver.match::before {{ background:var(--safe); }}
.driver.gap::before {{ background:var(--risk-mid); }}

/* Successor cards */
.succ-card {{ display:flex; gap:16px; align-items:stretch; background:var(--surface);
  border:1px solid var(--border); border-radius:11px; padding:15px 18px; margin-bottom:12px;
  transition:border-color .2s var(--ease), transform .2s var(--ease); }}
.succ-card:hover {{ border-color:var(--border-strong); transform:translateY(-2px); }}
.succ-rank {{ font-family:var(--serif); font-size:1.5rem; color:var(--blue); font-weight:380;
  min-width:26px; text-align:center; padding-top:2px; }}
.succ-body {{ flex:1; min-width:0; }}
.succ-top {{ display:flex; align-items:center; gap:9px; flex-wrap:wrap; }}
.succ-name {{ font-size:1.06rem; font-weight:600; color:var(--ink); }}
.succ-meta {{ font-size:.8rem; color:var(--ink-muted); margin:3px 0 8px; }}
.succ-section {{ font-size:.7rem; text-transform:uppercase; letter-spacing:.05em;
  color:var(--ink-faint); margin:9px 0 3px; }}
.succ-score {{ text-align:center; padding-left:16px; border-left:1px solid var(--border);
  display:flex; flex-direction:column; justify-content:center; min-width:78px; }}
.succ-score .n {{ font-family:var(--serif); font-size:2rem; font-weight:380; color:var(--gold-strong);
  line-height:1; }}
.succ-score .l {{ font-size:.72rem; color:var(--ink-muted); margin-top:4px; }}
.succ-callout {{ margin-top:13px; padding:11px 14px; border-radius:8px;
  background:rgba(79,184,174,.10); border:1px solid rgba(79,184,174,.28); }}
.succ-callout .k {{ font-size:.7rem; text-transform:uppercase; letter-spacing:.05em; color:var(--ink-muted); }}
.succ-callout .v {{ font-size:1.05rem; font-weight:600; color:var(--safe); margin-top:1px; }}

/* Profile card */
.profile {{ background:var(--surface); border:1px solid var(--border-strong); border-radius:12px;
  padding:20px 22px; box-shadow:var(--shadow-lg); animation:rise .4s var(--ease) both; }}
.profile .name {{ font-family:var(--serif); font-weight:600; font-size:1.5rem; color:var(--ink); }}
.profile .meta {{ font-size:.85rem; color:var(--ink-muted); margin:2px 0 12px; }}
.profile .action {{ margin-top:12px; padding:11px 14px; border-radius:8px;
  background:rgba(224,180,94,.10); border:1px solid rgba(224,180,94,.30); }}
.profile .action .k {{ font-size:.7rem; text-transform:uppercase; letter-spacing:.05em; color:var(--ink-muted); }}
.profile .action .v {{ font-size:1rem; font-weight:600; color:var(--gold-strong); margin-top:1px; }}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{ gap:4px; border-bottom:1px solid var(--border); }}
.stTabs [data-baseweb="tab"] {{ font-weight:500; color:var(--ink-muted); }}
.stTabs [aria-selected="true"] {{ color:var(--blue-strong) !important; }}
.stTabs [data-baseweb="tab-highlight"] {{ background:var(--blue) !important; }}

/* Inputs */
[data-testid="stWidgetLabel"] p {{ font-size:.78rem; font-weight:600; color:var(--ink-muted);
  letter-spacing:.01em; }}
[data-baseweb="tag"] {{ background:rgba(118,166,214,.18) !important; border:1px solid rgba(118,166,214,.35) !important; }}
[data-baseweb="tag"] span {{ color:var(--blue-strong) !important; }}
[data-baseweb="tag"] svg {{ fill:var(--blue-strong) !important; }}
.stButton button {{ border:1px solid var(--border-strong); border-radius:8px;
  transition:border-color .18s var(--ease), background .18s var(--ease); }}
.stButton button:hover {{ border-color:var(--blue); background:var(--surface-2); }}
/* Sliders + selection accents -> interactive blue */
[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {{ background:var(--blue) !important; }}
[data-baseweb="slider"] [data-testid="stTickBar"] {{ display:none; }}
.stRadio [role="radiogroup"] label[data-baseweb="radio"] div:first-child {{ border-color:var(--border-strong); }}

/* Dataframe header */
[data-testid="stDataFrame"] thead tr th {{ background:var(--surface-2) !important; color:var(--ink) !important; }}

hr {{ border-color:var(--border); }}

/* Visible keyboard focus everywhere (a11y) */
a:focus-visible, button:focus-visible, [role="group"]:focus-visible,
[tabindex]:focus-visible, [data-baseweb] :focus-visible {{
  outline:2px solid var(--blue) !important; outline-offset:2px; border-radius:6px; }}

@keyframes rise {{ from {{ opacity:0; transform:translateY(8px); }}
  to {{ opacity:1; transform:translateY(0); }} }}

@media (prefers-reduced-motion: reduce) {{
  * {{ transition:none !important; animation:none !important; }}
}}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def brand() -> None:
    # No company logo: this is an independent case study, published publicly.
    logo = f'<div style="text-align:center">{_SUN}</div>'
    st.markdown(
        f'<div class="brand">{logo}'
        '<div class="sub">People Analytics · case study</div></div>'
        '<div class="nav-label">Navigate</div>',
        unsafe_allow_html=True,
    )


def title(text: str, lead_html: str) -> None:
    st.markdown(f'<h1 class="display-title">{text}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="lead">{lead_html}</p>', unsafe_allow_html=True)


def insight(html: str, icon: str = "◆") -> None:
    """One framed takeaway sentence — the decision the chart supports."""
    st.markdown(
        f'<div class="insight" role="note"><div class="ic" aria-hidden="true">{icon}</div>'
        f'<div class="tx">{html}</div></div>',
        unsafe_allow_html=True,
    )


def panel_header(title_: str, sub: str | None = None) -> None:
    st.markdown(f'<h2 class="panel-h">{title_}</h2>', unsafe_allow_html=True)
    if sub:
        st.markdown(f'<div class="panel-sub">{sub}</div>', unsafe_allow_html=True)


def _kpi(label: str, value: str, delta: str | None, direction: str, signature: bool) -> str:
    cls = "kpi signature" if signature else "kpi"
    d = f'<div class="delta {direction}">{delta}</div>' if delta else ""
    aria = f"{label}: {value}" + (f", {delta}" if delta else "")
    return (f'<div class="{cls}" role="group" tabindex="0" aria-label="{aria}">'
            f'<div class="label">{label}</div><div class="value">{value}</div>{d}</div>')


def kpi_row(items: list[dict]) -> None:
    """items: {label, value, delta?, direction?('up'|'down'|'flat'), signature?}"""
    html = "".join(_kpi(i["label"], i["value"], i.get("delta"),
                        i.get("direction", "flat"), i.get("signature", False)) for i in items)
    st.markdown(f'<div class="kpi-row">{html}</div>', unsafe_allow_html=True)


def talent_chip(call: str) -> str:
    cls = {"Accelerate": "accelerate", "Stretch": "stretch", "Grow in role": "grow"}[call]
    return f'<span class="chip {cls}">{call}</span>'


def band_chip(band: str) -> str:
    return f'<span class="chip {band.lower()}">{band}</span>'


def legend() -> None:
    """Persistent colour + term key so the screen-share viewer never has to recall
    what gold/blue/amber mean or what the jargon stands for."""
    swatches = [
        (GOLD, "Gold — value: priority, money, key figures"),
        (BLUE, "Blue — interactive: selection, navigation"),
        (RISK_HIGH, "Amber — risk: high attrition / underpaid"),
        (SAFE, "Teal — healthy: retained / fairly paid"),
    ]
    rows = "".join(
        f'<div class="row"><span class="sw" style="background:{c}"></span>{t}</div>'
        for c, t in swatches)
    terms = (
        '<div class="term"><b>Regretted attrition</b> — a strong employee leaving '
        '(Accelerate / Stretch).</div>'
        '<div class="term"><b>Compa-ratio</b> — pay ÷ market benchmark; under 0.90 = underpaid.</div>'
        '<div class="term"><b>9-box / talent call</b> — performance × potential → '
        'Accelerate / Stretch / Grow in role.</div>'
        '<div class="term"><b>Priority score</b> — P(leave) × talent value × pay risk.</div>')
    with st.expander("Legend & glossary"):
        st.markdown(f'<div class="legend">{rows}{terms}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="legend" style="margin-top:12px;opacity:.85">Independent case study by '
        '<a href="https://clement0242.github.io" target="_blank">Clément Verdier</a> on a public '
        'HR dataset (14,999 employees) with seeded synthetic talent, pay and survey layers. '
        'Names are generated. Not affiliated with or endorsed by any employer.</div>',
        unsafe_allow_html=True)


# --- Plotly -----------------------------------------------------------------
def style(fig: go.Figure, height: int = 320, legend: bool = False) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Hanken Grotesk, sans-serif", color=INK_MUTED, size=13),
        colorway=SERIES,
        margin=dict(l=12, r=12, t=34 if legend else 14, b=12),
        height=height,
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.04, x=0, font=dict(size=12)),
        hoverlabel=dict(bgcolor=SURFACE2, bordercolor=BORDER_STRONG,
                        font=dict(family="Hanken Grotesk", color=INK)),
        transition=dict(duration=350, easing="cubic-in-out"),
    )
    fig.update_xaxes(gridcolor="rgba(168,182,200,.10)", zeroline=False,
                     linecolor=BORDER, tickfont=dict(color=INK_MUTED))
    fig.update_yaxes(gridcolor="rgba(168,182,200,.10)", zeroline=False,
                     linecolor=BORDER, tickfont=dict(color=INK_MUTED))
    return fig
