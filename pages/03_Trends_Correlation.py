
import re

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from core.analysis_controls import (
    render_analysis_controls,
    apply_analysis_filters,
)
from core.chart_colors import (
    get_variable_color,
    get_variable_line_style,
)



# ============================================================
# CONFIGURATION
# ============================================================

st.title("Trends & Correlation")
st.caption(
    "Time-series trends, electrical and sensor data, distributions, "
    "and correlation analysis."
)

GAP_THRESHOLD_SECONDS = 120
MAX_PLOT_POINTS = 25000


# ============================================================
# LOAD SOURCE DATA
# ============================================================

df_source = st.session_state.get("dataframe")

if not isinstance(df_source, pd.DataFrame) or df_source.empty:
    st.warning("No imported dataset was found. Please import data first.")
    st.stop()


# ============================================================
# HELPERS
# ============================================================

def normalize_name(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def find_column(columns, aliases):
    normalized = {normalize_name(c): c for c in columns}

    for alias in aliases:
        result = normalized.get(normalize_name(alias))
        if result is not None:
            return result

    return None


def to_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def format_timestamp(value):
    if pd.isna(value):
        return "N/A"

    return pd.Timestamp(value).strftime("%Y-%m-%d %H:%M:%S")


def make_plot_data(data, time_column):
    """
    Add NaN separator rows at acquisition gaps using vectorized
    operations rather than iterating through every source row.
    """

    if len(data) < 2:
        return data.copy()

    times = data[time_column]
    gap_mask = times.diff().dt.total_seconds().gt(
        GAP_THRESHOLD_SECONDS
    )

    gap_positions = np.flatnonzero(gap_mask.to_numpy())

    if len(gap_positions) == 0:
        return data

    separators = pd.DataFrame(
        np.nan,
        index=np.arange(len(gap_positions)),
        columns=data.columns,
    )

    previous_times = times.iloc[
        gap_positions - 1
    ].reset_index(drop=True)

    next_times = times.iloc[
        gap_positions
    ].reset_index(drop=True)

    separators[time_column] = (
        previous_times + (next_times - previous_times) / 2
    )

    original = data.copy()
    original["_original_order"] = np.arange(len(original), dtype=float)
    original["_separator_order"] = 0

    separators["_original_order"] = gap_positions - 0.5
    separators["_separator_order"] = 1

    combined = pd.concat(
        [original, separators],
        ignore_index=True,
    )

    combined = combined.sort_values(
        ["_original_order", "_separator_order"],
        kind="stable",
    )

    return (
        combined.drop(
            columns=["_separator_order", "_original_order"]
        )
        .reset_index(drop=True)
    )


def smooth_continuous_segments(
    data,
    time_column,
    column,
    window,
    threshold_seconds=120,
):
    """
    Centered moving average that does not cross missing values
    or acquisition gaps.
    """

    raw = to_numeric(data[column])
    timestamps = data[time_column]

    if len(data) == 0:
        return pd.Series(index=data.index, dtype=float)

    valid = timestamps.notna() & raw.notna()

    if not valid.any():
        return pd.Series(np.nan, index=data.index, dtype=float)

    elapsed = timestamps.diff().dt.total_seconds()

    new_segment = (
        ~valid
        | ~valid.shift(1, fill_value=False)
        | elapsed.gt(threshold_seconds)
    )

    new_segment = new_segment & valid
    segment_id = new_segment.cumsum()

    work = pd.DataFrame(
        {
            "value": raw,
            "segment": segment_id,
            "valid": valid,
        },
        index=data.index,
    )

    result = pd.Series(np.nan, index=data.index, dtype=float)
    valid_work = work.loc[work["valid"]]

    if valid_work.empty:
        return result

    smoothed = valid_work.groupby(
        "segment", sort=False
    )["value"].transform(
        lambda values: values.rolling(
            window=int(window),
            min_periods=1,
            center=True,
        ).mean()
    )

    result.loc[valid_work.index] = smoothed.to_numpy()

    return result


def downsample_for_plot(data, max_points=MAX_PLOT_POINTS):
    """
    Reduce points sent to Plotly for rendering only.
    Statistics and moving averages are calculated before this step.
    """

    if len(data) <= max_points:
        return data

    numeric_columns = data.select_dtypes(
        include=[np.number]
    ).columns

    if len(numeric_columns):
        separator_mask = data[numeric_columns].isna().all(axis=1)
    else:
        separator_mask = pd.Series(False, index=data.index)

    separator_positions = np.flatnonzero(
        separator_mask.to_numpy()
    )

    regular_positions = np.linspace(
        0,
        len(data) - 1,
        num=max_points,
        dtype=np.int64,
    )

    positions = np.unique(
        np.concatenate([regular_positions, separator_positions])
    )

    return data.iloc[positions]


def add_trace(
    fig,
    data,
    time_column,
    column,
    label,
    value_cache,
    secondary_y=False,
):
    if column is None or column not in data.columns:
        return

    values = value_cache.get(column)

    if values is None or not values.notna().any():
        return

    trace = go.Scattergl(
        x=data[time_column],
        y=values,
        mode="lines",
        name=label,
        connectgaps=False,
    )

    if secondary_y:
        trace.update(yaxis="y2")

    fig.add_trace(trace)


def make_single_axis_chart(
    data,
    time_column,
    title,
    series,
    value_cache,
    y_axis_title="Value",
):
    fig = go.Figure()

    for column, label in series:
        add_trace(
            fig,
            data,
            time_column,
            column,
            label,
            value_cache,
        )

    fig.update_layout(
        title=title,
        height=430,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=20, r=20, t=80, b=30),
        xaxis_title="Time",
        yaxis_title=y_axis_title,
    )

    return fig


