
# core/chart_colors.py
"""
Central color palette for the MFM Interactive Data Explorer.

ISA-5.1 provides conventions for instrument identification and
representation. It does not prescribe a universal color for every
variable in a trend chart.

The palette below is an application-wide convention, not an official
ISA-mandated color scheme.
"""

import re


# ============================================================
# VARIABLE COLORS
# ============================================================

VARIABLE_COLORS = {
    # --------------------------------------------------------
    # FLOW RATES
    # --------------------------------------------------------
    "oilrate": "#374151",       # Dark gray
    "waterrate": "#0284C7",     # Blue
    "gasrate": "#D97706",       # Amber/orange

    # --------------------------------------------------------
    # FLOW CONDITIONS
    # --------------------------------------------------------
    "actgvf": "#7C3AED",        # Purple
    "gvf": "#7C3AED",
    "actwlr": "#0D9488",        # Teal
    "wlr": "#0D9488",

    # --------------------------------------------------------
    # PRESSURE, TEMPERATURE AND DENSITY
    # --------------------------------------------------------
    "dp": "#DC2626",            # Red
    "differentialpressure": "#DC2626",
    "density": "#65A30D",       # Green
    "pflow": "#2563EB",         # Blue
    "tflow": "#EA580C",         # Orange

    # --------------------------------------------------------
    # ELECTRICAL / SENSOR VARIABLES
    # --------------------------------------------------------
    "ch1": "#9333EA",            # Purple
    "ch2": "#0891B2",            # Cyan
    "ch3": "#64748B",            # Slate gray
    "gasperm": "#A16207",        # Brown/amber
    "permcond": "#A16207",

    # --------------------------------------------------------
    # OTHER MPFM VARIABLES
    # --------------------------------------------------------
    "lowad": "#DB2777",          # Pink
    "lowadpercent": "#DB2777",
    "velmix": "#4F46E5",         # Indigo
    "mixvelocity": "#4F46E5",
    "condlayeroffset": "#0F766E",
    "caplayeroffset": "#CA8A04",
    "watercontinuous": "#0284C7",
    "oilcontinuous": "#374151",
    "operatingtime": "#16A34A",
    "qmasstot": "#475569",
}


# ============================================================
# NAME NORMALIZATION AND ALIASES
# ============================================================

def normalize_variable_name(variable):
    """
    Normalize variable names so that labels such as
    'P-Flow', 'P Flow' and 'p_flow' resolve consistently.
    """
    return re.sub(r"[^a-z0-9]", "", str(variable).lower())


# Optional aliases for common column and chart labels.
VARIABLE_ALIASES = {
    "pressureflow": "pflow",
    "flowpressure": "pflow",
    "temperatureflow": "tflow",
    "flowtemperature": "tflow",
    "differentialp": "dp",
    "actgvfpercent": "actgvf",
    "actwlrpercent": "actwlr",
    "gaspermeability": "gasperm",
    "velocitymix": "velmix",
    "qmasstotal": "qmasstot",
    "watercontinuity": "watercontinuous",
    "oilcontinuity": "oilcontinuous",
}


def get_variable_color(variable, default="#64748B"):
    """
    Return the consistent color for a variable.

    Parameters
    ----------
    variable : str
        Variable name or chart label.
    default : str
        Fallback color when no mapping exists.
    """
    normalized = normalize_variable_name(variable)
    canonical = VARIABLE_ALIASES.get(normalized, normalized)

    return VARIABLE_COLORS.get(canonical, default)


# ============================================================
# LINE STYLE HELPERS
# ============================================================

def get_variable_line_style(variable, moving_average=False):
    """
    Return Plotly-compatible line settings.

    The moving average keeps the variable's color but uses a
    dashed line, making it distinguishable from raw data.
    """
    color = get_variable_color(variable)

    if moving_average:
        return {
            "color": color,
            "dash": "dash",
            "width": 2,
        }

    return {
        "color": color,
        "dash": "solid",
        "width": 1.5,
    }
