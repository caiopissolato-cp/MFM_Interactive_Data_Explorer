
import keyword
import operator
import uuid

import numpy as np
import pandas as pd
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
def hex_to_rgba(hex_color, alpha=0.20):
    """Convert #RRGGBB to rgba() for transparent chart fills."""
    hex_color = hex_color.lstrip("#")

    red = int(hex_color[0:2], 16)
    green = int(hex_color[2:4], 16)
    blue = int(hex_color[4:6], 16)

    return f"rgba({red}, {green}, {blue}, {alpha})"
# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.title("Custom Analysis")

st.caption(
    "Create custom variables and build independent charts "
    "for MPFM data analysis."
)


# ============================================================
# SESSION STATE
# ============================================================

if "custom_analysis_variables" not in st.session_state:
    st.session_state["custom_analysis_variables"] = {}

if "custom_analysis_charts" not in st.session_state:
    st.session_state["custom_analysis_charts"] = []


def add_chart():
    charts = st.session_state["custom_analysis_charts"]

    charts.append(
        {
            "id": str(uuid.uuid4())[:8],
            "title": f"Custom Chart {len(charts) + 1}",
            "type": "Line",
            "x": "",
            "y": [],
            "secondary_y_enabled": False,
            "secondary_y_variable": "",
            "filter_enabled": False,
            "filter_variable": "",
            "filter_operator": ">",
            "filter_value": 0.0,
            "smoothing": False,
            "window": 10,
        }
    )


# ============================================================
# LOAD SHARED DATAFRAME
# ============================================================

df_source = st.session_state.get("dataframe")

if df_source is None:
    df_source = st.session_state.get("df")

if not isinstance(df_source, pd.DataFrame):
    st.warning(
        "No dataset was found. Import the logger data "
        "from the Data Import page first."
    )
    st.stop()

if df_source.empty:
    st.warning("The imported dataset is empty.")
    st.stop()

df_source = df_source.copy()

time_candidates = [
    "Time",
    "DateTime",
    "Datetime",
    "Timestamp",
    "Date Time",
]

time_column = next(
    (
        column
        for column in time_candidates
        if column in df_source.columns
    ),
    None,
)

if time_column is not None:
    df_source[time_column] = pd.to_datetime(
        df_source[time_column],
        errors="coerce",
    )

    df_source = df_source.sort_values(
        time_column,
        kind="stable",
    )


# ============================================================
# APPLY SHARED ANALYSIS CONTROLS
# ============================================================

qmass_column = next(
    (
        column
        for column in ["QmassTot", "Qmass Tot", "Q Mass Total"]
        if column in df_source.columns
    ),
    None,
)

controls = render_analysis_controls(
    dataframe=df_source,
    time_column=time_column,
    qmass_column=qmass_column,
)

df_source = apply_analysis_filters(
    dataframe=df_source,
    time_column=time_column,
    qmass_column=qmass_column,
    controls=controls,
)

if df_source.empty:
    st.warning(
        "No data remains after applying the selected time range "
        "and QmassTot filter."
    )
    st.stop()

filter_mode = controls["qmass_filter"]

st.session_state["enable_filter"] = filter_mode != "All data"
st.session_state["filter_mode"] = filter_mode


# ============================================================
# CUSTOM VARIABLES
# ============================================================

st.header("1. Custom Variables")

st.caption(
    "Select two variables and a mathematical operation "
    "to create a new calculated variable."
)

saved_variables = st.session_state[
    "custom_analysis_variables"
]

original_numeric_columns = [
    column
    for column in df_source.columns
    if pd.api.types.is_numeric_dtype(df_source[column])
]

operand_options = list(
    dict.fromkeys(
        original_numeric_columns
        + list(saved_variables.keys())
    )
)

operation_options = {
    "Addition (+)": "+",
    "Subtraction (-)": "-",
    "Multiplication (×)": "*",
    "Division (÷)": "/",
}

if not operand_options:
    st.warning("No numeric variables are available.")

