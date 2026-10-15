import pytest
from core.unit_conversion import convert_value

def test_unit_conversion_is_not_silently_assumed():
    with pytest.raises(NotImplementedError):
        convert_value(1, "bar", "psi")
