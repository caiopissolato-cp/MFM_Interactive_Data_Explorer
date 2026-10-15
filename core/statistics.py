"""Statistics and correlation helpers."""

import pandas as pd

def correlation_matrix(df: pd.DataFrame, columns: list[str], method: str = "pearson") -> pd.DataFrame:
    if method not in {"pearson", "spearman"}:
        raise ValueError("method must be 'pearson' or 'spearman'")
    numeric = df[columns].apply(pd.to_numeric, errors="coerce")
    return numeric.corr(method=method)
