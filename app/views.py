"""Page implementations for the People Analytics dashboard.

Each top-level function is one page; data loading, the Plotly helper, and the
shared constants live here too. `streamlit_app.py` wires these into navigation.
Kept import-safe (no set_page_config / CSS here) so pages can be unit-run via AppTest.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import succession
import theme as T

ROOT = Path(__file__).resolve().parents[1]
SURVEY_DIMS = [
    "Leadership & Manager", "Career & Growth", "Reward & Recognition",
    "Workload & Wellbeing", "Belonging & Conviviality", "Enablement & Tools",
]
REGRETTED = {"Accelerate", "Stretch"}
UNDERPAID = 0.90

# Human labels for the model's feature names (mirrors features.FEATURE_LABELS).
LABELS = {
    "engagement_index": "Low engagement", "performance_raw": "Performance",
    "projects": "Project load", "avg_monthly_hours": "Monthly hours",
    "tenure_years": "Tenure", "work_accident": "Work accident history",
    "promoted_last_5y": "No recent promotion", "potential": "Potential",
    "compa_ratio": "Pay vs market", "survey_score": "Survey sentiment",
    "department": "Department", "salary_band": "Salary band",
}


# --- Data ------------------------------------------------------------------
@st.cache_data
def load() -> pd.DataFrame:
    df = pd.read_csv(ROOT / "outputs" / "scored.csv")
    df["hire_date"] = pd.to_datetime(df["hire_date"])
    df["termination_date"] = pd.to_datetime(df["termination_date"])
    df["regretted"] = df["regretted"].astype(str).str.lower().eq("true")
    return df


@st.cache_data
def load_metrics() -> dict:
    import json
    return json.loads((ROOT / "outputs" / "metrics.json").read_text())


@st.cache_data
def headcount_series(months: int = 24) -> pd.DataFrame:
    df = load()
    end = pd.Timestamp(2026, 6, 30)
    periods = pd.date_range(end - pd.DateOffset(months=months - 1), end, freq="MS")
    rows = []
    for m in periods:
        me = m + pd.offsets.MonthEnd(0)
        hires = int(((df["hire_date"] >= m) & (df["hire_date"] <= me)).sum())
        deps = int(((df["termination_date"] >= m) & (df["termination_date"] <= me)).sum())
        active = int(((df["hire_date"] <= me) &
                      (df["termination_date"].isna() | (df["termination_date"] > me))).sum())
        rows.append((m, hires, deps, active))
    return pd.DataFrame(rows, columns=["month", "hires", "departures", "headcount"])


try:
    df = load()
    M = load_metrics()
except FileNotFoundError:
    st.error(
        "**Data not found.** The dashboard reads `outputs/scored.csv` and "
        "`outputs/metrics.json`, which aren't there yet. Build them once with the "
        "pipeline, then refresh:",
        icon="⚠️")
    st.code("python src/build_dataset.py\npython src/model.py", language="bash")
    st.stop()

active = df[df["status"] == "Active"].copy()


def empty_state(msg: str) -> None:
    """Friendly placeholder when a filter / cohort returns no rows."""
    st.markdown(
        f'<div class="empty"><div class="ic">⌕</div><div class="tx">{msg}</div></div>',
        unsafe_allow_html=True)


def chart(fig, **kw):
    st.plotly_chart(T.style(fig, **kw), width="stretch",
                    config={"displayModeBar": False})


# ===========================================================================
# Page 1 — Executive Overview
# ===========================================================================
def overview() -> None:
    leavers = df[df["attrition"] == 1]
    regret_share = (df["regretted"].sum() / max(len(leavers), 1))
    hi = active[active["priority_band"] == "High"]
    hi_key = int(hi["talent_call"].isin(REGRETTED).sum())

    T.title(
        "Workforce health, at a glance",
        f"<b>{len(active):,}</b> active employees. Annual attrition runs at "
        f"<b>{df['attrition'].mean():.0%}</b> — and <b>{regret_share:.0%}</b> of leavers are "
        f"key talent (<span class='teal'>regretted attrition</span>). "
        f"<b>{len(hi)}</b> people are flagged high-priority for retention right now, "
        f"{hi_key} of them on the Accelerate / Stretch track.",
    )

    T.kpi_row([
        {"label": "Active headcount", "value": f"{len(active):,}", "signature": True},
        {"label": "Annual attrition", "value": f"{df['attrition'].mean():.0%}",
         "delta": "vs 18% market", "direction": "down"},
        {"label": "Regretted (of leavers)", "value": f"{regret_share:.0%}",
         "delta": f"{int(df['regretted'].sum())} key people lost", "direction": "down"},
        {"label": "High-priority risks", "value": f"{len(hi)}",
         "delta": f"{hi_key} key talent", "direction": "down"},
        {"label": "Median compa-ratio", "value": f"{active['compa_ratio'].median():.2f}",
         "delta": "1.00 = market", "direction": "flat"},
    ])

    c1, c2 = st.columns([1.45, 1])
    with c1:
        T.panel_header("Headcount evolution",
                       "Active headcount, hires and departures — pick the window.")
        window = st.radio("Window", [12, 24, 36], index=1, horizontal=True,
                          format_func=lambda m: f"{m} months", label_visibility="collapsed")
        h = headcount_series(window)
        fig = go.Figure()
        fig.add_bar(x=h["month"], y=h["hires"], name="Hires", marker_color=T.SAFE, opacity=.85)
        fig.add_bar(x=h["month"], y=-h["departures"], name="Departures",
                    marker_color=T.RISK_HIGH, opacity=.85)
        fig.add_scatter(x=h["month"], y=h["headcount"], name="Headcount", yaxis="y2",
                        mode="lines", line=dict(color=T.BLUE, width=2.5))
        fig.update_layout(barmode="relative",
                          yaxis2=dict(overlaying="y", side="right", showgrid=False,
                                      tickfont=dict(color=T.BLUE)))
        chart(fig, height=300, legend=True)
    with c2:
        T.panel_header("Talent map (9-box)", "Active employees by performance × potential.")
        bands = ["Low", "Mid", "High"]
        cut = lambda s: pd.cut(s, [0, 2, 3, 5], labels=bands)
        grid = (active.assign(pb=cut(active["performance_rating"]),
                              qb=cut(active["potential"]))
                .groupby(["pb", "qb"], observed=True).size().unstack(fill_value=0)
                .reindex(index=bands, columns=bands, fill_value=0))
        fig = go.Figure(go.Heatmap(
            z=grid.values, x=[f"{b} potential" for b in bands],
            y=[f"{b} perf." for b in bands],
            colorscale=[[0, T.SURFACE2], [1, T.GOLD]], showscale=False,
            text=grid.values, texttemplate="%{text}",
            textfont=dict(color=T.INK, size=14)))
        chart(fig, height=340)

    T.panel_header("Where the risk sits",
                   "Annual attrition rate by function — darker bars exceed the company average.")
    by_dept = (df.groupby("department")["attrition"].mean().sort_values())
    avg = df["attrition"].mean()
    colors = [T.RISK_HIGH if v > avg else T.INK_MUTED for v in by_dept.values]
    fig = go.Figure(go.Bar(x=by_dept.values, y=by_dept.index, orientation="h",
                           marker_color=colors,
                           text=[f"{v:.0%}" for v in by_dept.values],
                           textposition="outside", textfont=dict(color=T.INK_MUTED)))
    fig.add_vline(x=avg, line=dict(color=T.GOLD, dash="dot", width=1.5))
    fig.update_xaxes(tickformat=".0%", range=[0, by_dept.max() * 1.18])
    chart(fig, height=300)

    top_dept = by_dept.idxmax()
    T.insight(
        f"<b>{top_dept}</b> runs the highest attrition at <b>{by_dept.max():.0%}</b> — "
        f"well above the {avg:.0%} company average. Start the retention conversation there.")


# ===========================================================================
# Page 2 — Turnover Model
# ===========================================================================
def model_page() -> None:
    leavers = df[df["attrition"] == 1]
    key_mask = df["talent_call"].isin(REGRETTED)
    key_attr = df.loc[key_mask, "attrition"].mean()
    regret_share = df["regretted"].sum() / max(len(leavers), 1)
    # Engagement is the #1 driver — quantify the gap between least and most engaged.
    lo_cut, hi_cut = df["engagement_index"].quantile([0.33, 0.67])
    lo_eng = df.loc[df["engagement_index"] <= lo_cut, "attrition"].mean()
    hi_eng = df.loc[df["engagement_index"] >= hi_cut, "attrition"].mean()
    ratio = lo_eng / hi_eng if hi_eng else 0
    top_driver = LABELS.get(next(iter(M["global_importance"])), "Engagement")

    T.title(
        "Why people leave — and whether it's the right people",
        f"Most departures are driven by <b>{top_driver.lower()}</b>, tenure and workload. But "
        f"volume isn't the point — <b>who</b> is: our Accelerate / Stretch talent leave at "
        f"<b>{key_attr:.0%}</b>, and <b>{regret_share:.0%}</b> of all leavers are key people. "
        f"That <span class='teal'>regretted attrition</span> is exactly what the priority list is "
        f"built to stop.",
    )

    T.kpi_row([
        {"label": "Annual attrition", "value": f"{df['attrition'].mean():.0%}", "signature": True},
        {"label": "Key-talent attrition", "value": f"{key_attr:.0%}",
         "delta": "Accelerate / Stretch", "direction": "down"},
        {"label": "Regretted (of leavers)", "value": f"{regret_share:.0%}",
         "delta": f"{int(df['regretted'].sum())} key people lost", "direction": "down"},
        {"label": "Disengaged attrition", "value": f"{lo_eng:.0%}",
         "delta": f"{ratio:.0f}× the most-engaged", "direction": "down"},
    ])

    T.panel_header("What drives departures",
                   "How much each factor weighs in who leaves — the levers leaders can act on.")
    imp = M["global_importance"]
    items = [(LABELS.get(k, k), v) for k, v in imp.items() if v > 0][:8][::-1]
    total = sum(v for _, v in items) or 1
    fig = go.Figure(go.Bar(x=[v / total for _, v in items], y=[k for k, _ in items],
                           orientation="h", marker_color=T.GOLD,
                           text=[f"{v/total:.0%}" for _, v in items],
                           textposition="outside", textfont=dict(color=T.INK_MUTED, size=11)))
    fig.update_xaxes(title="Relative importance", tickformat=".0%",
                     range=[0, max(v / total for _, v in items) * 1.18])
    chart(fig, height=340)

    T.panel_header("Are we losing the right — or the wrong — people?",
                   "If attrition concentrated in low performers it would be healthy churn. It does "
                   "not: Accelerate and Stretch talent leave at meaningful rates, which is exactly "
                   "what the priority list is built to stop.")
    c3, c4 = st.columns([1, 1])
    with c3:
        order = ["Accelerate", "Stretch", "Grow in role"]
        rate = df.groupby("talent_call")["attrition"].mean().reindex(order)
        fig = go.Figure(go.Bar(x=order, y=rate.values,
                               marker_color=[T.GOLD_STRONG, T.SAFE, T.INK_MUTED],
                               text=[f"{v:.0%}" for v in rate.values],
                               textposition="outside", textfont=dict(color=T.INK)))
        fig.update_yaxes(tickformat=".0%", range=[0, rate.max() * 1.25],
                         title="Attrition rate")
        chart(fig, height=300)
    with c4:
        perf = (df.groupby(["performance_rating", "attrition"]).size()
                .unstack(fill_value=0))
        perf_rate = (perf[1] / (perf[0] + perf[1]))
        fig = go.Figure(go.Bar(x=perf_rate.index, y=perf_rate.values, marker_color=T.COPPER,
                               text=[f"{v:.0%}" for v in perf_rate.values],
                               textposition="outside", textfont=dict(color=T.INK_MUTED)))
        fig.update_xaxes(title="Performance rating (1–5)", dtick=1)
        fig.update_yaxes(tickformat=".0%", range=[0, perf_rate.max() * 1.25],
                         title="Attrition rate")
        chart(fig, height=300)


# ===========================================================================
# Page 3 — Retention Priority List
# ===========================================================================
def profile_card(emp: pd.Series) -> None:
    call = emp["talent_call"]
    st.markdown(
        f'<div class="profile" role="group" tabindex="0" '
        f'aria-label="Retention profile: {emp["name"]}">'
        f'<div class="name">{emp["name"]}</div>'
        f'<div class="meta">{emp["employee_id"]} · {emp["department"]} · '
        f'{emp["tenure_years"]:.0f} yrs tenure · perf {emp["performance_rating"]}/5 · '
        f'potential {emp["potential"]}/5</div>'
        f'{T.talent_chip(call)} &nbsp; {T.band_chip(emp["priority_band"])}'
        '</div>', unsafe_allow_html=True)

    k1, k2, k3 = st.columns(3)
    k1.markdown(T._kpi("Priority score", f'{emp["priority_score"]:.0f}', None, "flat", False),
                unsafe_allow_html=True)
    k2.markdown(T._kpi("P(leave, 12m)", f'{emp["p_attrition"]:.0%}', None, "flat", False),
                unsafe_allow_html=True)
    k3.markdown(T._kpi("Compa-ratio", f'{emp["compa_ratio"]:.2f}',
                       "below market" if emp["compa_ratio"] < UNDERPAID else "fair",
                       "down" if emp["compa_ratio"] < UNDERPAID else "up", False),
                unsafe_allow_html=True)

    st.markdown('<div class="panel-h" style="font-size:.95rem;">Risk drivers</div>',
                unsafe_allow_html=True)
    chips = "".join(f'<span class="driver">{emp[f"driver_{i}"]}</span>'
                    for i in (1, 2, 3) if emp[f"driver_{i}"])
    st.markdown(chips, unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1])
    with c1:
        vals = [emp[f"survey_{d}"] for d in SURVEY_DIMS]
        short = [d.split(" & ")[0] for d in SURVEY_DIMS]
        fig = go.Figure(go.Scatterpolar(
            r=vals + [vals[0]], theta=short + [short[0]], fill="toself",
            fillcolor="rgba(224,180,94,.18)", line=dict(color=T.GOLD)))
        fig.update_layout(polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(range=[0, 5], gridcolor=T.BORDER, tickfont=dict(color=T.INK_FAINT)),
            angularaxis=dict(gridcolor=T.BORDER, tickfont=dict(color=T.INK_MUTED, size=11))))
        st.markdown('<div class="panel-sub" style="margin-top:8px;">Engagement survey (1–5)</div>',
                    unsafe_allow_html=True)
        chart(fig, height=260)
    with c2:
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=emp["compa_ratio"],
            number=dict(font=dict(color=T.INK, size=30)),
            gauge=dict(
                axis=dict(range=[0.6, 1.4], tickcolor=T.INK_MUTED),
                bar=dict(color=T.GOLD),
                steps=[dict(range=[0.6, 0.9], color="rgba(228,138,72,.25)"),
                       dict(range=[0.9, 1.1], color="rgba(79,184,174,.18)"),
                       dict(range=[1.1, 1.4], color="rgba(168,182,200,.10)")],
                threshold=dict(line=dict(color=T.INK, width=2), value=1.0))))
        st.markdown('<div class="panel-sub" style="margin-top:8px;">Pay vs market (1.00 = on market)</div>',
                    unsafe_allow_html=True)
        chart(fig, height=260)

    st.markdown(
        f'<div class="profile action"><div class="k">Suggested action</div>'
        f'<div class="v">{emp["suggested_action"]}</div></div>', unsafe_allow_html=True)


def priority_page() -> None:
    pool = active[active["priority_score"].notna()].copy()
    with st.sidebar:
        st.markdown("###### Filters")
        depts = st.multiselect("Function", sorted(pool["department"].unique()))
        calls = st.multiselect("Talent call", list(T.TALENT_COLOR.keys()))
        bands = st.multiselect("Priority", ["High", "Medium", "Low"], default=["High", "Medium"])
        query = st.text_input("Search name")

    f = pool
    if depts:
        f = f[f["department"].isin(depts)]
    if calls:
        f = f[f["talent_call"].isin(calls)]
    if bands:
        f = f[f["priority_band"].isin(bands)]
    if query:
        f = f[f["name"].str.contains(query, case=False, na=False)]
    f = f.sort_values("priority_score", ascending=False).reset_index(drop=True)

    key_n = int(f["talent_call"].isin(REGRETTED).sum())
    T.title(
        "Who to act on now",
        f"<b>{len(f):,}</b> active employees match your filters, ranked by retention priority — "
        f"probability of leaving × talent value × pay risk. <b>{key_n}</b> are Accelerate / "
        f"Stretch talent. Select a row to see why, and what to do.",
    )

    if f.empty:
        empty_state("No one matches these filters. Widen the talent call, priority band "
                    "or function in the sidebar, or clear the search.")
        return

    disp = f.assign(**{
        "P(leave)": (f["p_attrition"] * 100).round(0),
    })[["name", "department", "talent_call", "priority_score", "P(leave)",
        "compa_ratio", "driver_1", "suggested_action"]]
    event = st.dataframe(
        disp, hide_index=True, width="stretch", height=430,
        on_select="rerun", selection_mode="single-row",
        column_config={
            "name": st.column_config.TextColumn("Employee", width="medium"),
            "department": st.column_config.TextColumn("Function"),
            "talent_call": st.column_config.TextColumn("Talent call"),
            "priority_score": st.column_config.ProgressColumn(
                "Priority", min_value=0, max_value=100, format="%d"),
            "P(leave)": st.column_config.NumberColumn("P(leave)", format="%d%%"),
            "compa_ratio": st.column_config.NumberColumn("Compa", format="%.2f"),
            "driver_1": st.column_config.TextColumn("Top driver"),
            "suggested_action": st.column_config.TextColumn("Suggested action", width="medium"),
        })

    rows = event.selection.rows
    st.markdown("<hr>", unsafe_allow_html=True)
    if rows:
        profile_card(f.iloc[rows[0]])
    else:
        st.markdown('<p class="panel-sub">Select an employee above to open their retention '
                    'profile — drivers, engagement survey, pay position, and the suggested action.</p>',
                    unsafe_allow_html=True)


# ===========================================================================
# Page 4 — Pay Equity
# ===========================================================================
def pay_page() -> None:
    underpaid = active[active["compa_ratio"] < UNDERPAID]
    key_under = underpaid[underpaid["talent_call"].isin(REGRETTED)]

    with st.sidebar:
        st.markdown("###### Pay what-if")
        st.caption("Lift underpaid key talent to this share of market.")
        target = st.slider("Target compa-ratio", 0.90, 1.00, 0.95, 0.01,
                           label_visibility="collapsed")
    # Cost to bring underpaid key talent up to the chosen target of market.
    cost = ((target - key_under["compa_ratio"]) * key_under["market_benchmark"]).clip(lower=0).sum()

    T.title(
        "Are we paying our best people fairly?",
        f"<b>{len(underpaid) / len(active):.0%}</b> of active employees sit below market "
        f"(compa-ratio under 0.90). <b>{len(key_under)}</b> of them are Accelerate / Stretch "
        f"talent — <span class='teal'>underpaid and high-value is a double flight risk</span>. "
        f"Closing their gap to <span class='blue'>{target:.2f}</span> of market costs about "
        f"<b>${cost/1e6:.1f}M</b> a year — move the slider to price any target.",
    )

    T.kpi_row([
        {"label": "Median compa-ratio", "value": f"{active['compa_ratio'].median():.2f}",
         "signature": True},
        {"label": "Below market", "value": f"{len(underpaid) / len(active):.0%}",
         "delta": f"{len(underpaid)} people", "direction": "down"},
        {"label": "Underpaid key talent", "value": f"{len(key_under)}",
         "delta": "double risk", "direction": "down"},
        {"label": f"Cost to reach {target:.2f}", "value": f"${cost/1e6:.1f}M",
         "delta": "key talent / year", "direction": "flat"},
    ])

    c1, c2 = st.columns([1, 1.25])
    with c1:
        T.panel_header("Pay distribution", "Compa-ratio across active employees; amber = below market.")
        fig = go.Figure()
        below = active[active["compa_ratio"] < UNDERPAID]["compa_ratio"]
        above = active[active["compa_ratio"] >= UNDERPAID]["compa_ratio"]
        fig.add_histogram(x=above, marker_color=T.INK_MUTED, opacity=.8, xbins=dict(size=0.02),
                          name="At/above market")
        fig.add_histogram(x=below, marker_color=T.RISK_HIGH, opacity=.85, xbins=dict(size=0.02),
                          name="Below market")
        fig.add_vline(x=1.0, line=dict(color=T.GOLD, dash="dot"))
        fig.update_layout(barmode="overlay")
        fig.update_xaxes(title="Compa-ratio")
        chart(fig, height=340, legend=True)
    with c2:
        T.panel_header("The double-risk quadrant",
                       "Performance vs pay. Top-left = strong performers paid below market — "
                       "act here first.")
        fig = go.Figure()
        for call in ["Grow in role", "Stretch", "Accelerate"]:
            s = active[active["talent_call"] == call]
            fig.add_scatter(
                x=s["compa_ratio"],
                y=s["performance_rating"] + (s.index % 7 - 3) / 14,  # vertical jitter
                mode="markers", name=call,
                marker=dict(color=T.TALENT_COLOR[call], size=5, opacity=.55))
        fig.add_vrect(x0=active["compa_ratio"].min(), x1=UNDERPAID,
                      fillcolor="rgba(228,138,72,.10)", line_width=0)
        fig.add_vline(x=UNDERPAID, line=dict(color=T.RISK_HIGH, dash="dot"))
        fig.update_xaxes(title="Compa-ratio (pay vs market)")
        fig.update_yaxes(title="Performance rating", dtick=1)
        chart(fig, height=340, legend=True)

    T.panel_header("Underpaid key talent — the action list",
                   f"Accelerate / Stretch employees below market, with the gap to a fair {target:.2f}.")
    if key_under.empty:
        empty_state("No Accelerate / Stretch talent currently sits below market — pay risk is "
                    "contained for key people.")
        return
    tbl = key_under.assign(
        gap=lambda d: ((target - d["compa_ratio"]) * d["market_benchmark"]).clip(lower=0)
        .round(-2).astype(int)
    ).sort_values("gap", ascending=False)[
        ["name", "department", "talent_call", "performance_rating", "potential",
         "salary", "market_benchmark", "compa_ratio", "gap"]].head(25)
    st.dataframe(
        tbl, hide_index=True, width="stretch", height=360,
        column_config={
            "name": st.column_config.TextColumn("Employee", width="medium"),
            "department": st.column_config.TextColumn("Function"),
            "talent_call": st.column_config.TextColumn("Talent call"),
            "performance_rating": st.column_config.NumberColumn("Perf", format="%d"),
            "potential": st.column_config.NumberColumn("Pot.", format="%d"),
            "salary": st.column_config.NumberColumn("Salary", format="$%d"),
            "market_benchmark": st.column_config.NumberColumn("Market", format="$%d"),
            "compa_ratio": st.column_config.NumberColumn("Compa", format="%.2f"),
            "gap": st.column_config.NumberColumn("Gap to fair", format="$%d"),
        })


# ===========================================================================
# Page — Tenure & Lifecycle
# ===========================================================================
TENURE_BANDS = ["0–3 yrs · Establishing", "4–5 yrs · The cliff", "6+ yrs · Anchored"]


def _tenure_band(s: pd.Series) -> pd.Series:
    return pd.cut(s, [0, 3, 5, 100], labels=TENURE_BANDS)


def tenure_page() -> None:
    leavers = df[df["attrition"] == 1]
    by_year = df.groupby("tenure_years")["attrition"].mean()
    avg = df["attrition"].mean()
    peak_year = int(by_year.idxmax())
    cliff = leavers["tenure_years"].between(4, 5)
    cliff_share = cliff.mean()
    early_rate = df.loc[df["tenure_years"] <= 3, "attrition"].mean()
    regret_tenure = leavers.loc[leavers["regretted"], "tenure_years"].median()

    with st.sidebar:
        st.markdown("###### Lifecycle focus")
        st.caption("Highlight a tenure cohort across the page.")
        focus = st.radio("Cohort", ["All employees", *TENURE_BANDS],
                         label_visibility="collapsed")

    T.title(
        "When in their journey do we lose people?",
        f"Attrition is not flat across a career — it peaks hard at the "
        f"<b>{peak_year}-year</b> mark, then all but disappears. "
        f"<b>{cliff_share:.0%}</b> of every departure happens in the 4–5 year "
        f"<span class='blue'>cliff</span>, and the key talent we regret losing leaves at a "
        f"median of <b>{regret_tenure:.0f} years</b>. Retention effort is a timing problem as "
        f"much as a people problem.",
    )

    T.kpi_row([
        {"label": "Median tenure (active)", "value": f"{active['tenure_years'].median():.0f} yrs",
         "signature": True},
        {"label": "Peak-risk year", "value": f"Year {peak_year}",
         "delta": f"{by_year.max():.0%} leave", "direction": "down"},
        {"label": "Departures from the cliff", "value": f"{cliff_share:.0%}",
         "delta": "of all leavers (yr 4–5)", "direction": "down"},
        {"label": "Early attrition (≤3 yrs)", "value": f"{early_rate:.0%}",
         "delta": "vs company avg", "direction": "flat"},
        {"label": "Regretted leaver tenure", "value": f"{regret_tenure:.0f} yrs",
         "delta": "median at exit", "direction": "flat"},
    ])

    c1, c2 = st.columns([1.5, 1])
    with c1:
        T.panel_header("The mid-tenure cliff",
                       "Attrition rate by exact years of service. The selected cohort is gold; "
                       "amber bars exceed the company average.")
        focus_years = {TENURE_BANDS[0]: range(0, 4), TENURE_BANDS[1]: range(4, 6),
                       TENURE_BANDS[2]: range(6, 999)}.get(focus)
        colors = []
        for yr, v in by_year.items():
            if focus_years and int(yr) in focus_years:
                colors.append(T.GOLD)
            elif v > avg:
                colors.append(T.RISK_HIGH)
            else:
                colors.append(T.INK_MUTED)
        fig = go.Figure(go.Bar(
            x=[f"{int(y)}" for y in by_year.index], y=by_year.values, marker_color=colors,
            text=[f"{v:.0%}" for v in by_year.values], textposition="outside",
            textfont=dict(color=T.INK_MUTED, size=11)))
        fig.add_hline(y=avg, line=dict(color=T.BLUE, dash="dot", width=1.5),
                      annotation_text="company avg", annotation_position="top left",
                      annotation_font=dict(color=T.BLUE, size=11))
        fig.update_xaxes(title="Years of service")
        fig.update_yaxes(tickformat=".0%", range=[0, by_year.max() * 1.2], title="Attrition rate")
        chart(fig, height=340)
    with c2:
        T.panel_header("Are we losing the good ones early?",
                       "Attrition of Accelerate / Stretch talent vs everyone else, by cohort.")
        b = df.assign(band=_tenure_band(df["tenure_years"]),
                      key=df["talent_call"].isin(REGRETTED))
        rate = (b.groupby(["band", "key"], observed=True)["attrition"].mean()
                .unstack(fill_value=0).reindex(TENURE_BANDS))
        fig = go.Figure()
        fig.add_bar(x=TENURE_BANDS, y=rate.get(False, 0), name="Other talent",
                    marker_color=T.INK_MUTED, opacity=.85)
        fig.add_bar(x=TENURE_BANDS, y=rate.get(True, 0), name="Key talent",
                    marker_color=T.GOLD)
        fig.update_layout(barmode="group")
        fig.update_xaxes(tickangle=-12, tickfont=dict(size=10))
        fig.update_yaxes(tickformat=".0%", title="Attrition rate")
        chart(fig, height=340, legend=True)

    key_cliff = df[(df["tenure_years"].between(4, 5)) & df["regretted"]]
    T.insight(
        f"The cliff is not healthy churn: <b>{len(key_cliff)}</b> of the people lost at 4–5 years "
        f"were Accelerate / Stretch talent. Catch them <b>before</b> year 4 — onboarding, growth "
        f"conversations and pay reviews land best in years 2–3.")


# ===========================================================================
# Page 5 — Succession & Replacement
# ===========================================================================
@st.cache_resource
def _successor_index():
    return succession.build_index(active)


READY_CHIP = {"Ready now": "stretch", "Ready in 1–2 years": "medium",
              "Development needed": "low"}


def _successor_card(rank: int, c: pd.Series) -> None:
    ready_cls = READY_CHIP[c["readiness"]]
    why = "".join(f'<span class="driver match">{w}</span>' for w in c["why"])
    gaps = "".join(f'<span class="driver gap">{g}</span>' for g in c["gaps"]) \
        if c["gaps"] else '<span class="panel-sub">No material gaps</span>'
    st.markdown(
        f'<div class="succ-card" role="group" tabindex="0" '
        f'aria-label="Successor {rank}: {c["name"]}, {c["readiness"]}, '
        f'match {c["match"]:.0f} percent">'
        f'<div class="succ-rank" aria-hidden="true">{rank}</div>'
        f'<div class="succ-body">'
        f'<div class="succ-top"><span class="succ-name">{c["name"]}</span>'
        f'{T.talent_chip(c["talent_call"])}'
        f'<span class="chip {ready_cls}">{c["readiness"]}</span></div>'
        f'<div class="succ-meta">{c["department"]} · perf {c["performance_rating"]}/5 · '
        f'potential {c["potential"]}/5 · flight risk {c["flight_risk"]:.0f}%</div>'
        f'<div class="succ-section">Why they fit</div>{why}'
        f'<div class="succ-section">Development gaps</div>{gaps}'
        f'</div>'
        f'<div class="succ-score"><div class="n">{c["successor_score"]:.0f}</div>'
        f'<div class="l">match {c["match"]:.0f}%</div></div>'
        f'</div>', unsafe_allow_html=True)


def succession_page() -> None:
    pool = active[active["priority_score"].notna()].sort_values(
        "priority_score", ascending=False).reset_index(drop=True)

    T.title(
        "If we lose them, who steps in?",
        "Succession planning by <b>profile similarity</b>. Pick a role's incumbent and the model "
        "finds the internal employees whose profile most resembles theirs (k-nearest-neighbours "
        "over performance, potential, workload, tenure and function), then ranks them by "
        "<b>readiness</b> and how <span class='teal'>retainable</span> they are — a great match "
        "who is themselves a flight risk is not a safe successor.",
    )

    labels = [f'{r["name"]} — {r["department"]} · {r["talent_call"]} '
              f'(priority {r["priority_score"]:.0f})' for _, r in pool.iterrows()]
    id_by_label = dict(zip(labels, pool["employee_id"]))
    with st.sidebar:
        st.markdown("###### Role to backfill")
        st.caption("Defaults to the highest-priority flight risk.")
        choice = st.selectbox("Incumbent", labels, index=0, label_visibility="collapsed")

    nn, matrix, pos_index = _successor_index()
    target, succ = succession.find_successors(
        id_by_label[choice], active, nn, matrix, pos_index, k=5)

    ready_now = int((succ["readiness"] == "Ready now").sum())
    c1, c2 = st.columns([1, 2.1])
    with c1:
        T.panel_header("Open role")
        st.markdown(
            f'<div class="profile"><div class="name">{target["name"]}</div>'
            f'<div class="meta">{target["department"]} · {target["tenure_years"]:.0f} yrs · '
            f'perf {target["performance_rating"]}/5 · potential {target["potential"]}/5</div>'
            f'{T.talent_chip(target["talent_call"])} '
            f'<span class="chip high">P(leave) {target["p_attrition"]:.0%}</span>'
            f'<div class="succ-callout"><div class="k">Bench strength</div>'
            f'<div class="v">{ready_now} ready-now successor{"s" if ready_now != 1 else ""}</div>'
            f'<div class="panel-sub" style="margin-top:6px;">of {len(succ)} closest internal '
            f'profiles</div></div></div>', unsafe_allow_html=True)
    with c2:
        T.panel_header("Ranked internal successors",
                       "Successor score = profile match × readiness × retention.")
        for i, (_, cand) in enumerate(succ.iterrows(), start=1):
            _successor_card(i, cand)
