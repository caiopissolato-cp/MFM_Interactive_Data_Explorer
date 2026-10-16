
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.analysis_controls import (
    render_analysis_controls,
    apply_analysis_filters,
)
from core.chart_colors import (
    get_variable_color,
    get_variable_line_style,
)

st.set_page_config(page_title="Overview", layout="wide")


# ============================================================
# HELPERS
# ============================================================

def normalize_name(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def find_column(columns, aliases):
    normalized = {normalize_name(col): col for col in columns}

    for alias in aliases:
        match = normalized.get(normalize_name(alias))
        if match is not None:
            return match

    for col in columns:
        col_norm = normalize_name(col)

        for alias in aliases:
            alias_norm = normalize_name(alias)

            if alias_norm and alias_norm in col_norm:
                return col

    return None


def format_duration(seconds):
    """Format duration for the selected data period."""
    if pd.isna(seconds) or seconds < 0:
        return "N/A"

    seconds = int(round(seconds))
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)

    parts = []

    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    if minutes or hours or days:
        parts.append(f"{minutes}m")

    parts.append(f"{secs}s")
    return " ".join(parts)


def format_duration_hhmm(seconds):
    """Format duration as HH:MM, without seconds."""
    if pd.isna(seconds) or seconds < 0:
        return "N/A"

    total_minutes = int(seconds // 60)
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}:{minutes:02d}"


def prepare_data(source_df, time_column, qmass_column, required_columns):
    """Prepare only the columns required by Overview."""
    columns_to_keep = list(dict.fromkeys(
        [time_column, qmass_column]
        + [c for c in required_columns if c in source_df.columns]
    ))

    data = source_df.loc[:, columns_to_keep].copy()

    data[time_column] = pd.to_datetime(
        data[time_column],
        errors="coerce",
    )

    data[qmass_column] = pd.to_numeric(
        data[qmass_column],
        errors="coerce",
    )

    data = data.dropna(subset=[time_column])

    data = data.drop_duplicates(
        subset=[time_column],
        keep="last",
    )

    data = data.sort_values(
        time_column,
        ignore_index=True,
    )

    for column in required_columns:
        if column in data.columns and column != time_column:
            data[column] = pd.to_numeric(
                data[column],
                errors="coerce",
            )

    return data