else:
    with st.container(border=True):

        with st.form(
            "custom_variable_form",
            clear_on_submit=False,
        ):

            variable_name = st.text_input(
                "New variable name",
                placeholder="Example: CH1_CH2_Difference",
                help=(
                    "Use letters, numbers and underscores. "
                    "The name must not start with a number."
                ),
            )

            operand_col1, operation_col, operand_col2 = st.columns(
                [2, 1, 2]
            )

            with operand_col1:
                variable_a = st.selectbox(
                    "First variable",
                    options=operand_options,
                    key="custom_operand_a",
                )

            with operation_col:
                selected_operation = st.selectbox(
                    "Operation",
                    options=list(operation_options.keys()),
                    key="custom_operation",
                )

            with operand_col2:
                variable_b = st.selectbox(
                    "Second variable",
                    options=operand_options,
                    key="custom_operand_b",
                )

            operation_symbol = operation_options[
                selected_operation
            ]

            st.caption(
                f"Calculation: {variable_a} "
                f"{operation_symbol} {variable_b}"
            )

            save_variable = st.form_submit_button(
                "Calculate and Save Variable",
                type="primary",
            )

    if save_variable:

        valid_name = (
            variable_name.isidentifier()
            and not keyword.iskeyword(variable_name)
            and not variable_name.startswith("__")
        )

        if not valid_name:
            st.error(
                "Enter a valid variable name, for example "
                "'CH1_CH2_Difference'."
            )

        elif (
            variable_name in df_source.columns
            and variable_name not in saved_variables
        ):
            st.error(
                "This name already exists in the imported dataset. "
                "Choose a different name."
            )

        else:
            try:
                if variable_a in saved_variables:
                    values_a = saved_variables[
                        variable_a
                    ]["values"].reindex(df_source.index)
                else:
                    values_a = pd.to_numeric(
                        df_source[variable_a],
                        errors="coerce",
                    )

                if variable_b in saved_variables:
                    values_b = saved_variables[
                        variable_b
                    ]["values"].reindex(df_source.index)
                else:
                    values_b = pd.to_numeric(
                        df_source[variable_b],
                        errors="coerce",
                    )

                values_a = pd.to_numeric(
                    values_a,
                    errors="coerce",
                )

                values_b = pd.to_numeric(
                    values_b,
                    errors="coerce",
                )

                if operation_symbol == "+":
                    result = operator.add(values_a, values_b)

                elif operation_symbol == "-":
                    result = operator.sub(values_a, values_b)

                elif operation_symbol == "*":
                    result = operator.mul(values_a, values_b)

                elif operation_symbol == "/":
                    denominator = values_b.replace(0, np.nan)
                    result = operator.truediv(
                        values_a,
                        denominator,
                    )

                else:
                    raise ValueError("Unsupported operation.")

                result = pd.to_numeric(
                    result,
                    errors="coerce",
                ).replace(
                    [np.inf, -np.inf],
                    np.nan,
                )

                if result.notna().sum() == 0:
                    st.error(
                        "The calculation did not produce valid values. "
                        "Check the selected variables."
                    )

                else:
                    formula_text = (
                        f"{variable_a} "
                        f"{operation_symbol} "
                        f"{variable_b}"
                    )

                    saved_variables[variable_name] = {
                        "values": result.copy(),
                        "formula": formula_text,
                    }

                    st.success(
                        f"Variable '{variable_name}' created successfully."
                    )

                    st.rerun()

            except Exception as error:
                st.error(
                    f"Could not calculate variable: {error}"
                )


# ============================================================
# DISPLAY AND DELETE SAVED VARIABLES
# ============================================================

saved_variables = st.session_state[
    "custom_analysis_variables"
]

if saved_variables:
    st.subheader("Saved Variables")

    for name, variable in list(saved_variables.items()):

        with st.container(border=True):

            info_col, delete_col = st.columns([5, 1])

            with info_col:
                st.markdown(f"**{name}**")
                st.code(variable["formula"])

                st.caption(
                    f"Valid values: "
                    f"{variable['values'].notna().sum():,}"
                )

            with delete_col:
                st.write("")

                if st.button(
                    "Delete",
                    key=f"delete_variable_{name}",
                ):
                    del st.session_state[
                        "custom_analysis_variables"
                    ][name]

                    st.rerun()


