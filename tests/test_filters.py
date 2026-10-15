import pandas as pd
from core.data_filters import filter_numeric

def test_filter_numeric_greater_than():
    df = pd.DataFrame({"WLR": [20, 80, 90]})
    result = filter_numeric(df, "WLR", ">", 80)
    assert result["WLR"].tolist() == [90]
