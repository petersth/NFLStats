# src/utils/ranking_utils.py - Team ranking utility functions

from typing import Dict, List, Tuple
import logging
from ..domain.entities import PerformanceRank
from .nfl_metrics import LOWER_IS_BETTER_METRICS, RANKING_METRICS

logger = logging.getLogger(__name__)


def calculate_all_rankings(team_stats_dict: Dict) -> Dict[str, Dict]:
    """Calculate rankings for ALL teams at once from league statistics dictionary.
    
    Args:
        team_stats_dict: Dictionary mapping team abbreviations to their SeasonStats objects
        
    Returns:
        Dictionary mapping team abbreviations to their rankings dict
    """
    all_rankings = {}
    
    # Pre-calculate rankings for all metrics once
    metric_rankings = {}
    for metric in RANKING_METRICS:
        metric_rankings[metric] = _calculate_all_ranks_for_metric(team_stats_dict, metric)
    
    # Assign rankings to each team
    for team_abbr in team_stats_dict:
        team_rankings = {}
        for metric in RANKING_METRICS:
            if team_abbr in metric_rankings[metric]:
                team_rankings[metric] = metric_rankings[metric][team_abbr]
        all_rankings[team_abbr] = team_rankings
    
    return all_rankings


def calculate_team_rankings(team_abbr: str, team_stats_dict: Dict) -> Dict:
    """Calculate rankings for a specific team from league statistics dictionary.
    
    Implements NFL-standard ranking methodology with proper tie handling:
    - Uses 'min' ranking method: tied teams receive the same (best) rank
    - Handles directional metrics: higher values rank better for most metrics,
      lower values rank better for turnovers, sacks allowed, penalties
    - Provides 1-based ranking (1st = best, 32nd = worst in 32-team league)
    
    Args:
        team_abbr: Team abbreviation to calculate rankings for (e.g., 'KC', 'BUF')
        team_stats_dict: Dictionary mapping team abbreviations to SeasonStats objects
        
    Returns:
        Dictionary mapping metric names to integer rank positions (1-32 scale)
        Returns empty dict if team not found or no valid metrics
        
    Example:
        rankings = calculate_team_rankings('KC', all_team_stats)
        # Returns: {'avg_yards_per_play': 3, 'turnovers_per_game': 8, ...}
    """
    if team_abbr not in team_stats_dict:
        logger.warning(f"Team '{team_abbr}' not found in team stats dictionary")
        return {}
    
    rankings = {}
    team_stats = team_stats_dict[team_abbr]
    
    for metric in RANKING_METRICS:
        if hasattr(team_stats, metric):
            team_value = getattr(team_stats, metric)
            
            # Get all team values for this metric
            team_values = _extract_metric_values(team_stats_dict, metric)
            
            # Calculate rank for this team
            rank = _calculate_metric_rank(team_abbr, team_value, team_values, metric)
            if rank:
                rankings[metric] = rank
    
    return rankings


def _calculate_all_ranks_for_metric(team_stats_dict: Dict, metric: str) -> Dict[str, int]:
    """Calculate ranks for all teams for a single metric."""
    # Get all team values for this metric
    team_values = _extract_metric_values(team_stats_dict, metric)
    
    # Sort by value based on whether lower or higher is better
    if metric in LOWER_IS_BETTER_METRICS:
        ranked_teams = sorted(team_values, key=lambda x: x[1])
    else:
        ranked_teams = sorted(team_values, key=lambda x: x[1], reverse=True)
    
    # Assign ranks with tie handling
    ranks = {}
    current_rank = 1
    for i, (abbr, value) in enumerate(ranked_teams):
        if i > 0:
            prev_value = ranked_teams[i-1][1]
            if value != prev_value:
                current_rank = i + 1
        ranks[abbr] = current_rank
    
    return ranks


def _extract_metric_values(team_stats_dict: Dict, metric: str) -> List[Tuple[str, float]]:
    """Extract all team values for a specific metric."""
    team_values = []
    for abbr, stats in team_stats_dict.items():
        if hasattr(stats, metric):
            value = getattr(stats, metric)
            team_values.append((abbr, value))

    return team_values


def _calculate_metric_rank(team_abbr: str, team_value: float, 
                          team_values: List[Tuple[str, float]], metric: str) -> int:
    """Calculate the rank for a team's metric value with proper tie handling.
    
    Implements the 'min' ranking method used in sports statistics:
    - Teams with identical values receive the same rank (the best available rank)
    - Subsequent ranks are adjusted to account for tied positions
    - Example: If 3 teams tie for 2nd place, they all get rank 2, next team gets rank 5
    
    Args:
        team_abbr: Team abbreviation to find rank for
        team_value: The team's value for this metric
        team_values: List of (team_abbr, value) tuples for all teams
        metric: Metric name (determines sort direction via LOWER_IS_BETTER_METRICS)
        
    Returns:
        Integer rank position (1-based), or None if team not found
    """
    try:
        # Sort by value based on whether lower or higher is better
        if metric in LOWER_IS_BETTER_METRICS:
            # Lower is better for turnovers, sacks allowed, penalty yards
            ranked_teams = sorted(team_values, key=lambda x: x[1])
        else:
            # Higher is better for most offensive metrics (yards/play, completion %, etc.)
            ranked_teams = sorted(team_values, key=lambda x: x[1], reverse=True)
        
        # Handle ties using 'min' method - all tied values get the same (minimum) rank
        current_rank = 1
        for i, (abbr, value) in enumerate(ranked_teams):
            if i > 0:
                prev_value = ranked_teams[i-1][1]
                # If value changed from previous, update rank to position + 1
                if value != prev_value:
                    current_rank = i + 1
            
            if abbr == team_abbr:
                return current_rank
        
        return None
        
    except Exception as e:
        logger.error(f"Error calculating rank for {team_abbr} {metric}: {e}")
        return None


def calculate_performance_rank(rank: int, total_teams: int) -> PerformanceRank:
    """Convert a raw rank to a PerformanceRank object with context."""
    # Calculate percentile (higher percentile = better performance)
    percentile = ((total_teams - rank + 1) / total_teams) * 100
    
    # Determine description and color based on rank
    if rank == 1:
        description = "Best in NFL"
        color = "gold"
        percentile_str = "1st"
    elif rank <= 3:
        description = "Elite"
        color = "green"
        percentile_str = f"Top {int(percentile)}%"
    elif rank <= 8:
        description = "Excellent"
        color = "lightgreen"
        percentile_str = f"Top {int(percentile)}%"
    elif rank <= 16:
        description = "Above Average"
        color = "yellow"
        percentile_str = f"Top {int(percentile)}%"
    elif rank <= 24:
        description = "Below Average"
        color = "orange"
        percentile_str = f"Bottom {int(100 - percentile)}%"
    else:
        description = "Poor"
        color = "red"
        percentile_str = f"Bottom {int(100 - percentile)}%"
    
    return PerformanceRank(
        rank=rank,
        total_teams=total_teams,
        description=description,
        percentile=percentile_str,
        color=color
    )