def make_dual_axis_chart(
    data,
    time_column,
    title,
    left_column,
    right_column,
    left_label,
    right_label,
    value_cache,
):
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    for column, label, secondary in [
        (left_column, left_label, False),
        (right_column, right_label, True),
    ]:
        values = value_cache.get(column)

        if values is not None and values.notna().any():
            fig.add_trace(
                go.Scattergl(
                    x=data[time_column],
                    y=values,
                    mode="lines",
                    name=label,
                    connectgaps=False,
                ),
                secondary_y=secondary,
            )

    fig.update_layout(
        title=title,
        height=430,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=20, r=20, t=80, b=30),
    )

    fig.update_xaxes(title_text="Time")
    fig.update_yaxes(title_text=left_label, secondary_y=False)
    fig.update_yaxes(title_text=right_label, secondary_y=True)

    return fig


def show_missing_columns(names):
    missing = [
        name for name, column in names
        if column is None
    ]

    if missing:
        st.caption(
            "Columns not found in the imported dataset: "
            + ", ".join(missing)
        )


# ============================================================
# IDENTIFY REQUIRED COLUMNS
# ============================================================

columns = list(df_source.columns)

time_column = find_column(
    columns,
    ["Time", "DateTime", "Timestamp", "Date Time", "Date"],
)

if time_column is None:
    st.error("Could not identify the time column.")
    st.write("Available columns:", columns)
    st.stop()


aliases = {
    "oil": ["Oil rate", "OilRate", "Oil Rate"],
    "water": ["Water rate", "WaterRate", "Water Rate"],
    "gas": ["Gas rate", "GasRate", "Gas Rate"],
    "gvf": ["ActGVF", "Act GVF", "ACT GVF", "GVF"],
    "wlr": ["ActWLR", "Act WLR", "ACT WLR", "WLR"],
    "dp": ["dP", "DP", "Delta P", "Differential Pressure"],
    "density": ["Density", "Liquid Density"],
    "pflow": ["P-flow", "P Flow", "Pflow", "Pressure Flow"],
    "tflow": ["T-flow", "T Flow", "Tflow", "Temperature Flow"],
    "ch1": ["CH1_PermCond", "CH1 PermCond", "CH1 Perm Cond"],
    "ch2": ["CH2_PermCond", "CH2 PermCond", "CH2 Perm Cond"],
    "ch3": ["CH3_PermCond", "CH3 PermCond", "CH3 Perm Cond"],
    "gasperm": ["GasPerm", "GasPerm(CM)", "GasPermCM", "Gas Perm"],
    "velmix": ["Vel.mix", "Vel Mix", "VelMix", "Mixture Velocity"],
    "qmass": ["QmassTot", "Qmass Tot", "Q Mass Total"],
}

col = {
    key: find_column(columns, possible_names)
    for key, possible_names in aliases.items()
}

qmass_column = col["qmass"]

required_columns = list(
    dict.fromkeys(
        [time_column]
        + [value for value in col.values() if value is not None]
    )
)

# Select only columns used by this page.
df_all = df_source.loc[:, required_columns].copy()

df_all[time_column] = pd.to_datetime(
    df_all[time_column],
    errors="coerce",
)

df_all = df_all.dropna(subset=[time_column])

df_all = df_all.drop_duplicates(
    subset=[time_column],
    keep="last",
)

df_all = df_all.sort_values(
    time_column,
    ignore_index=True,
)

# Convert required numeric columns once.
for column in col.values():
    if column is not None:
        df_all[column] = to_numeric(df_all[column])