def make_gauge(
    title,
    value,
    observed_values=None,
    percent=False,
    suffix="",
):
    """Create a gauge."""
    if value is None or pd.isna(value):
        axis_range = [0, 100] if percent else [0, 1]

        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=0,
                title={"text": title},
                number={"suffix": suffix},
                gauge={"axis": {"range": axis_range}},
            )
        )

        fig.update_layout(
            height=220,
            margin=dict(l=20, r=20, t=55, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        return fig

    value = float(value)

    if percent:
        axis_min, axis_max = 0, 100
    else:
        values = (
            pd.to_numeric(observed_values, errors="coerce").dropna()
            if observed_values is not None
            else pd.Series(dtype=float)
        )

        if not values.empty:
            axis_min = min(0.0, float(values.min()))
            axis_max = float(values.max())

            if axis_max <= axis_min:
                axis_max = axis_min + max(abs(axis_min) * 0.1, 1.0)
            else:
                axis_max += (axis_max - axis_min) * 0.08
        else:
            axis_min = min(0.0, value)
            axis_max = max(value * 1.1, 1.0)

    plotted_value = min(max(value, axis_min), axis_max)

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=plotted_value,
            title={"text": title},
            number={
                "suffix": suffix,
                "font": {"size": 24},
                "valueformat": ".1f" if percent else ".3f",
            },
            gauge={
                "axis": {
                    "range": [axis_min, axis_max],
                    "tickformat": ".0f" if percent else ".3g",
                },
                "bar": {"color": "#0f766e"},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 1,
                "bordercolor": "#94a3b8",
            },
        )
    )

    fig.update_layout(
        height=220,
        margin=dict(l=20, r=20, t=55, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
    )

    return fig


def calculate_category_time_percent(data, time_column, category_column):
    """
    Time-weighted percentage for each category.
    The state at a timestamp applies until the next timestamp.
    """
    if len(data) < 2:
        return {}

    timestamps = data[time_column]
    categories = data[category_column]

    intervals = (timestamps.shift(-1) - timestamps).dt.total_seconds()
    valid = intervals.gt(0) & categories.notna()

    total_seconds = intervals.loc[valid].sum()

    if total_seconds <= 0:
        return {}

    category_seconds = (
        pd.DataFrame({
            "category": categories.loc[valid],
            "seconds": intervals.loc[valid],
        })
        .groupby("category", sort=False)["seconds"]
        .sum()
    )

    return category_seconds.div(total_seconds).mul(100).to_dict()


def calculate_operating_time_percent(data, time_column, qmass_column):
    """Time-weighted percentage of valid intervals where QmassTot > 0."""
    if len(data) < 2:
        return None

    timestamps = data[time_column]
    qmass = data[qmass_column]

    intervals = (timestamps.shift(-1) - timestamps).dt.total_seconds()
    valid = intervals.gt(0) & qmass.notna()

    total_seconds = intervals.loc[valid].sum()

    if total_seconds <= 0:
        return None

    operating_seconds = intervals.loc[valid & qmass.gt(0)].sum()
    return operating_seconds / total_seconds * 100


# ============================================================
# ZERO FLOW EVENTS
# ============================================================

ZERO_FLOW_AVERAGE_ALIASES = {
    "dP Avg": ["dP", "DP", "Delta P", "Differential Pressure"],
    "CH1_PermCond Avg": [
        "CH1_PermCond", "CH1 PermCond", "CH1 Perm Cond",
    ],
    "CH2_PermCond Avg": [
        "CH2_PermCond", "CH2 PermCond", "CH2 Perm Cond",
    ],
    "CH3_PermCond Avg": [
        "CH3_PermCond", "CH3 PermCond", "CH3 Perm Cond",
    ],
    "Density Avg": ["Density", "Liquid Density"],
    "GasDensity Avg": ["GasDensity", "Gas Density", "Gas_Density"],
    "OilDensity Avg": ["OilDensity", "Oil Density", "Oil_Density"],
    "WaterDensity Avg": ["WaterDensity", "Water Density", "Water_Density"],
    "P-flow Avg": ["P-flow", "P Flow", "Pflow", "Pressure Flow"],
    "T-flow Avg": ["T-flow", "T Flow", "Tflow", "Temperature Flow"],
}


def get_zero_flow_events(
    data,
    time_column,
    qmass_column,
    gap_threshold_seconds=120,
    min_records=30,
    min_duration_minutes=30,
    exclude_last_records=5,
):
    """
    Identify Zero Flow events and acquisition gaps.

    - Ignore Zero Flow events with fewer than min_records.
    - Calculate averages only if duration reaches min_duration_minutes.
    - Exclude the last exclude_last_records zero-flow readings from averages.
    - Extend duration to the following positive-flow reading when appropriate.
    - Never merge events across acquisition gaps.
    - Data Gap events are listed independently of Zero Flow events.
    """
    average_columns = list(ZERO_FLOW_AVERAGE_ALIASES.keys())

    output_columns = [
        "Event Type",
        "Start Time",
        "End Time",
        "_DurationSeconds",
        "Entries",
    ] + average_columns

    if data is None or data.empty:
        return pd.DataFrame(columns=output_columns)

    if time_column not in data.columns or qmass_column not in data.columns:
        return pd.DataFrame(columns=output_columns)

    resolved_columns = {}

    for output_name, aliases in ZERO_FLOW_AVERAGE_ALIASES.items():
        actual_column = find_column(data.columns, aliases)
        if actual_column is not None:
            resolved_columns[output_name] = actual_column

    selected_columns = list(dict.fromkeys(
        [time_column, qmass_column] + list(resolved_columns.values())
    ))

    work = data.loc[:, selected_columns].copy()

    work[time_column] = pd.to_datetime(work[time_column], errors="coerce")
    work[qmass_column] = pd.to_numeric(work[qmass_column], errors="coerce")

    for column in resolved_columns.values():
        work[column] = pd.to_numeric(work[column], errors="coerce")

    work = (
        work.dropna(subset=[time_column])
        .sort_values(time_column)
        .drop_duplicates(subset=[time_column], keep="last")
        .reset_index(drop=True)
    )

    if work.empty:
        return pd.DataFrame(columns=output_columns)

    timestamps = work[time_column]
    qmass = work[qmass_column]

    interval_seconds = timestamps.diff().dt.total_seconds()
    gap_mask = interval_seconds.gt(gap_threshold_seconds).to_numpy()
    is_zero = qmass.eq(0).fillna(False).to_numpy()

    events = []
    n = len(work)

    # --------------------------------------------------------
    # 1. Data Gaps
    # --------------------------------------------------------
    for position in np.flatnonzero(gap_mask):
        if position == 0:
            continue

        gap_start = timestamps.iloc[position - 1]
        gap_end = timestamps.iloc[position]
        gap_duration = max(0, int((gap_end - gap_start).total_seconds()))

        events.append({
            "Event Type": "Data Gap",
            "Start Time": gap_start,
            "End Time": gap_end,
            "_DurationSeconds": gap_duration,
            "Entries": 0,
        })

    # --------------------------------------------------------
    # 2. Continuous Zero Flow runs
    # --------------------------------------------------------
    min_duration_seconds = min_duration_minutes * 60
    i = 0

    while i < n:
        if not is_zero[i]:
            i += 1
            continue

        start_pos = i
        end_pos = i

        while end_pos + 1 < n:
            next_pos = end_pos + 1

            if not is_zero[next_pos] or gap_mask[next_pos]:
                break

            end_pos = next_pos

        event = work.iloc[start_pos:end_pos + 1]
        entry_count = len(event)

        if entry_count >= min_records:
            start_time = timestamps.iloc[start_pos]
            last_zero_time = timestamps.iloc[end_pos]
            end_time = last_zero_time

            next_pos = end_pos + 1

            if next_pos < n and not gap_mask[next_pos]:
                next_qmass = qmass.iloc[next_pos]

                if pd.notna(next_qmass) and next_qmass > 0:
                    end_time = timestamps.iloc[next_pos]

            duration_seconds = max(
                0,
                int((end_time - start_time).total_seconds()),
            )

            record = {
                "Event Type": "Zero Flow",
                "Start Time": start_time,
                "End Time": end_time,
                "_DurationSeconds": duration_seconds,
                "Entries": entry_count,
            }

            if duration_seconds >= min_duration_seconds:
                if exclude_last_records > 0:
                    mean_data = event.iloc[:-exclude_last_records]
                else:
                    mean_data = event

                for output_name, actual_column in resolved_columns.items():
                    record[output_name] = (
                        np.nan if mean_data.empty
                        else mean_data[actual_column].mean()
                    )
            else:
                for output_name in average_columns:
                    record[output_name] = np.nan

            events.append(record)

        i = end_pos + 1

    if not events:
        return pd.DataFrame(columns=output_columns)

    result = pd.DataFrame(events)

    for column in output_columns:
        if column not in result.columns:
            result[column] = np.nan

    return result[output_columns].sort_values(
        "Start Time",
        ignore_index=True,
    )


# ============================================================
# PAGE INITIALIZATION
# ============================================================

st.title("Overview")

st.caption(
    "Summary statistics and gauges for the selected dataset "
    "and analysis period."
)

source_df = st.session_state.get("dataframe")

if source_df is None or not isinstance(source_df, pd.DataFrame):
    st.info(
        "No dataset found. Please import a logger file "
        "in the Data Import page first."
    )
    st.stop()

if source_df.empty:
    st.warning("The imported dataset is empty.")
    st.stop()


# ============================================================
# RESOLVE TIMESTAMP AND QmassTot COLUMNS
# ============================================================

time_column = find_column(
    source_df.columns,
    ["Time", "Timestamp", "DateTime", "Date Time", "Date"],
)

qmass_column = find_column(
    source_df.columns,
    ["QmassTot", "Q mass total", "Mass flow total"],
)

if time_column is None:
    st.error("Could not identify the time column.")
    st.stop()

if qmass_column is None:
    st.error("Could not identify the QmassTot column.")
    st.stop()


# ============================================================
# GAUGE DEFINITIONS
# ============================================================

gauge_definitions = [
    {"label": "P-Flow", "aliases": ["P-flow"], "percent": False},
    {"label": "T-Flow", "aliases": ["T-flow"], "percent": False},
    {"label": "dP", "aliases": ["dP"], "percent": False},
    {"label": "ACT GVF", "aliases": ["ActGVF"], "percent": True},
    {"label": "Act WLR", "aliases": ["ActWLR"], "percent": True},
    {"label": "LowAD%", "aliases": ["LowADpercent"], "percent": True},
    {"label": "Vel Mix", "aliases": ["Vel.mix"], "percent": False},
    {"label": "Density", "aliases": ["Density"], "percent": False},
    {
        "label": "Cond Layer Offset",
        "aliases": ["condLayerOffset"],
        "percent": False,
    },
    {
        "label": "Cap Layer Offset",
        "aliases": ["capLayerOffset"],
        "percent": False,
    },
]

resolved_gauges = []

for definition in gauge_definitions:
    column = find_column(source_df.columns, definition["aliases"])
    resolved_gauges.append({**definition, "column": column})

continuous_column = find_column(
    source_df.columns,
    [
        "Oil / Water continuous",
        "OilWaterContinuous",
        "Oil Water Continuous",
    ],
)

zero_flow_columns = []

for aliases in ZERO_FLOW_AVERAGE_ALIASES.values():
    column = find_column(source_df.columns, aliases)
    if column is not None:
        zero_flow_columns.append(column)


# ============================================================
# PREPARE REDUCED DATASET
# ============================================================

required_columns = [
    item["column"]
    for item in resolved_gauges
    if item["column"] is not None
]

if continuous_column is not None:
    required_columns.append(continuous_column)

required_columns.extend(zero_flow_columns)

df_all = prepare_data(
    source_df,
    time_column,
    qmass_column,
    required_columns,
)

if df_all.empty:
    st.warning("No valid timestamp records were found.")
    st.stop()


# ============================================================
# SHARED SIDEBAR CONTROLS
# ============================================================

controls = render_analysis_controls(
    dataframe=df_all,
    time_column=time_column,
    qmass_column=qmass_column,
)

# Apply the global time and QmassTot selections to the
# Overview gauges and selected-period statistics.
df = apply_analysis_filters(
    dataframe=df_all,
    time_column=time_column,
    qmass_column=qmass_column,
    controls=controls,
)

# Keep these compatibility keys for existing pages that may
# still read the older shared filter settings.
selected_filter = controls["qmass_filter"]

st.session_state["enable_filter"] = selected_filter != "All data"
st.session_state["filter_mode"] = selected_filter

# The complete-dataset calculations below intentionally use
# df_all, not df.


# ============================================================
# SELECTED DATA SUMMARY
# ============================================================

st.subheader("Selected Data Summary")

if df.empty:
    st.warning(
        "No records match the selected time range and QmassTot filter. "
        "Adjust the controls in the sidebar."
    )
else:
    start_time = df[time_column].iloc[0]
    end_time = df[time_column].iloc[-1]
    duration_seconds = (end_time - start_time).total_seconds()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Start Time",
            start_time.strftime("%Y-%m-%d %H:%M:%S"),
        )

    with col2:
        st.metric(
            "End Time",
            end_time.strftime("%Y-%m-%d %H:%M:%S"),
        )

    with col3:
        st.metric(
            "Selected Period Duration",
            format_duration(duration_seconds),
        )

    st.caption(
        f"Available data: "
        f"{df_all[time_column].iloc[0]:%Y-%m-%d %H:%M:%S} to "
        f"{df_all[time_column].iloc[-1]:%Y-%m-%d %H:%M:%S} | "
        f"Selected filter: {selected_filter} | "
        f"Records analyzed: {len(df):,}"
    )


