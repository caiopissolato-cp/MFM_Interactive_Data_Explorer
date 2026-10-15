"""Reusable KPI display components."""

import streamlit as st

def render_kpi(label: str, value, help_text: str | None = None):
    st.metric(label=label, value=value, help=help_text)