# ============================================================
# APPLY SHARED ANALYSIS CONTROLS
# ============================================================

controls = render_analysis_controls(
    dataframe=df_all,
    time_column=time_column,
    qmass_column=qmass_column,
)

df = apply_analysis_filters(
    dataframe=df_all,
    time_column=time_column,
    qmass_column=qmass_column,
    controls=controls,
)

if df.empty:
    st.warning(
        "No records remain after applying the selected time range "
        "and QmassTot filter."
    )
    st.stop()

# Shared QmassTot filter.
filter_mode = controls["qmass_filter"]

st.session_state["enable_filter"] = filter_mode != "All data"
st.session_state["filter_mode"] = filter_mode

# Shared Moving Average controls.
smoothing_enabled = controls["ma_enabled"]
window = int(controls["ma_window"])

st.caption(
    f"Records: {len(df):,} | "
    f"Start: {format_timestamp(df[time_column].iloc[0])} | "
    f"End: {format_timestamp(df[time_column].iloc[-1])} | "
    f"QmassTot filter: {filter_mode} | "
    f"Moving Average: "
    f"{'ON (' + str(window) + ' samples)' if smoothing_enabled else 'OFF'}"
)



# ============================================================
# PREPARE PLOT DATA AND CACHE SERIES
# ============================================================

df_plot_full = make_plot_data(
    df,
    time_column,
)

plot_positions = np.linspace(
    0,
    len(df_plot_full) - 1,
    num=min(MAX_PLOT_POINTS, len(df_plot_full)),
    dtype=np.int64,
)

separator_columns = [
    c for c in df_plot_full.columns
    if c != time_column
]

if separator_columns:
    separator_mask = df_plot_full[separator_columns].isna().all(axis=1)
    separator_positions = np.flatnonzero(separator_mask.to_numpy())

    plot_positions = np.unique(
        np.concatenate([plot_positions, separator_positions])
    )

df_plot = df_plot_full.iloc[plot_positions].reset_index(drop=True)

# Calculate displayed series once, reusing them across charts.
value_cache = {}

for key, column in col.items():
    if column is None:
        continue

    if smoothing_enabled:
        values = smooth_continuous_segments(
            df_plot_full,
            time_column,
            column,
            int(window),
            GAP_THRESHOLD_SECONDS,
        )
    else:
        values = to_numeric(df_plot_full[column])

    value_cache[column] = (
        values.iloc[plot_positions].reset_index(drop=True)
    )


# ============================================================
# 1. FLOW RATES
# ============================================================

st.header("1. Flow Rates")

show_missing_columns([
    ("Oil rate", col["oil"]),
    ("Water rate", col["water"]),
    ("Gas rate", col["gas"]),
])

fig = make_subplots(specs=[[{"secondary_y": True}]])

for key, label in [
    ("oil", "Oil rate"),
    ("water", "Water rate"),
]:
    column = col[key]

    if column is not None and value_cache[column].notna().any():
        fig.add_trace(
            go.Scattergl(
                x=df_plot[time_column],
                y=value_cache[column],
                mode="lines",
                name=label,
                connectgaps=False,
            ),
            secondary_y=False,
        )

if (
    col["gas"] is not None
    and value_cache[col["gas"]].notna().any()
):
    fig.add_trace(
        go.Scattergl(
            x=df_plot[time_column],
            y=value_cache[col["gas"]],
            mode="lines",
            name="Gas rate",
            connectgaps=False,
        ),
        secondary_y=True,
    )

if any(col[key] is not None for key in ["oil", "water", "gas"]):
    fig.update_layout(
        title="Flow Rates: Oil & Water (Y1) vs Gas (Y2)",
        height=460,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=20, r=20, t=80, b=30),
    )
    fig.update_xaxes(title_text="Time")
    fig.update_yaxes(title_text="Oil / Water Rate", secondary_y=False)
    fig.update_yaxes(title_text="Gas Rate", secondary_y=True)

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No flow-rate columns were found.")


# ============================================================
# 2. GVF & WLR
# ============================================================

st.header("2. GVF & WLR")

show_missing_columns([
    ("ActGVF", col["gvf"]),
    ("ActWLR", col["wlr"]),
])

available_gvf_wlr = [
    (col[key], label)
    for key, label in [
        ("gvf", "ActGVF"),
        ("wlr", "ActWLR"),
    ]
    if col[key] is not None
]