# ============================================================
# PROCESS VARIABLE GAUGES
# ============================================================

st.subheader("Process Variable Gauges")

if df.empty:
    st.info("Gauges cannot be calculated because no records are selected.")
else:
    # 0 = Oil Continuous
    # 1 = Water Continuous
    water_continuous_pct = None

    if continuous_column is not None:
        category_percentages = calculate_category_time_percent(
            df,
            time_column,
            continuous_column,
        )
        water_continuous_pct = category_percentages.get(1, 0.0)

    operating_pct = calculate_operating_time_percent(
        df,
        time_column,
        qmass_column,
    )

    all_gauges = resolved_gauges + [
        {
            "label": "Water Continuous",
            "type": "percentage",
            "value": water_continuous_pct,
        },
        {
            "label": "Operating Time",
            "type": "percentage",
            "value": operating_pct,
        },
    ]

    for row_start in range(0, len(all_gauges), 4):
        gauge_row = all_gauges[row_start:row_start + 4]
        cols = st.columns(4)

        for widget_col, config in zip(cols, gauge_row):
            with widget_col:
                if config.get("type") == "percentage":
                    value = config["value"]

                    if value is None:
                        st.warning(
                            f"Cannot calculate {config['label']} "
                            "for the selected period."
                        )
                        continue

                    fig = make_gauge(
                        config["label"],
                        value,
                        percent=True,
                        suffix="%",
                    )

                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                        key=f"gauge_{normalize_name(config['label'])}",
                    )

                    if config["label"] == "Water Continuous":
                        st.caption(
                            f"{value:.1f}% of analyzed time with "
                            "Oil / Water continuous = 1."
                        )
                    elif config["label"] == "Operating Time":
                        st.caption(
                            f"{value:.1f}% of analyzed time with QmassTot > 0."
                        )

                    continue

                column = config["column"]

                if column is None:
                    st.warning(f"Column not found: {config['label']}")
                    continue

                values = df[column].dropna()

                if values.empty:
                    st.info(f"No valid data for {config['label']}.")
                    continue

                average_value = float(values.mean())

                fig = make_gauge(
                    config["label"],
                    average_value,
                    observed_values=values,
                    percent=config["percent"],
                    suffix="%" if config["percent"] else "",
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    key=f"gauge_{normalize_name(config['label'])}",
                )

                st.caption(
                    f"Average in selected period: {average_value:.3f}"
                )


