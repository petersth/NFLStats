# src/utils/ranking_utils.py - Ranking utility functions

from ..domain.entities import PerformanceRank
from ..config import TOTAL_NFL_TEAMS

# Business rules for ranking thresholds
ELITE_CUTOFF = 3
TOP_25_PERCENT_CUTOFF = 8
ABOVE_AVERAGE_CUTOFF = 16
BOTTOM_25_PERCENT_CUTOFF = 25
BOTTOM_3_CUTOFF = 30


def calculate_performance_rank(rank: int, total_teams: int = TOTAL_NFL_TEAMS) -> PerformanceRank:
    """Calculate performance ranking with proper business rules.
    
    Args:
        rank: Team's rank (1 = best)
        total_teams: Total number of teams in comparison
        
    Returns:
        PerformanceRank object with description, percentile, and color
    """
    if rank == 1:
        return PerformanceRank(
            rank=rank,
            total_teams=total_teams,
            description='Best in NFL',
            percentile='100th percentile',
            color='success'
        )
    elif rank <= ELITE_CUTOFF:
        return PerformanceRank(
            rank=rank,
            total_teams=total_teams,
            description='Elite',
            percentile=f'Top {int((ELITE_CUTOFF/total_teams)*100)}%',
            color='success'
        )
    elif rank <= TOP_25_PERCENT_CUTOFF:
        return PerformanceRank(
            rank=rank,
            total_teams=total_teams,
            description='Excellent',
            percentile=f'Top {int((TOP_25_PERCENT_CUTOFF/total_teams)*100)}%',
            color='success'
        )
    elif rank <= ABOVE_AVERAGE_CUTOFF:
        return PerformanceRank(
            rank=rank,
            total_teams=total_teams,
            description='Above Average',
            percentile=f'Top {int((ABOVE_AVERAGE_CUTOFF/total_teams)*100)}%',
            color='info'
        )
    elif rank <= BOTTOM_25_PERCENT_CUTOFF:
        return PerformanceRank(
            rank=rank,
            total_teams=total_teams,
            description='Below Average',
            percentile=f'Bottom {int(((total_teams-rank+1)/total_teams)*100)}%',
            color='warning'
        )
    elif rank >= BOTTOM_3_CUTOFF:
        return PerformanceRank(
            rank=rank,
            total_teams=total_teams,
            description='Poor',
            percentile=f'Bottom {int(((total_teams-rank+1)/total_teams)*100)}%',
            color='error'
        )
    else:
        return PerformanceRank(
            rank=rank,
            total_teams=total_teams,
            description='Below Average',
            percentile=f'Bottom {int(((total_teams-rank+1)/total_teams)*100)}%',
            color='warning'
        )