# ============================================================
# BUILD DATAFRAME INCLUDING CUSTOM VARIABLES
# ============================================================

df = df_source.copy()

for name, variable in st.session_state[
    "custom_analysis_variables"
].items():
    df[name] = variable["values"].reindex(df.index)

numeric_columns = [
    column
    for column in df.columns
    if pd.api.types.is_numeric_dtype(df[column])
]

x_options = list(df.columns)

if not numeric_columns:
    st.warning("No numeric variables are available for charting.")
    st.stop()


# ============================================================
# CHART BUILDER
# ============================================================

st.divider()

st.header("2. Chart Builder")

st.caption(
    "Create multiple independent charts. Each chart has its own "
    "variables, filters, moving average and axis settings."
)

if st.button(
    "＋ Add New Chart",
    type="primary",
    key="add_custom_chart",
):
    add_chart()
    st.rerun()

if not st.session_state["custom_analysis_charts"]:
    st.info(
        "No charts created yet. Click 'Add New Chart' to begin."
    )


# ============================================================
# RENDER CHARTS
# ============================================================

chart_types = [
    "Line",
    "Scatter",
    "Line + Markers",
    "Bar",
    "Area",
    "Histogram",
    "Box Plot",
]

filter_operators = [">", ">=", "<", "<=", "==", "!="]

filter_functions = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
}

