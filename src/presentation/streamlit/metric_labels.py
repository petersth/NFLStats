"""Consistent metric names for the dashboard, independent of export schemas."""

_LABELS = {
    "avg_yards_per_play": "Yards / play",
    "turnovers_per_game": "Turnovers",
    "completion_pct": "Completion rate",
    "rush_ypc": "Rush yards / carry",
    "sacks_per_game": "Sacks allowed",
    "third_down_pct": "3rd down rate",
    "success_rate": "Success rate",
    "first_downs_per_game": "1st downs",
    "points_per_drive": "Points / drive",
    "redzone_td_pct": "Red zone TD rate",
    "penalty_yards_per_game": "Penalty yards",
    "toer": "TOER",
    "toer_allowed": "TOER allowed",
}

_PER_GAME_METRICS = {
    "turnovers_per_game",
    "sacks_per_game",
    "first_downs_per_game",
    "penalty_yards_per_game",
}


def get_metric_label(metric_key: str, *, season: bool = False) -> str:
    """Distinguish season per-game averages from the same counts in one game."""
    label = _LABELS[metric_key]
    if season and metric_key in _PER_GAME_METRICS:
        return f"{label} / game"
    return label
