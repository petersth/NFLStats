# src/utils/league_stats_utils.py - League statistics utility functions

from typing import Dict, List
from math import fsum
from ..domain.entities import SeasonStats
from .nfl_metrics import AVERAGING_METRICS


def extract_stats_for_averaging(season_stats: SeasonStats) -> Dict:
    """Extract stats from SeasonStats object for league averaging calculations.
    
    Args:
        season_stats: SeasonStats object containing team's season statistics
        
    Returns:
        Dictionary with metrics needed for league average calculations
    """
    return {
        'games_played': season_stats.games_played,
        'avg_yards_per_play': season_stats.avg_yards_per_play,
        'turnovers_per_game': season_stats.turnovers_per_game,
        'completion_pct': season_stats.completion_pct,
        'rush_ypc': season_stats.rush_ypc,
        'sacks_per_game': season_stats.sacks_per_game,
        'third_down_pct': season_stats.third_down_pct,
        'success_rate': season_stats.success_rate,
        'first_downs_per_game': season_stats.first_downs_per_game,
        'points_per_drive': season_stats.points_per_drive,
        'redzone_td_pct': season_stats.redzone_td_pct,
        'penalty_yards_per_game': season_stats.penalty_yards_per_game,
        'toer': season_stats.toer,
        'toer_allowed': season_stats.toer_allowed,
    }


def calculate_league_averages(all_stats_data: List[Dict]) -> Dict:
    """Calculate league averages from list of team stats dictionaries.

    TOER and TOER allowed weight each team by games played, so every team-game
    contributes equally. Other metrics retain their mean-of-teams benchmarks.
    
    Args:
        all_stats_data: List of stat dictionaries from extract_stats_for_averaging
        
    Returns:
        Dictionary with league average values for each metric
    """
    if not all_stats_data:
        return {}
    
    league_averages = {}
    
    for metric in AVERAGING_METRICS:
        if metric in ('toer', 'toer_allowed'):
            played_stats = [
                stats for stats in all_stats_data
                if metric in stats and stats['games_played'] > 0
            ]
            total_games = sum(stats['games_played'] for stats in played_stats)
            league_averages[metric] = (
                fsum(stats[metric] * stats['games_played'] for stats in played_stats) / total_games
                if total_games else 0.0
            )
            continue
        values = [stats.get(metric, 0) for stats in all_stats_data if metric in stats]
        if values:
            league_averages[metric] = sum(values) / len(values)
        else:
            league_averages[metric] = 0.0
    
    return league_averages
