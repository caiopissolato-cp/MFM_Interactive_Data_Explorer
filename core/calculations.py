"""Custom engineering calculations."""

import numpy as np
import pandas as pd

def calculate_binary(
    df: pd.DataFrame,
    column_a: str,
    operator: str,
    column_b: str,
) -> pd.Series:
    """Calculate a basic operation between two numeric columns."""
    a = pd.to_numeric(df[column_a], errors="coerce")
    b = pd.to_numeric(df[column_b], errors="coerce")

    if operator == "+":
        return a + b
    if operator == "-":
        return a - b
    if operator == "*":
        return a * b
    if operator == "/":
        return a / b.replace(0, np.nan)
    raise ValueError(f"Unsupported operator: {operator}")
