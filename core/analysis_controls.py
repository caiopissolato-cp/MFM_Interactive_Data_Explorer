
from datetime import date, datetime, time

import pandas as pd
import streamlit as st


# ============================================================
# SHARED ANALYSIS CONTROLS
# ============================================================

START_DATE_KEY = "global_analysis_start_date"
START_TIME_KEY = "global_analysis_start_time"
END_DATE_KEY = "global_analysis_end_date"
END_TIME_KEY = "global_analysis_end_time"

QMASS_FILTER_KEY = "global_analysis_qmass_filter"
MA_ENABLED_KEY = "global_analysis_ma_enabled"
MA_WINDOW_KEY = "global_analysis_ma_window"

DATA_SIGNATURE_KEY = "global_analysis_data_signature"

QMASS_FILTER_OPTIONS = [
    "All data",
    "QmassTot > 0",
    "QmassTot == 0",
]

MA_WINDOW_OPTIONS = [5, 10, 30, 60]


def render_analysis_controls(
    dataframe: pd.DataFrame,
    time_column: str,
    qmass_column: str | None,
) -> dict:
    """
    Render shared controls in the sidebar.

    Returns:
        start_datetime: selected start timestamp
        end_datetime: selected end timestamp
        qmass_filter: selected QmassTot filter
        ma_enabled: whether moving average is enabled
        ma_window: moving average window in samples
    """

    if dataframe is None or dataframe.empty:
        return {
            "start_datetime": None,
            "end_datetime": None,
            "qmass_filter": "All data",
            "ma_enabled": False,
            "ma_window": 5,
        }

    if time_column not in dataframe.columns:
        return {
            "start_datetime": None,
            "end_datetime": None,
            "qmass_filter": "All data",
            "ma_enabled": False,
            "ma_window": 5,
        }

    timestamps = pd.to_datetime(
        dataframe[time_column],
        errors="coerce",
    ).dropna()

    if timestamps.empty:
        return {
            "start_datetime": None,
            "end_datetime": None,
            "qmass_filter": "All data",
            "ma_enabled": False,
            "ma_window": 5,
        }

    min_timestamp = timestamps.min()
    max_timestamp = timestamps.max()

    min_date = min_timestamp.date()
    max_date = max_timestamp.date()

    min_time = min_timestamp.time().replace(microsecond=0)
    max_time = max_timestamp.time().replace(microsecond=0)

    # Detect when a different dataset has been loaded.
    signature = (
        str(time_column),
        len(dataframe),
        str(min_timestamp),
        str(max_timestamp),
    )

    previous_signature = st.session_state.get(DATA_SIGNATURE_KEY)

    if previous_signature != signature:
        st.session_state[DATA_SIGNATURE_KEY] = signature

        # Reset the date/time controls to the new dataset boundaries.
        st.session_state[START_DATE_KEY] = min_date
        st.session_state[START_TIME_KEY] = min_time
        st.session_state[END_DATE_KEY] = max_date
        st.session_state[END_TIME_KEY] = max_time

        # Preserve the user's filter and moving-average preferences
        # when a new dataset is loaded.
        if QMASS_FILTER_KEY not in st.session_state:
            st.session_state[QMASS_FILTER_KEY] = "All data"

        if MA_ENABLED_KEY not in st.session_state:
            st.session_state[MA_ENABLED_KEY] = False

        if MA_WINDOW_KEY not in st.session_state:
            st.session_state[MA_WINDOW_KEY] = 10

    # Ensure stored dates/times remain valid for the current dataset.
    if START_DATE_KEY not in st.session_state:
        st.session_state[START_DATE_KEY] = min_date

    if START_TIME_KEY not in st.session_state:
        st.session_state[START_TIME_KEY] = min_time

    if END_DATE_KEY not in st.session_state:
        st.session_state[END_DATE_KEY] = max_date

    if END_TIME_KEY not in st.session_state:
        st.session_state[END_TIME_KEY] = max_time

    if QMASS_FILTER_KEY not in st.session_state:
        st.session_state[QMASS_FILTER_KEY] = "All data"

    if MA_ENABLED_KEY not in st.session_state:
        st.session_state[MA_ENABLED_KEY] = False

    if MA_WINDOW_KEY not in st.session_state:
        st.session_state[MA_WINDOW_KEY] = 10

    # Clamp dates if the current dataset has different boundaries.
    st.session_state[START_DATE_KEY] = min(
        max(st.session_state[START_DATE_KEY], min_date),
        max_date,
    )

    st.session_state[END_DATE_KEY] = min(
        max(st.session_state[END_DATE_KEY], min_date),
        max_date,
    )

    # ========================================================
    # SIDEBAR UI
    # ========================================================

    with st.sidebar:
        st.divider()
        st.subheader("Analysis Controls")

        st.caption("Time Slicer")

        start_date = st.date_input(
            "Start date",
            min_value=min_date,
            max_value=max_date,
            key=START_DATE_KEY,
        )

        start_time = st.time_input(
            "Start time",
            key=START_TIME_KEY,
        )

        end_date = st.date_input(
            "End date",
            min_value=min_date,
            max_value=max_date,
            key=END_DATE_KEY,
        )

        end_time = st.time_input(
            "End time",
            key=END_TIME_KEY,
        )

        st.caption("Mass Flow Filter")

        qmass_filter = st.selectbox(
            "QmassTot filter",
            options=QMASS_FILTER_OPTIONS,
            key=QMASS_FILTER_KEY,
        )

        st.caption("Moving Average")

        ma_enabled = st.checkbox(
            "Enable moving average",
            key=MA_ENABLED_KEY,
        )

        ma_window = st.selectbox(
            "Window (samples)",
            options=MA_WINDOW_OPTIONS,
            key=MA_WINDOW_KEY,
            disabled=not ma_enabled,
        )

    # ========================================================
    # VALIDATE TIME RANGE
    # ========================================================

    start_datetime = datetime.combine(start_date, start_time)
    end_datetime = datetime.combine(end_date, end_time)

    if start_datetime > end_datetime:
        st.sidebar.warning(
            "Start date/time is after End date/time. "
            "The selected time range will return no data."
        )

    return {
        "start_datetime": start_datetime,
        "end_datetime": end_datetime,
        "qmass_filter": qmass_filter,
        "ma_enabled": ma_enabled,
        "ma_window": ma_window,
    }


