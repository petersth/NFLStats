"""Season boundaries for historical franchise display names."""

import pytest

from src.utils.team_code_mapper import get_team_display_name


@pytest.mark.parametrize('year,expected', [
    (1999, 'Washington Redskins'),
    (2019, 'Washington Redskins'),
    (2020, 'Washington Football Team'),
    (2021, 'Washington Football Team'),
    (2022, 'Washington Commanders'),
    (2026, 'Washington Commanders'),
    (None, 'Washington Commanders'),
])
def test_washington_name_matches_season(year, expected):
    assert get_team_display_name('WAS', year) == expected


@pytest.mark.parametrize('team_code,year,expected', [
    ('LA', 2015, 'St. Louis Rams'),
    ('LA', 2016, 'Los Angeles Rams'),
    ('LV', 2019, 'Oakland Raiders'),
    ('LV', 2020, 'Las Vegas Raiders'),
    ('LAC', 2016, 'San Diego Chargers'),
    ('LAC', 2017, 'Los Angeles Chargers'),
    ('DET', 2020, 'Detroit Lions'),
])
def test_other_franchise_names_are_preserved(team_code, year, expected):
    assert get_team_display_name(team_code, year) == expected
