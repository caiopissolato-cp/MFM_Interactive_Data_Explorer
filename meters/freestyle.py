"""Generic profile for files without a recognized meter model."""

from .base import MeterProfile

class FreestyleProfile(MeterProfile):
    name = "Freestyle"
    required_columns = []
    optional_columns = []
