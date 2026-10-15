"""Model 2600 profile. Validate aliases and limits against real exports."""

from .base import MeterProfile

class Model2600Profile(MeterProfile):
    name = "Model 2600"
    required_columns = ["P-flow", "T-flow"]
    optional_columns = [
        "Oil rate", "Water rate", "Gas rate", "ActGVF", "ActWLR",
        "dP", "Density", "GasDens", "Vel.mix",
        "CH1_PermCond", "CH2_PermCond",
    ]
