"""People Analytics — Retention Priority dashboard (entry point).

Decision-first executive view over the augmented workforce dataset. Spine: a
Retention Priority Score (P(attrition) x talent value x pay risk) that ranks the
people leadership cannot afford to lose, each with the *why* and a suggested action.

Run:  streamlit run app/streamlit_app.py
"""
import streamlit as st

import theme as T

st.set_page_config(page_title="People Analytics · Retention Priority",
                   page_icon="◆", layout="wide", initial_sidebar_state="expanded")
T.inject_css()

import views  # noqa: E402  (after set_page_config; loads cached data on import)

with st.sidebar:
    T.brand()

nav = st.navigation([
    st.Page(views.overview, title="Executive Overview", default=True,
            icon=":material/dashboard:"),
    st.Page(views.model_page, title="Why People Leave", icon=":material/insights:"),
    st.Page(views.tenure_page, title="Tenure & Lifecycle", icon=":material/timeline:"),
    st.Page(views.priority_page, title="Retention Priority", icon=":material/flag:"),
    st.Page(views.pay_page, title="Pay Equity", icon=":material/payments:"),
    st.Page(views.succession_page, title="Succession", icon=":material/account_tree:"),
])
nav.run()

with st.sidebar:
    st.markdown("<hr>", unsafe_allow_html=True)
    T.legend()
