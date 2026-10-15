"""Functions for importing source files will live here."""

from io import BytesIO
import pandas as pd

def load_delimited_file(file_bytes: bytes, delimiter: str = "\\t") -> pd.DataFrame:
    """Load a delimited text file from bytes."""
    return pd.read_csv(BytesIO(file_bytes), sep=delimiter, engine="python")
