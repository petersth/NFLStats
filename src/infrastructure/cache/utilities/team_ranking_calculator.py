# src/infrastructure/cache/utilities/team_ranking_calculator.py

from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class TeamRankingCalculator:
    """Shared utility for calculating team rankings from league statistics."""
    
    # NFL metrics where lower values are better (rest are higher-is-better)
    LOWER_IS_BETTER_METRICS = {
        'turnovers_per_game', 
        'sacks_per_game', 
        'penalty_yards_per_game'
    }
    
    # Standard NFL metrics used across all ranking calculations
    RANKING_METRICS = [
        'avg_yards_per_play', 'rush_ypc', 'points_per_drive', 'success_rate',
        'third_down_pct', 'completion_pct', 'redzone_td_pct', 'first_downs_per_game',
        'turnovers_per_game', 'sacks_per_game', 'penalty_yards_per_game'
    ]
    
    @classmethod
    def calculate_all_rankings(cls, team_stats_dict: Dict) -> Dict[str, Dict]:
        """Calculate rankings for ALL teams at once from league statistics dictionary.
        
        Args:
            team_stats_dict: Dictionary mapping team abbreviations to their SeasonStats objects
            
        Returns:
            Dictionary mapping team abbreviations to their rankings dict
        """
        all_rankings = {}
        
        # Pre-calculate rankings for all metrics once
        metric_rankings = {}
        for metric in cls.RANKING_METRICS:
            metric_rankings[metric] = cls._calculate_all_ranks_for_metric(team_stats_dict, metric)
        
        # Assign rankings to each team
        for team_abbr in team_stats_dict:
            team_rankings = {}
            for metric in cls.RANKING_METRICS:
                if team_abbr in metric_rankings[metric]:
                    team_rankings[metric] = metric_rankings[metric][team_abbr]
            all_rankings[team_abbr] = team_rankings
        
        return all_rankings
    
    @classmethod
    def _calculate_all_ranks_for_metric(cls, team_stats_dict: Dict, metric: str) -> Dict[str, int]:
        """Calculate ranks for all teams for a single metric."""
        # Get all team values for this metric
        team_values = cls._extract_metric_values(team_stats_dict, metric)
        
        # Sort by value based on whether lower or higher is better
        if metric in cls.LOWER_IS_BETTER_METRICS:
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
    
    @classmethod
    def calculate_team_rankings(cls, team_abbr: str, team_stats_dict: Dict) -> Dict:
        """Calculate rankings for a specific team from league statistics dictionary.
        
        Args:
            team_abbr: Team abbreviation to calculate rankings for
            team_stats_dict: Dictionary mapping team abbreviations to their SeasonStats objects
            
        Returns:
            Dictionary mapping metric names to rank positions (1-based)
        """
        if team_abbr not in team_stats_dict:
            logger.warning(f"Team '{team_abbr}' not found in team stats dictionary")
            return {}
        
        rankings = {}
        team_stats = team_stats_dict[team_abbr]
        
        for metric in cls.RANKING_METRICS:
            if hasattr(team_stats, metric):
                team_value = getattr(team_stats, metric)
                
                # Get all team values for this metric
                team_values = cls._extract_metric_values(team_stats_dict, metric)
                
                # Calculate rank for this team
                rank = cls._calculate_metric_rank(team_abbr, team_value, team_values, metric)
                if rank:
                    rankings[metric] = rank
        
        return rankings
    
    @classmethod
    def _extract_metric_values(cls, team_stats_dict: Dict, metric: str) -> List[Tuple[str, float]]:
        """Extract all team values for a specific metric."""
        team_values = []
        for abbr, stats in team_stats_dict.items():
            if hasattr(stats, metric):
                value = getattr(stats, metric)
                team_values.append((abbr, value))

        return team_values
    
    @classmethod
    def _calculate_metric_rank(cls, team_abbr: str, team_value: float, 
                              team_values: List[Tuple[str, float]], metric: str) -> int:
        """Calculate the rank for a team's metric value with proper tie handling."""
        try:
            # Sort by value based on whether lower or higher is better
            if metric in cls.LOWER_IS_BETTER_METRICS:
                # Lower is better for turnovers, sacks allowed, penalty yards
                ranked_teams = sorted(team_values, key=lambda x: x[1])
            else:
                # Higher is better for most offensive metrics
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