"""Model 1900 profile. Validate aliases and limits against real exports."""

from .base import MeterProfile

class Model1900Profile(MeterProfile):
    name = "Model 1900"
    required_columns = ["P-flow", "T-flow"]
    optional_columns = [
        "Oil rate", "Water rate", "Gas rate", "ActGVF", "ActWLR",
        "dP", "Density", "GasDens", "Vel.mix",
        "AvgPermCond", "PermCond2", "GasPerm",
    ]