def apply_analysis_filters(
    dataframe: pd.DataFrame,
    time_column: str,
    qmass_column: str | None,
    controls: dict,
) -> pd.DataFrame:
    """
    Apply the shared time and QmassTot filters.

    This function does not modify the original dataframe.
    """

    if dataframe is None or dataframe.empty:
        return dataframe.copy() if dataframe is not None else pd.DataFrame()

    filtered = dataframe

    start_datetime = controls.get("start_datetime")
    end_datetime = controls.get("end_datetime")

    if time_column in filtered.columns:
        timestamps = pd.to_datetime(
            filtered[time_column],
            errors="coerce",
        )

        mask = timestamps.notna()

        if start_datetime is not None:
            mask &= timestamps >= pd.Timestamp(start_datetime)

        if end_datetime is not None:
            mask &= timestamps <= pd.Timestamp(end_datetime)

        filtered = filtered.loc[mask].copy()

    qmass_filter = controls.get("qmass_filter", "All data")

    if qmass_column and qmass_column in filtered.columns:
        qmass = pd.to_numeric(
            filtered[qmass_column],
            errors="coerce",
        )

        if qmass_filter == "QmassTot > 0":
            filtered = filtered.loc[qmass > 0].copy()

        elif qmass_filter == "QmassTot == 0":
            filtered = filtered.loc[qmass == 0].copy()

    return filtered


def apply_moving_average(
    series: pd.Series,
    controls: dict,
) -> pd.Series:
    """
    Apply the shared moving-average settings to a numeric series.

    Call this only for charts that should use smoothing.
    """

    if not controls.get("ma_enabled", False):
        return series

    window = int(controls.get("ma_window", 10))

    numeric_series = pd.to_numeric(series, errors="coerce")

    return numeric_series.rolling(
        window=window,
        min_periods=1,
    ).mean()
