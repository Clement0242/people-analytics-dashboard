"""AI Analyst: ask the dashboard's data in plain language.

The model never sees the raw table. The app computes a compact, numeric
summary of the workforce (the same figures the pages show), adds the focused
employee if one is chosen, and sends it with the conversation to a relay
(Cloudflare Worker) that holds the OpenRouter key and only allows free models.
The relay's instructions forbid inventing numbers and remind that the data is
public + synthetic.

Transport:
- in the browser version (stlite / Pyodide) Python runs in a web worker, where
  a synchronous XMLHttpRequest is allowed: no async plumbing in the page;
- in the server version (streamlit run), urllib; if OPENROUTER_API_KEY is set
  in the environment, OpenRouter is called directly with the same free models.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

import numpy as np
import pandas as pd
import streamlit as st

import theme as T

RELAY = "https://clement-assistant.clement-verdier.workers.dev"
SITE = "https://clement0242.github.io"
FREE_MODELS = ["nvidia/nemotron-3-super-120b-a12b:free", "qwen/qwen3.8-27b:free", "openrouter/free"]
DIMS = ["Leadership & Manager", "Career & Growth", "Reward & Recognition",
        "Workload & Wellbeing", "Belonging & Conviviality", "Enablement & Tools"]
KEY = {"Accelerate", "Stretch"}

SUGGESTIONS = [
    "Which departments should leadership worry about first, and why?",
    "Are we losing our best people? Quantify regretted attrition.",
    "Who are the top 5 flight risks among key talent, and what would you do for each?",
    "How much would it cost to bring underpaid key talent to 0.95 compa-ratio?",
    "What does the engagement survey say about leavers vs stayers?",
    "How reliable is the attrition model, and what are its limits?",
    "When in their tenure do people leave, and what should onboarding change?",
    "Explain the Retention Priority Score to a non-technical HR director.",
]


def _pct(x):
    return f"{100 * x:.1f}%"


@st.cache_data(show_spinner=False)
def data_summary(df: pd.DataFrame, M: dict) -> str:
    """The numeric facts the model may use. ~8-10k characters, English."""
    act = df[df["status"] == "Active"]
    lv = df[df["attrition"] == 1]
    L = []
    add = L.append
    add("DATASET: public HR attrition dataset (14,999 employees, real 'left' label) + seeded synthetic layers "
        "(27-question survey, potential, 9-box, talent call, salary, market benchmark, compa-ratio, names, dates). "
        "Departures spread over the last 12 months. Independent case study, not a real company.")
    add(f"HEADLINE: employees {len(df):,}; active {len(act):,}; leavers {len(lv):,}; attrition {_pct(df['attrition'].mean())}; "
        f"regretted attrition = voluntary leavers in Accelerate/Stretch: {int(df['regretted'].sum())} people = "
        f"{_pct(df['regretted'].sum() / max(len(lv), 1))} of leavers; median compa-ratio (active) {act['compa_ratio'].median():.2f}; "
        f"active below 0.90 compa: {_pct((act['compa_ratio'] < 0.90).mean())}; priority bands (active): "
        + ", ".join(f"{k} {v}" for k, v in act["priority_band"].value_counts().items()) + ".")
    cm = M["confusion"]
    add(f"MODEL: gradient boosting; split grouped by identical record (dataset has {M.get('duplicate_rows', 3008)} duplicate rows); "
        f"ROC-AUC {M['roc_auc']} (naive random split {M.get('naive_roc_auc', 'n/a')}); PR-AUC {M['pr_auc']}; threshold "
        f"{M['threshold']} chosen on training folds; precision {cm['tp'] / max(cm['tp'] + cm['fp'], 1):.2f}, recall "
        f"{cm['tp'] / max(cm['tp'] + cm['fn'], 1):.2f}; every employee scored out-of-fold. Global drivers (permutation "
        "importance): " + ", ".join(f"{k} {v:.3f}" for k, v in list(M["global_importance"].items())[:7]) + ". "
        "Per-employee drivers = drop in predicted risk when the factor is set to the company median.")
    add("PRIORITY SCORE: P(attrition) x talent weight (Accelerate 1.0, Stretch 0.65, Grow in role 0.30) x pay factor "
        "(1 + 2 x max(0, 0.95 - compa), capped), scaled to the highest active score = 100; bands by capacity: High = top "
        "0.5% of active, Medium = next 2.5%.")
    g = df.groupby("department").agg(n=("attrition", "size"), attr=("attrition", "mean"), reg=("regretted", "sum"),
                                       compa=("compa_ratio", "median"), eng=("engagement_index", "mean"))
    hi = act.groupby("department")["priority_band"].apply(lambda s: int((s == "High").sum()))
    add("BY DEPARTMENT (headcount, attrition, regretted leavers, median compa, mean engagement 0-1, active High-priority): "
        + "; ".join(f"{d} {int(r.n)} / {_pct(r.attr)} / {int(r.reg)} / {r.compa:.2f} / {r.eng:.2f} / {int(hi.get(d, 0))}"
                    for d, r in g.sort_values("attr", ascending=False).iterrows()))
    t = df.groupby("talent_call").agg(n=("attrition", "size"), attr=("attrition", "mean"), compa=("compa_ratio", "median"))
    add("BY TALENT CALL (n, attrition, median compa): " + "; ".join(f"{k} {int(r.n)} / {_pct(r.attr)} / {r.compa:.2f}" for k, r in t.iterrows()))
    pr = df.groupby("performance_rating")["attrition"].agg(["size", "mean"])
    add("BY PERFORMANCE RATING 1-5 (n, attrition): " + "; ".join(f"{k}: {int(r['size'])} / {_pct(r['mean'])}" for k, r in pr.iterrows()))
    tn = df.groupby("tenure_years")["attrition"].agg(["size", "mean"])
    add("BY TENURE YEARS (n, attrition): " + "; ".join(f"{int(k)}y: {int(r['size'])} / {_pct(r['mean'])}" for k, r in tn.iterrows()))
    sb = df.groupby("salary_band")["attrition"].mean()
    add("BY SALARY BAND (attrition): " + "; ".join(f"{k} {_pct(v)}" for k, v in sb.items()))
    df_ = df.assign(eq=pd.qcut(df["engagement_index"], 3, labels=["low", "mid", "high"]))
    add("BY ENGAGEMENT TERCILE (attrition): " + "; ".join(f"{k} {_pct(v)}" for k, v in df_.groupby("eq", observed=True)["attrition"].mean().items()))
    sv = df.groupby("attrition")[[f"survey_{d}" for d in DIMS]].mean()
    add("SURVEY MEANS 1-5, stayers vs leavers: " + "; ".join(f"{d} {sv.loc[0, 'survey_' + d]:.2f} vs {sv.loc[1, 'survey_' + d]:.2f}" for d in DIMS))
    ct = lv["comment_theme"].value_counts(normalize=True).head(6)
    add("LEAVERS' COMMENT THEMES: " + "; ".join(f"{k} {_pct(v)}" for k, v in ct.items()))
    hours = df.groupby(pd.cut(df["avg_monthly_hours"], [0, 150, 200, 250, 400]), observed=True)["attrition"].mean()
    add("BY MONTHLY HOURS (attrition): " + "; ".join(f"{k} {_pct(v)}" for k, v in hours.items()))
    proj = df.groupby("projects")["attrition"].mean()
    add("BY NUMBER OF PROJECTS (attrition): " + "; ".join(f"{int(k)} {_pct(v)}" for k, v in proj.items()))
    promo = df.groupby("promoted_last_5y")["attrition"].mean()
    add(f"PROMOTED IN LAST 5 YEARS: attrition {_pct(promo.get(1, np.nan))} vs not promoted {_pct(promo.get(0, np.nan))}.")
    ku = act[act["talent_call"].isin(KEY) & (act["compa_ratio"] < 0.90)]
    gap = ((0.95 - ku["compa_ratio"]).clip(lower=0) * ku["market_benchmark"]).sum()
    add(f"PAY EQUITY: underpaid key talent (Accelerate/Stretch, compa < 0.90): {len(ku)}; cost to bring them to 0.95 "
        f"compa: ${gap / 1e6:.1f}M per year; underpaid active by talent call: "
        + "; ".join(f"{k} {_pct(v)}" for k, v in act.groupby("talent_call")["compa_ratio"].apply(lambda s: (s < 0.90).mean()).items()))
    add("SUGGESTED ACTIONS (active): " + "; ".join(f"{k} {v}" for k, v in act["suggested_action"].value_counts().items()))
    top = act.sort_values("priority_score", ascending=False).head(25)
    add("TOP 25 RETENTION PRIORITIES (id | name | department | talent call | perf/pot | tenure y | P(leave) | compa | drivers | action): "
        + " ; ".join(f"{r.employee_id} | {r['name']} | {r.department} | {r.talent_call} | {int(r.performance_rating)}/{int(r.potential)} | "
                     f"{int(r.tenure_years)} | {r.p_attrition:.2f} | {r.compa_ratio:.2f} | "
                     f"{', '.join(x for x in (r.driver_1, r.driver_2, r.driver_3) if isinstance(x, str) and x)} | {r.suggested_action}"
                     for _, r in top.iterrows()))
    add("DASHBOARD PAGES: Executive Overview, Why People Leave (drivers, model reliability, regretted check), Tenure & "
        "Lifecycle, Retention Priority (ranked list + employee profile), Pay Equity (compa-ratio, double-risk quadrant, "
        "what-if slider), Succession (k-nearest-neighbour successors), AI Analyst (this chat).")
    return "\n".join(L)


def employee_summary(r: pd.Series) -> str:
    dims = "; ".join(f"{d} {r['survey_' + d]:.1f}" for d in DIMS)
    return (f"FOCUSED EMPLOYEE: {r.employee_id} {r['name']}, {r.department}, status {r.status}, tenure {int(r.tenure_years)} y, "
            f"performance {int(r.performance_rating)}/5, potential {int(r.potential)}/5, talent call {r.talent_call}, "
            f"salary ${r.salary:,.0f} vs market ${r.market_benchmark:,.0f} (compa {r.compa_ratio:.2f}), monthly hours "
            f"{int(r.avg_monthly_hours)}, projects {int(r.projects)}, promoted last 5y {'yes' if r.promoted_last_5y else 'no'}, "
            f"engagement {r.engagement_index:.2f}, survey {r.survey_score:.2f}/5 ({dims}), comment theme '{r.comment_theme}', "
            f"P(leave) {r.p_attrition:.2f}, priority {r.priority_score if pd.notna(r.priority_score) else 'n/a'} "
            f"({r.priority_band if isinstance(r.priority_band, str) else 'n/a'}), drivers "
            f"{', '.join(x for x in (r.driver_1, r.driver_2, r.driver_3) if isinstance(x, str) and x)}, suggested action "
            f"'{r.suggested_action if isinstance(r.suggested_action, str) else 'n/a'}'.")


def _post(url: str, payload: dict, headers: dict) -> tuple[int, str]:
    body = json.dumps(payload)
    if "pyodide" in sys.modules:                       # browser: sync XHR is allowed in a web worker
        from js import XMLHttpRequest  # type: ignore
        req = XMLHttpRequest.new()
        req.open("POST", url, False)
        for k, v in headers.items():
            req.setRequestHeader(k, v)
        req.send(body)
        return int(req.status), str(req.responseText)
    rq = urllib.request.Request(url, data=body.encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(rq, timeout=90) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def ask(messages: list[dict], data: str) -> tuple[str, str]:
    """Send the conversation; returns (answer, model) or raises RuntimeError with a readable reason."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if key and "pyodide" not in sys.modules:           # local server with its own key
        sysmsg = ("You are the AI analyst of a People Analytics dashboard. Answer only from the DATA; never invent "
                  "numbers; the data is public + synthetic; answer in the user's language; be concise.\n\nDATA\n" + data)
        code, txt = _post("https://openrouter.ai/api/v1/chat/completions",
                          {"models": FREE_MODELS, "messages": [{"role": "system", "content": sysmsg}] + messages[-12:],
                           "max_tokens": 900, "reasoning": {"enabled": False}},
                          {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                           "HTTP-Referer": SITE, "X-Title": "People Analytics dashboard"})
        if code != 200:
            raise RuntimeError(f"OpenRouter error {code}")
        d = json.loads(txt)
        return d["choices"][0]["message"]["content"].strip(), d.get("model", "")
    headers = {"Content-Type": "application/json"}
    if "pyodide" not in sys.modules:
        headers["Origin"] = SITE
    code, txt = _post(RELAY, {"mode": "people-analytics", "donnees": data, "messages": messages[-12:]}, headers)
    try:
        d = json.loads(txt)
    except ValueError:
        d = {}
    if code == 200 and d.get("reponse"):
        return d["reponse"], d.get("modele", "")
    reason = {"trop": "Too many questions in a minute — wait a few seconds.",
              "quota": "The free daily quota is used up — try again tomorrow.",
              "indisponible": "The free models are busy right now — try again in a moment.",
              "messages": "The assistant is not enabled on the relay yet."}.get(d.get("erreur"), f"Relay error {code}.")
    raise RuntimeError(reason)