if available_gvf_wlr:
    fig = make_single_axis_chart(
        df_plot,
        time_column,
        "GVF & WLR",
        available_gvf_wlr,
        value_cache,
        y_axis_title="Fraction",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("GVF and WLR columns were not found.")


# ============================================================
# 3–6. dP COMPARISONS
# ============================================================

st.header("3–6. Differential Pressure Comparisons")

comparison_specs = [
    ("dP vs Density", "dp", "density", "dP", "Density"),
    ("dP vs P-flow", "dp", "pflow", "dP", "P-flow"),
    ("dP vs T-flow", "dp", "tflow", "dP", "T-flow"),
    ("dP vs ActWLR", "dp", "wlr", "dP", "ActWLR"),
]

for title, left_key, right_key, left_label, right_label in comparison_specs:
    left_column = col[left_key]
    right_column = col[right_key]

    if left_column is None or right_column is None:
        missing = []

        if left_column is None:
            missing.append(left_label)

        if right_column is None:
            missing.append(right_label)

        st.subheader(title)
        st.caption("Missing columns: " + ", ".join(missing))
        continue

    fig = make_dual_axis_chart(
        data=df_plot,
        time_column=time_column,
        title=title,
        left_column=left_column,
        right_column=right_column,
        left_label=left_label,
        right_label=right_label,
        value_cache=value_cache,
    )

    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# 7. ELECTRICAL & SENSOR DATA
# ============================================================

st.header("7. Electrical & Sensor Data")

sensor_specs = [
    ("ch1", "CH1 Perm/Cond"),
    ("ch2", "CH2 Perm/Cond"),
    ("ch3", "CH3 Perm/Cond"),
    ("gasperm", "GasPerm"),
]

show_missing_columns([
    (label, col[key])
    for key, label in sensor_specs
])

available_sensors = [
    (key, label)
    for key, label in sensor_specs
    if col[key] is not None
]

if available_sensors:
    fig = go.Figure()

    for key, label in available_sensors:
        column = col[key]

        if value_cache[column].notna().any():
            fig.add_trace(
                go.Scattergl(
                    x=df_plot[time_column],
                    y=value_cache[column],
                    mode="lines",
                    name=label,
                    connectgaps=False,
                )
            )

    fig.update_layout(
        title="Perm/Cond: CH1, CH2, CH3 & GasPerm",
        height=460,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=20, r=20, t=80, b=30),
        xaxis_title="Time",
        yaxis_title="Permittivity / Conductivity",
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No requested sensor columns were found.")


# ============================================================
# 8. DISTRIBUTION HISTOGRAMS
# ============================================================

st.header("8. Distribution")

histogram_specs = [
    ("ActGVF", "gvf"),
    ("ActWLR", "wlr"),
    ("dP", "dp"),
    ("Vel.mix", "velmix"),
]

show_missing_columns([
    (label, col[key])
    for label, key in histogram_specs
])

available_histograms = [
    (label, col[key])
    for label, key in histogram_specs
    if col[key] is not None
]

if available_histograms:
    histogram_columns = st.columns(2)

    for i, (label, column) in enumerate(available_histograms):
        with histogram_columns[i % 2]:
            # Histograms use original values, without moving average.
            values = to_numeric(df[column]).dropna()

            if values.empty:
                st.info(f"No valid values for {label}.")
                continue

            fig = px.histogram(
                x=values,
                nbins=40,
                histnorm="percent",
                title=f"{label} Distribution",
                labels={
                    "x": label,
                    "y": "Percentage (%)",
                },
            )

            fig.update_layout(
                height=350,
                showlegend=False,
                margin=dict(l=15, r=15, t=60, b=25),
            )

            st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No histogram variables were found.")


# ============================================================
# 9. CORRELATION MATRIX — PEARSON, LOWER TRIANGLE ONLY
# ============================================================

st.header("Correlation Matrix")

st.caption(
    "Pearson correlation using original numeric values after applying "
    "the selected time range and QmassTot filter. Moving Average "
    "is not applied."
)

correlation_candidates = [
    ("dP", "dp"),
    ("Density", "density"),
    ("P-flow", "pflow"),
    ("T-flow", "tflow"),
    ("CH1_PermCond", "ch1"),
    ("CH2_PermCond", "ch2"),
    ("CH3_PermCond", "ch3"),
    ("Vel.mix", "velmix"),
]

correlation_data = pd.DataFrame(index=df.index)
missing_variables = []

for label, key in correlation_candidates:
    column = col[key]

    if column is None:
        missing_variables.append(label)
    else:
        correlation_data[label] = to_numeric(df[column])

if missing_variables:
    st.warning(
        "The following variables were not found and will be excluded: "
        + ", ".join(missing_variables)
    )

correlation_data = correlation_data.dropna(axis=1, how="all")

if not correlation_data.empty:
    correlation_data = correlation_data.loc[
        :,
        correlation_data.nunique(dropna=True) > 1,
    ]

if correlation_data.shape[1] < 2:
    st.info(
        "At least two numeric variables with variation are required "
        "to calculate the correlation matrix."
    )
else:
    correlation_matrix = correlation_data.corr(
        method="pearson",
        min_periods=3,
    )

    matrix_values = correlation_matrix.to_numpy(dtype=float).copy()

    # Hide upper triangle, including the diagonal.
    matrix_values[np.triu_indices_from(matrix_values, k=0)] = np.nan

    text_values = [
        [
            "" if not np.isfinite(value) else f"{value:.2f}"
            for value in row
        ]
        for row in matrix_values
    ]

    fig = go.Figure(
        data=go.Heatmap(
            z=matrix_values,
            x=correlation_matrix.columns.tolist(),
            y=correlation_matrix.index.tolist(),
            zmin=-1,
            zmax=1,
            zmid=0,
            colorscale="RdBu",
            reversescale=True,
            text=text_values,
            texttemplate="%{text}",
            colorbar={"title": "Pearson r"},
            hovertemplate=(
                "Variable X: %{x}<br>"
                "Variable Y: %{y}<br>"
                "Pearson correlation: %{z:.3f}"
                "<extra></extra>"
            ),
            hoverongaps=False,
        )
    )

    fig.update_layout(
        title="Pearson Correlation Matrix",
        height=650,
        xaxis_title="Variable",
        yaxis_title="Variable",
        margin=dict(l=130, r=30, t=80, b=140),
    )

    fig.update_xaxes(tickangle=-45, side="bottom")
    fig.update_yaxes(autorange="reversed")

    st.plotly_chart(fig, use_container_width=True)

    with st.expander("View correlation values as a table"):
        st.dataframe(
            correlation_matrix.style.format("{:.3f}", na_rep=""),
            use_container_width=True,
        )


# ============================================================
# 10. CH1 / CH2 RATIO — MOVING AVERAGES ONLY
# ============================================================

st.header("10. CH1 / CH2 Ratio — Moving Averages")

st.caption(
    "Centered moving averages of the CH1/CH2 ratio for 5, 10, 30 "
    "and 60 samples. The raw ratio is not displayed."
)

ch1_column = col["ch1"]
ch2_column = col["ch2"]

if ch1_column is None or ch2_column is None:
    missing = []

    if ch1_column is None:
        missing.append("CH1_PermCond")

    if ch2_column is None:
        missing.append("CH2_PermCond")

    st.warning(
        "Cannot calculate CH1/CH2 ratio. Missing columns: "
        + ", ".join(missing)
    )

else:
    ratio_data = pd.DataFrame({
        time_column: df[time_column].reset_index(drop=True),
        "CH1_CH2_Ratio": (
            df[ch1_column].reset_index(drop=True)
            / df[ch2_column].replace(0, np.nan).reset_index(drop=True)
        ),
    })

    ratio_data["CH1_CH2_Ratio"] = (
        ratio_data["CH1_CH2_Ratio"]
        .replace([np.inf, -np.inf], np.nan)
    )

    ratio_plot_full = make_plot_data(ratio_data, time_column)

    # Compute all four moving averages on the filtered dataset.
    fig = go.Figure()

    for ma_window in [5, 10, 30, 60]:
        smoothed_ratio = smooth_continuous_segments(
            ratio_plot_full,
            time_column,
            "CH1_CH2_Ratio",
            ma_window,
            GAP_THRESHOLD_SECONDS,
        )

        if smoothed_ratio.notna().any():
            ratio_with_smoothing = ratio_plot_full.assign(
                _smoothed=smoothed_ratio.to_numpy()
            )

            ratio_display = downsample_for_plot(
                ratio_with_smoothing
            )

            fig.add_trace(
                go.Scattergl(
                    x=ratio_display[time_column],
                    y=ratio_display["_smoothed"],
                    mode="lines",
                    name=f"MA {ma_window}",
                    connectgaps=False,
                )
            )

    fig.update_layout(
        title="CH1/CH2 Ratio — Moving Averages",
        height=500,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
        margin=dict(l=20, r=20, t=90, b=30),
        xaxis_title="Time",
        yaxis_title="CH1 / CH2 Ratio",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        key="ch1_ch2_moving_average_comparison",
    )

    st.caption(
        "The ratio is calculated as CH1_PermCond / CH2_PermCond. "
        "Missing values and zero denominators are excluded. "
        "Moving averages use centered windows and do not cross "
        "acquisition gaps."
    )
