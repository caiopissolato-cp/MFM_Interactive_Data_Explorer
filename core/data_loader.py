"""Functions for importing source files."""

from io import BytesIO

import pandas as pd


def load_delimited_file(
    file_bytes: bytes,
    delimiter: str = "\t",
) -> pd.DataFrame:
    """Load a delimited text file from bytes using the fast C engine."""

    return pd.read_csv(
        BytesIO(file_bytes),
        sep=delimiter,
        engine="c",
        low_memory=True,
    )