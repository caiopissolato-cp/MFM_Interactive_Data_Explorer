"""Base interface for meter profiles."""

class MeterProfile:
    name = "Base"
    required_columns = []
    optional_columns = []
    column_aliases = {}
    default_charts = []
    default_limits = {}