for chart_index, chart in enumerate(
    st.session_state["custom_analysis_charts"]
):

    chart_id = chart["id"]

    # Backward compatibility for charts created before
    # secondary-axis settings were added.
    chart.setdefault("secondary_y_enabled", False)
    chart.setdefault("secondary_y_variable", "")

    with st.container(border=True):

        # ----------------------------------------------------
        # CHART TITLE AND MANAGEMENT
        # ----------------------------------------------------

        title_col, copy_col, delete_col = st.columns([6, 1, 1])

        with title_col:
            chart["title"] = st.text_input(
                "Chart title",
                value=chart.get("title", "Custom Chart"),
                key=f"title_{chart_id}",
            )

        with copy_col:
            st.write("")

            if st.button(
                "Copy",
                key=f"duplicate_{chart_id}",
                help="Duplicate this chart",
            ):
                new_chart = chart.copy()
                new_chart["id"] = str(uuid.uuid4())[:8]
                new_chart["title"] = chart["title"] + " (Copy)"
                new_chart["y"] = list(chart["y"])

                st.session_state[
                    "custom_analysis_charts"
                ].insert(chart_index + 1, new_chart)

                st.rerun()

        with delete_col:
            st.write("")

            if st.button(
                "Delete",
                key=f"delete_chart_{chart_id}",
            ):
                st.session_state[
                    "custom_analysis_charts"
                ] = [
                    item
                    for item in st.session_state[
                        "custom_analysis_charts"
                    ]
                    if item["id"] != chart_id
                ]

                st.rerun()

        # ----------------------------------------------------
        # CHART TYPE AND X AXIS
        # ----------------------------------------------------

        config_col1, config_col2 = st.columns(2)

        with config_col1:
            current_type = chart.get("type", "Line")

            chart["type"] = st.selectbox(
                "Chart type",
                options=chart_types,
                index=(
                    chart_types.index(current_type)
                    if current_type in chart_types
                    else 0
                ),
                key=f"type_{chart_id}",
            )

        with config_col2:
            current_x = chart.get("x", "")

            if current_x not in x_options:
                current_x = (
                    time_column
                    if time_column in x_options
                    else x_options[0]
                )

            chart["x"] = st.selectbox(
                "X-axis variable",
                options=x_options,
                index=x_options.index(current_x),
                key=f"x_{chart_id}",
            )

        # ----------------------------------------------------
        # PRIMARY Y VARIABLES
        # ----------------------------------------------------

        chart["y"] = st.multiselect(
            "Y-axis variables / series",
            options=numeric_columns,
            default=[
                variable
                for variable in chart.get("y", [])
                if variable in numeric_columns
            ],
            key=f"y_{chart_id}",
            help=(
                "Select the numeric variables to plot. "
                "A selected variable can be assigned to the secondary axis below."
            ),
        )

        # ----------------------------------------------------
        # SECONDARY Y AXIS CONTROLS
        # ----------------------------------------------------

        secondary_axis_supported = chart["type"] not in [
            "Histogram",
            "Box Plot",
        ]

        if secondary_axis_supported:

            chart["secondary_y_enabled"] = st.checkbox(
                "Enable secondary Y-axis",
                value=chart.get("secondary_y_enabled", False),
                key=f"secondary_y_enabled_{chart_id}",
                help=(
                    "Adds a second Y-axis on the right side of this chart. "
                    "The selected secondary variable uses its own scale."
                ),
            )

            if chart["secondary_y_enabled"]:

                current_secondary = chart.get(
                    "secondary_y_variable",
                    "",
                )

                if current_secondary not in numeric_columns:
                    current_secondary = (
                        chart["y"][0]
                        if chart["y"]
                        else numeric_columns[0]
                    )

                chart["secondary_y_variable"] = st.selectbox(
                    "Secondary Y-axis variable (right)",
                    options=numeric_columns,
                    index=numeric_columns.index(current_secondary),
                    key=f"secondary_y_variable_{chart_id}",
                    help=(
                        "This variable will be plotted on the right Y-axis. "
                        "All other selected series remain on the left Y-axis."
                    ),
                )

                st.caption(
                    "Left axis: remaining selected series | "
                    f"Right axis: {chart['secondary_y_variable']}"
                )

        else:
            chart["secondary_y_enabled"] = False

            st.caption(
                "The secondary Y-axis is not available for "
                "Histogram and Box Plot charts."
            )

        # ----------------------------------------------------
        # PER-CHART FILTER
        # ----------------------------------------------------

        chart["filter_enabled"] = st.checkbox(
            "Enable filter for this chart only",
            value=chart.get("filter_enabled", False),
            key=f"filter_enabled_{chart_id}",
        )

        chart_filter = None

        if chart["filter_enabled"]:

            filter_col1, filter_col2, filter_col3 = st.columns(3)

            with filter_col1:
                current_filter_variable = chart.get(
                    "filter_variable",
                    numeric_columns[0],
                )

                if current_filter_variable not in numeric_columns:
                    current_filter_variable = numeric_columns[0]

                chart["filter_variable"] = st.selectbox(
                    "Filter variable",
                    options=numeric_columns,
                    index=numeric_columns.index(
                        current_filter_variable
                    ),
                    key=f"filter_variable_{chart_id}",
                )

            with filter_col2:
                current_operator = chart.get("filter_operator", ">")

                chart["filter_operator"] = st.selectbox(
                    "Condition",
                    options=filter_operators,
                    index=filter_operators.index(current_operator),
                    key=f"filter_operator_{chart_id}",
                )

            with filter_col3:
                chart["filter_value"] = st.number_input(
                    "Threshold",
                    value=float(chart.get("filter_value", 0.0)),
                    key=f"filter_value_{chart_id}",
                )

            chart_filter = (
                chart["filter_variable"],
                chart["filter_operator"],
                chart["filter_value"],
            )

        # ----------------------------------------------------
        # MOVING AVERAGE CONTROLS
        # ----------------------------------------------------

        if chart["type"] in ["Line", "Line + Markers", "Area"]:

            smooth_col1, smooth_col2 = st.columns([1, 2])

            with smooth_col1:
                chart["smoothing"] = st.checkbox(
                    "Moving average",
                    value=chart.get("smoothing", False),
                    key=f"smoothing_{chart_id}",
                )

            with smooth_col2:
                chart["window"] = st.number_input(
                    "Window (samples)",
                    min_value=2,
                    max_value=1000,
                    value=int(chart.get("window", 10)),
                    step=1,
                    disabled=not chart["smoothing"],
                    key=f"window_{chart_id}",
                )

        # ----------------------------------------------------
        # VALIDATE SERIES SELECTION
        # ----------------------------------------------------

        if not chart["y"]:
            st.info("Select at least one Y-axis variable.")
            continue

        plot_df = df.copy()

        if chart_filter is not None:
            filter_variable, condition, threshold = chart_filter

            filter_series = pd.to_numeric(
                plot_df[filter_variable],
                errors="coerce",
            )

            valid_rows = filter_functions[condition](
                filter_series,
                threshold,
            )

            plot_df = plot_df.loc[valid_rows].copy()

        if plot_df.empty:
            st.warning(
                "No data remains after applying this chart's filter."
            )
            continue

        x_variable = chart["x"]

        secondary_enabled = (
            chart.get("secondary_y_enabled", False)
            and secondary_axis_supported
        )

        secondary_variable = (
            chart.get("secondary_y_variable", "")
            if secondary_enabled
            else None
        )

        # Build the full list of series used for processing.
        # The secondary variable is included even if it wasn't
        # selected in the primary Y-series multiselect.
        plot_variables = list(chart["y"])

        if (
            secondary_enabled
            and secondary_variable not in plot_variables
        ):
            plot_variables.append(secondary_variable)

        # ----------------------------------------------------
        # HISTOGRAM
        # ----------------------------------------------------

        if chart["type"] == "Histogram":

            fig = go.Figure()

            for variable in chart["y"]:

                values = pd.to_numeric(
                    plot_df[variable],
                    errors="coerce",
                ).dropna()

                fig.add_trace(
                    go.Histogram(
                        x=values,
                        name=variable,
                        opacity=0.65,
                    )
                )

            fig.update_layout(
                barmode="overlay",
                xaxis_title="Value",
                yaxis_title="Count",
            )

        # ----------------------------------------------------
        # BOX PLOT
        # ----------------------------------------------------

        elif chart["type"] == "Box Plot":

            fig = go.Figure()

            for variable in chart["y"]:

                values = pd.to_numeric(
                    plot_df[variable],
                    errors="coerce",
                ).dropna()

                fig.add_trace(
                    go.Box(
                        y=values,
                        name=variable,
                        boxpoints="outliers",
                    )
                )

            fig.update_layout(
                xaxis_title="Variable",
                yaxis_title="Value",
            )

        # ----------------------------------------------------
        # TIME SERIES GAP HANDLING
        # ----------------------------------------------------

        else:

            if (
                time_column is not None
                and x_variable == time_column
                and chart["type"] in [
                    "Line",
                    "Line + Markers",
                    "Area",
                ]
            ):

                plot_df = plot_df.sort_values(
                    time_column,
                    kind="stable",
                ).copy()

                time_diffs = (
                    plot_df[time_column]
                    .diff()
                    .dt.total_seconds()
                )

                gap_positions = np.flatnonzero(
                    time_diffs.gt(120).to_numpy()
                )

                if len(gap_positions) > 0:

                    original_plot_df = plot_df.copy()
                    expanded_parts = []
                    start_position = 0

                    for gap_position in gap_positions:

                        expanded_parts.append(
                            original_plot_df.iloc[
                                start_position:gap_position
                            ]
                        )

                        gap_row = original_plot_df.iloc[
                            [gap_position]
                        ].copy()

                        for variable in plot_variables:
                            gap_row[variable] = np.nan

                        expanded_parts.append(gap_row)

                        start_position = gap_position

                    expanded_parts.append(
                        original_plot_df.iloc[start_position:]
                    )

                    plot_df = pd.concat(
                        expanded_parts,
                        ignore_index=True,
                    )

            # ------------------------------------------------
            # MOVING AVERAGE
            # ------------------------------------------------

            if (
                chart.get("smoothing", False)
                and chart["type"] in [
                    "Line",
                    "Line + Markers",
                    "Area",
                ]
            ):

                for variable in plot_variables:

                    numeric_series = pd.to_numeric(
                        plot_df[variable],
                        errors="coerce",
                    )

                    if (
                        time_column is not None
                        and x_variable == time_column
                    ):

                        timestamps = pd.to_datetime(
                            plot_df[time_column],
                            errors="coerce",
                        )

                        time_diffs = (
                            timestamps.diff()
                            .dt.total_seconds()
                        )

                        new_segment = (
                            time_diffs.isna()
                            | time_diffs.gt(120)
                            | timestamps.isna()
                        )

                        segment_id = new_segment.cumsum()

                        smoothed = numeric_series.groupby(
                            segment_id
                        ).transform(
                            lambda series: series.rolling(
                                int(chart["window"]),
                                min_periods=1,
                                center=True,
                            ).mean()
                        )

                        plot_df[variable] = smoothed.where(
                            numeric_series.notna()
                        )

                    else:

                        plot_df[variable] = numeric_series.rolling(
                            int(chart["window"]),
                            min_periods=1,
                            center=True,
                        ).mean()

            # ------------------------------------------------
            # CREATE FIGURE WITH OPTIONAL SECONDARY Y AXIS
            # ------------------------------------------------

            if secondary_enabled:
                fig = make_subplots(
                    specs=[[{"secondary_y": True}]]
                )
            else:
                fig = go.Figure()

            # If the secondary variable is selected in the
            # primary series list, plot it only on the right.
            for variable in plot_variables:

                use_secondary_y = (
                    secondary_enabled
                    and variable == secondary_variable
                )

                if chart["type"] == "Scatter":

                    trace = go.Scatter(
                        x=plot_df[x_variable],
                        y=plot_df[variable],
                        mode="markers",
                        name=variable,
                    )

                elif chart["type"] == "Line + Markers":

                    trace = go.Scatter(
                        x=plot_df[x_variable],
                        y=plot_df[variable],
                        mode="lines+markers",
                        name=variable,
                        connectgaps=False,
                    )

                elif chart["type"] == "Area":

                    trace = go.Scatter(
                        x=plot_df[x_variable],
                        y=plot_df[variable],
                        mode="lines",
                        fill="tozeroy",
                        name=variable,
                        connectgaps=False,
                    )

                elif chart["type"] == "Bar":

                    trace = go.Bar(
                        x=plot_df[x_variable],
                        y=plot_df[variable],
                        name=variable,
                    )

                else:

                    trace = go.Scatter(
                        x=plot_df[x_variable],
                        y=plot_df[variable],
                        mode="lines",
                        name=variable,
                        connectgaps=False,
                    )

                if secondary_enabled:
                    fig.add_trace(
                        trace,
                        secondary_y=use_secondary_y,
                    )
                else:
                    fig.add_trace(trace)

            # ------------------------------------------------
            # AXIS TITLES
            # ------------------------------------------------

            primary_variables = [
                variable
                for variable in plot_variables
                if not (
                    secondary_enabled
                    and variable == secondary_variable
                )
            ]

            if primary_variables:
                primary_axis_title = ", ".join(primary_variables)
            else:
                primary_axis_title = "Value"

            fig.update_layout(
                xaxis_title=x_variable,
                hovermode="x unified",
                barmode="group",
            )

            if secondary_enabled:

                fig.update_yaxes(
                    title_text=primary_axis_title,
                    secondary_y=False,
                )

                fig.update_yaxes(
                    title_text=secondary_variable,
                    secondary_y=True,
                )

            else:
                fig.update_layout(
                    yaxis_title="Value",
                )

        # ----------------------------------------------------
        # FINAL CHART LAYOUT
        # ----------------------------------------------------

        fig.update_layout(
            title=chart["title"],
            height=500,
            legend_title_text="Variables",
            margin=dict(
                l=55,
                r=65 if secondary_enabled else 30,
                t=65,
                b=50,
            ),
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            key=f"plot_{chart_id}",
        )

        displayed_series = (
            plot_variables
            if chart["type"] not in ["Histogram", "Box Plot"]
            else chart["y"]
        )

        st.caption(
            f"Rows plotted: {len(plot_df):,} | "
            f"Series: {len(displayed_series)}"
            + (
                f" | Secondary Y-axis: {secondary_variable}"
                if secondary_enabled
                else ""
            )
        )


# ============================================================
# EXPORT DATA
# ============================================================

st.divider()

st.header("3. Export Data")

st.caption(
    "Download the current dataset, including saved custom variables."
)

csv_data = df.to_csv(
    index=False
).encode("utf-8-sig")

st.download_button(
    label="Download dataset as CSV",
    data=csv_data,
    file_name="custom_analysis_data.csv",
    mime="text/csv",
)
