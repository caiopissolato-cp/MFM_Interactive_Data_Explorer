"""Reusable row filtering functions."""

import pandas as pd

def filter_numeric(
    df: pd.DataFrame,
    column: str,
    condition: str,
    value: float,
) -> pd.DataFrame:
    """Return only rows satisfying a numeric condition."""
    if column not in df.columns:
        raise KeyError(f"Column not found: {column}")

    series = pd.to_numeric(df[column], errors="coerce")
    operations = {
        ">": series > value,
        "<": series < value,
        "==": series == value,
        ">=": series >= value,
        "<=": series <= value,
        "!=": series != value,
    }
    if condition not in operations:
        raise ValueError(f"Unsupported condition: {condition}")
    return df.loc[operations[condition]].copy()
