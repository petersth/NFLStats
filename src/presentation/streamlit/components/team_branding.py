"""Bundled team marks for headers, with neutral historical fallbacks."""

import base64
from functools import lru_cache
from pathlib import Path
from typing import Optional

from ....config.nfl_constants import TEAM_DATA


_LOGO_DIRECTORY = Path(__file__).resolve().parent.parent / "assets" / "team_logos"
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# Avoid showing a modern city/name-specific mark for an earlier identity.
# Other logos identify the franchise, rather than reproducing every redesign.
_FIRST_LOGO_SEASON = {"LA": 2020, "LAC": 2020, "TEN": 2026, "WAS": 2022}


@lru_cache(maxsize=32)
def _load_logo(team_abbr: str) -> Optional[str]:
    """Read a known, local PNG once; a missing asset must not break analysis."""
    try:
        image = (_LOGO_DIRECTORY / f"{team_abbr}.png").read_bytes()
    except OSError:
        return None
    if not image.startswith(_PNG_SIGNATURE):
        return None
    return "data:image/png;base64," + base64.b64encode(image).decode("ascii")


def get_team_logo_data_uri(team_abbr: str, season_year: Optional[int] = None) -> Optional[str]:
    """Return a self-contained logo, or None when a neutral mark is needed.

    Logos never require browser network access. Only canonical team codes may
    resolve to files; unknown values are handled by the caller's fallback.
    """
    team_abbr = str(team_abbr).upper()
    if team_abbr not in TEAM_DATA:
        return None
    first_season = _FIRST_LOGO_SEASON.get(team_abbr)
    if season_year is not None and first_season is not None and season_year < first_season:
        return None
    return _load_logo(team_abbr)


def get_team_mark_abbreviation(team_abbr: str, season_year: Optional[int] = None) -> str:
    """Return plain text for a neutral mark, respecting historical cities."""
    team_abbr = str(team_abbr).upper()
    if team_abbr not in TEAM_DATA:
        return "?"
    if season_year is not None:
        if team_abbr == "LA" and 1995 <= season_year <= 2015:
            return "STL"
        if team_abbr == "LAC" and season_year <= 2016:
            return "SD"
        if team_abbr == "LV" and 1995 <= season_year <= 2019:
            return "OAK"
    return team_abbr
