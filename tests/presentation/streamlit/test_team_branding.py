"""Local team marks must cover the league without mislabeling past identities."""

import base64
import hashlib
import json

import pytest

from src.config.nfl_constants import TEAM_DATA
from src.presentation.streamlit.components import team_branding


def test_all_current_teams_have_bundled_pngs_with_recorded_provenance():
    sources = json.loads((team_branding._LOGO_DIRECTORY / "sources.json").read_text())
    assert set(sources) == {f"{abbr}.png" for abbr in TEAM_DATA}
    for abbr in TEAM_DATA:
        uri = team_branding.get_team_logo_data_uri(abbr, 2026)
        assert uri is not None, abbr
        mime, encoded = uri.split(",", 1)
        image = base64.b64decode(encoded, validate=True)
        assert mime == "data:image/png;base64"
        assert image.startswith(b"\x89PNG\r\n\x1a\n")
        assert hashlib.sha256(image).hexdigest() == sources[f"{abbr}.png"]["sha256"]


@pytest.mark.parametrize("abbr,year,mark", [
    ("LA", 1999, "STL"), ("LA", 2015, "STL"),
    ("LA", 2016, "LA"), ("LA", 2019, "LA"),
    ("LAC", 2016, "SD"), ("LAC", 2017, "LAC"),
    ("LAC", 2019, "LAC"), ("WAS", 2019, "WAS"),
    ("WAS", 2020, "WAS"), ("WAS", 2021, "WAS"),
    ("TEN", 1999, "TEN"), ("TEN", 2025, "TEN"),
])
def test_historical_identities_use_neutral_marks(abbr, year, mark):
    assert team_branding.get_team_logo_data_uri(abbr, year) is None
    assert team_branding.get_team_mark_abbreviation(abbr, year) == mark


@pytest.mark.parametrize("abbr,year", [
    ("LA", 2020), ("LAC", 2020), ("WAS", 2022), ("TEN", 2026),
])
def test_current_mark_starts_at_the_identity_boundary(abbr, year):
    assert team_branding.get_team_logo_data_uri(abbr, year) is not None


def test_raiders_shield_is_shared_across_relocation():
    assert team_branding.get_team_logo_data_uri("LV", 2019) == team_branding.get_team_logo_data_uri("LV", 2020)
    assert team_branding.get_team_mark_abbreviation("LV", 2019) == "OAK"
    assert team_branding.get_team_mark_abbreviation("LV", 2020) == "LV"


def test_unknown_codes_cannot_resolve_arbitrary_files():
    for abbr in ("../../../../secret", '<img src=x onerror="alert(1)">', "XYZ", None):
        assert team_branding.get_team_logo_data_uri(abbr, 2026) is None
        assert team_branding.get_team_mark_abbreviation(abbr, 2026) == "?"


def test_missing_or_invalid_asset_uses_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(team_branding, "_LOGO_DIRECTORY", tmp_path)
    team_branding._load_logo.cache_clear()
    try:
        assert team_branding.get_team_logo_data_uri("ARI", 2026) is None
        (tmp_path / "DET.png").write_text("not an image")
        assert team_branding.get_team_logo_data_uri("DET", 2026) is None
    finally:
        team_branding._load_logo.cache_clear()
