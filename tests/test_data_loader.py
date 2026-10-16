
from core.data_loader import load_delimited_file


def test_load_tab_delimited_file():
    raw = b"Time\tP-flow\n2026-01-01 00:00:00\t10.5\n"

    df = load_delimited_file(raw, delimiter="\t")

    assert list(df.columns) == ["Time", "P-flow"]
    assert len(df) == 1
    assert df.iloc[0]["P-flow"] == 10.5
