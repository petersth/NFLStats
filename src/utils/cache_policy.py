"""Freshness limits shared by source data and the analyses derived from it."""

from .season_utils import get_current_nfl_season_info

LIVE_SEASON_TTL_SECONDS = 10 * 60
HISTORICAL_SEASON_TTL_SECONDS = 30 * 60


def get_season_cache_ttl(season_year: int) -> int:
    """Return the source refresh interval for this season, in seconds."""
    season_info = get_current_nfl_season_info()
    is_live_season = (
        season_year == season_info["current_season"]
        and season_info["season_status"] in {"in_progress", "playoffs"}
    )
    return LIVE_SEASON_TTL_SECONDS if is_live_season else HISTORICAL_SEASON_TTL_SECONDS