# ============================================================
# ZERO FLOW EVENTS — COMPLETE DATASET
# ============================================================

st.subheader("Zero Flow Events — Complete Dataset")

st.caption(
    "This table always uses the complete imported dataset, "
    "independent of the sidebar Time Slicer and QmassTot filter. "
    "Zero Flow events with fewer than 30 entries are excluded. "
    "Averages are only calculated after 30 minutes without flow, "
    "excluding the last five zero-flow readings."
)

zero_events = get_zero_flow_events(
    df_all,
    time_column,
    qmass_column,
    gap_threshold_seconds=120,
    min_records=30,
    min_duration_minutes=30,
    exclude_last_records=5,
)

if zero_events.empty:
    st.info(
        "No qualifying Zero Flow periods or acquisition gaps were found."
    )
else:
    display_events = zero_events.copy()

    display_events["Duration"] = (
        display_events["_DurationSeconds"].apply(format_duration_hhmm)
    )

    display_events = display_events.drop(
        columns=["_DurationSeconds"],
        errors="ignore",
    )

    for column in ["Start Time", "End Time"]:
        if column in display_events.columns:
            display_events[column] = pd.to_datetime(
                display_events[column],
                errors="coerce",
            ).dt.strftime("%Y-%m-%d %H:%M:%S")

    average_columns = [
        column
        for column in display_events.columns
        if column.endswith(" Avg")
    ]

    for column in average_columns:
        display_events[column] = pd.to_numeric(
            display_events[column],
            errors="coerce",
        ).round(3)

    preferred_columns = [
        "Event Type",
        "Start Time",
        "End Time",
        "Duration",
        "Entries",
        "dP Avg",
        "CH1_PermCond Avg",
        "CH2_PermCond Avg",
        "CH3_PermCond Avg",
        "Density Avg",
        "GasDensity Avg",
        "OilDensity Avg",
        "WaterDensity Avg",
        "P-flow Avg",
        "T-flow Avg",
    ]

    ordered_columns = [
        column
        for column in preferred_columns
        if column in display_events.columns
    ]

    remaining_columns = [
        column
        for column in display_events.columns
        if column not in ordered_columns
    ]

    display_events = display_events[ordered_columns + remaining_columns]

    st.dataframe(
        display_events,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# OPERATING TIME — COMPLETE DATASET
# ============================================================

st.subheader("Operating Time — Complete Dataset")

full_operating_pct = calculate_operating_time_percent(
    df_all,
    time_column,
    qmass_column,
)

if full_operating_pct is None:
    st.info(
        "Not enough valid timestamps in the complete dataset "
        "to calculate Operating Time."
    )
else:
    st.metric(
        "Complete Dataset Operating Time",
        f"{full_operating_pct:.1f}%",
        "QmassTot > 0",
    )