def page(df: pd.DataFrame, M: dict) -> None:
    T.title(
        "AI Analyst",
        "Ask the workforce data in plain language. The assistant answers <b>only</b> from the figures this dashboard "
        "computes — headline KPIs, model reliability, departments, talent, tenure, survey, pay equity and the 25 top "
        "retention priorities — and says when the data cannot answer. Free open models via OpenRouter; "
        "<span class='teal'>public + synthetic data</span>, names are generated.")
    data = data_summary(df, M)
    st.session_state.setdefault("chat", [])
    with st.sidebar:
        st.markdown('<div class="nav-label">Focus</div>', unsafe_allow_html=True)
        act = df[df["status"] == "Active"].sort_values("priority_score", ascending=False)
        opts = ["(whole workforce)"] + [f"{r.employee_id} · {r['name']} · {r.department}" for _, r in act.head(200).iterrows()]
        choice = st.selectbox("Add one employee to the context", opts, index=0,
                              help="The 200 highest retention priorities. Their full profile is added to what the assistant can see.")
        if st.button("Clear the conversation", width="stretch"):
            st.session_state["chat"] = []
            st.rerun()
    if choice != opts[0]:
        emp = df[df["employee_id"] == choice.split(" · ")[0]].iloc[0]
        data = data + "\n" + employee_summary(emp)
        T.insight(f"Focus on <b>{emp['name']}</b> ({emp.employee_id}) — the assistant sees the full profile.")

    pending = None
    if not st.session_state["chat"]:
        st.markdown("**Try one of these**")
        cols = st.columns(2)
        for i, q in enumerate(SUGGESTIONS):
            if cols[i % 2].button(q, key=f"sugg{i}", width="stretch"):
                pending = q
    for m in st.session_state["chat"]:
        with st.chat_message(m["role"], avatar=":material/analytics:" if m["role"] == "assistant" else None):
            st.markdown(m["content"])
            if m.get("model"):
                st.caption(f"Model: {m['model']}")
    typed = st.chat_input("Ask about attrition, talent, pay, engagement, a department or an employee…")
    q = typed or pending
    if q:
        st.session_state["chat"].append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.markdown(q)
        with st.chat_message("assistant", avatar=":material/analytics:"):
            with st.spinner("Reading the data…"):
                try:
                    hist = [{"role": m["role"], "content": m["content"]} for m in st.session_state["chat"]]
                    answer, model = ask(hist, data)
                except Exception as e:  # noqa: BLE001 - shown to the user, never crashes the page
                    answer, model = f"_{e}_", ""
            st.markdown(answer)
            if model:
                st.caption(f"Model: {model}")
        st.session_state["chat"].append({"role": "assistant", "content": answer, "model": model})
    with st.expander("What the assistant can see"):
        st.code(data, language=None)
