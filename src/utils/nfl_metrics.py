# src/utils/nfl_metrics.py - Shared NFL metrics constants and utilities

from typing import Set, List

# NFL metrics where lower values are better (rest are higher-is-better)
LOWER_IS_BETTER_METRICS: Set[str] = {
    'turnovers_per_game', 
    'sacks_per_game', 
    'penalty_yards_per_game'
}

# Standard NFL metrics used for league averaging calculations
AVERAGING_METRICS: List[str] = [
    'avg_yards_per_play', 'turnovers_per_game', 'completion_pct', 'rush_ypc',
    'sacks_per_game', 'third_down_pct', 'success_rate', 'first_downs_per_game',
    'points_per_drive', 'redzone_td_pct', 'penalty_yards_per_game'
]

# Standard NFL metrics used for ranking calculations  
RANKING_METRICS: List[str] = [
    'avg_yards_per_play', 'rush_ypc', 'points_per_drive', 'success_rate',
    'third_down_pct', 'completion_pct', 'redzone_td_pct', 'first_downs_per_game',
    'turnovers_per_game', 'sacks_per_game', 'penalty_yards_per_game'
]

# All unique metrics (union of averaging and ranking metrics)
ALL_METRICS: Set[str] = set(AVERAGING_METRICS + RANKING_METRICS)