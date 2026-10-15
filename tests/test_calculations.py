import pandas as pd
from core.calculations import calculate_binary

def test_division_by_zero_returns_missing():
    df = pd.DataFrame({"A": [10.0, 20.0], "B": [2.0, 0.0]})
    result = calculate_binary(df, "A", "/", "B")
    assert result.iloc[0] == 5.0
    assert pd.isna(result.iloc[1])
