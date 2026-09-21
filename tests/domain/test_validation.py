from decimal import Decimal

import pytest

from src.domain.exceptions import DataValidationError
from src.domain.validation import NFLValidator, validate_positive_integer


@pytest.mark.parametrize('year', [2024, '2024', 2024.0, Decimal('2024')])
def test_season_accepts_exact_integer_representations(year):
    assert NFLValidator.validate_season_year(year) == 2024


@pytest.mark.parametrize('year', [2024.5, Decimal('2024.5'), float('nan'),
                                 float('inf'), float('-inf'), True])
def test_season_rejects_noninteger_or_nonfinite_values(year):
    with pytest.raises(DataValidationError, match='must be a valid integer'):
        NFLValidator.validate_season_year(year)


@pytest.mark.parametrize('value', [1.5, float('nan'), float('inf'), True])
def test_positive_integer_does_not_truncate_or_accept_nonfinite_values(value):
    with pytest.raises(DataValidationError, match='must be a valid integer'):
        validate_positive_integer(value, 'games')


def test_positive_integer_accepts_whole_valued_numbers_and_checks_sign():
    assert validate_positive_integer(2.0, 'games') == 2
    with pytest.raises(DataValidationError, match='must be positive'):
        validate_positive_integer(0, 'games')
