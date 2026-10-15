"""Data validation and column detection helpers."""

import pandas as pd

def basic_data_summary(df: pd.DataFrame) -> dict:
    """Return basic metadata for a loaded dataframe."""
    return {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "column_names": [str(c) for c in df.columns],
        "duplicate_rows": int(df.duplicated().sum()),
    }
