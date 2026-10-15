"""Reusable Plotly time-series charts."""

import plotly.graph_objects as go
import streamlit as st

def render_line_chart(df, x_column: str, y_columns: list[str], title: str = "Trend"):
    fig = go.Figure()
    for column in y_columns:
        if x_column in df.columns and column in df.columns:
            fig.add_trace(go.Scatter(x=df[x_column], y=df[column], name=column, mode="lines"))
    fig.update_layout(title=title, template="plotly_white", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
