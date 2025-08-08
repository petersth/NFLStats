# src/domain/metrics.py - Centralized metrics constants

"""
Centralized constants for NFL statistics metrics.
This module provides a single source of truth for metric names, display names,
and other metric-related constants throughout the application.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
from enum import Enum


class MetricType(Enum):
    """Types of metrics for categorization."""
    EFFICIENCY = "efficiency"
    VOLUME = "volume"
    RATE = "rate"
    PERCENTAGE = "percentage"


@dataclass(frozen=True)
class MetricDefinition:
    """Definition of a metric with all its properties."""
    key: str                    # Internal key used in code (e.g., 'avg_yards_per_play')
    display_name: str          # Human-readable name (e.g., 'Average Yards Per Play')
    short_name: str            # Short display name (e.g., 'Avg Yards/Play')
    export_name: str           # Name used in exports (e.g., 'Avg_Yards_Per_Play')
    unit: str                  # Unit of measurement (e.g., 'yards', '%', 'per game')
    higher_is_better: bool     # True if higher values are better for ranking
    metric_type: MetricType    # Type category for grouping
    description: str           # Detailed description for tooltips/help


class NFLMetrics:
    """Centralized constants for all NFL statistics metrics."""
    
    # Core efficiency metrics
    AVG_YARDS_PER_PLAY = MetricDefinition(
        key='avg_yards_per_play',
        display_name='Average Yards Per Play',
        short_name='Avg Yards/Play',
        export_name='Avg_Yards_Per_Play',
        unit='yards',
        higher_is_better=True,
        metric_type=MetricType.EFFICIENCY,
        description='Average yards gained per offensive play (rush attempts + pass attempts)'
    )
    
    SUCCESS_RATE = MetricDefinition(
        key='success_rate',
        display_name='Play Success Rate',
        short_name='Success Rate %',
        export_name='Success_Rate',
        unit='%',
        higher_is_better=True,
        metric_type=MetricType.PERCENTAGE,
        description='Percentage of plays that achieve minimum yardage thresholds by down'
    )
    
    # Passing metrics
    COMPLETION_PCT = MetricDefinition(
        key='completion_pct',
        display_name='Pass Completion Percentage',
        short_name='Completion %',
        export_name='Completion_Pct',
        unit='%',
        higher_is_better=True,
        metric_type=MetricType.PERCENTAGE,
        description='Percentage of pass attempts that are completed'
    )
    
    # Rushing metrics
    RUSH_YPC = MetricDefinition(
        key='rush_ypc',
        display_name='Rushing Yards Per Carry',
        short_name='Rush YPC',
        export_name='Rush_YPC',
        unit='yards',
        higher_is_better=True,
        metric_type=MetricType.EFFICIENCY,
        description='Average yards gained per rushing attempt'
    )
    
    # Turnover metrics
    TURNOVERS_PER_GAME = MetricDefinition(
        key='turnovers_per_game',
        display_name='Turnovers Per Game',
        short_name='Turnovers/Game',
        export_name='Turnovers_Per_Game',
        unit='per game',
        higher_is_better=False,
        metric_type=MetricType.RATE,
        description='Average turnovers (interceptions + fumbles lost) per game'
    )
    
    # Defense metrics
    SACKS_PER_GAME = MetricDefinition(
        key='sacks_per_game',
        display_name='Sacks Per Game',
        short_name='Sacks/Game',
        export_name='Sacks_Per_Game',
        unit='per game',
        higher_is_better=False,  # Lower is better for offense
        metric_type=MetricType.RATE,
        description='Average sacks allowed per game'
    )
    
    # Third down metrics
    THIRD_DOWN_PCT = MetricDefinition(
        key='third_down_pct',
        display_name='Third Down Conversion Rate',
        short_name='3rd Down %',
        export_name='Third_Down_Pct',
        unit='%',
        higher_is_better=True,
        metric_type=MetricType.PERCENTAGE,
        description='Percentage of third down attempts that result in first downs'
    )
    
    # First down metrics
    FIRST_DOWNS_PER_GAME = MetricDefinition(
        key='first_downs_per_game',
        display_name='First Downs Per Game',
        short_name='1st Downs/Game',
        export_name='First_Downs_Per_Game',
        unit='per game',
        higher_is_better=True,
        metric_type=MetricType.RATE,
        description='Average first downs gained per game'
    )
    
    # Scoring metrics
    POINTS_PER_DRIVE = MetricDefinition(
        key='points_per_drive',
        display_name='Points Per Drive',
        short_name='Pts/Drive',
        export_name='Points_Per_Drive',
        unit='points',
        higher_is_better=True,
        metric_type=MetricType.EFFICIENCY,
        description='Average points scored per offensive drive'
    )
    
    # Red zone metrics
    REDZONE_TD_PCT = MetricDefinition(
        key='redzone_td_pct',
        display_name='Red Zone Touchdown Percentage',
        short_name='Red Zone TD %',
        export_name='Redzone_TD_Pct',
        unit='%',
        higher_is_better=True,
        metric_type=MetricType.PERCENTAGE,
        description='Percentage of red zone trips that result in touchdowns'
    )
    
    # Penalty metrics
    PENALTY_YARDS_PER_GAME = MetricDefinition(
        key='penalty_yards_per_game',
        display_name='Penalty Yards Per Game',
        short_name='Penalty Yds/Game',
        export_name='Penalty_Yards_Per_Game',
        unit='yards per game',
        higher_is_better=False,
        metric_type=MetricType.RATE,
        description='Average penalty yards assessed per game'
    )
    
    # Composite metrics
    TOER = MetricDefinition(
        key='toer',
        display_name='Total Offensive Efficiency Rating',
        short_name='TOER',
        export_name='TOER',
        unit='rating',
        higher_is_better=True,
        metric_type=MetricType.EFFICIENCY,
        description='Composite offensive efficiency score (0-100) based on 11 key offensive metrics'
    )
    
    # Volume metrics
    TOTAL_YARDS = MetricDefinition(
        key='total_yards',
        display_name='Total Yards',
        short_name='Total Yds',
        export_name='Total_Yards',
        unit='yards',
        higher_is_better=True,
        metric_type=MetricType.VOLUME,
        description='Total offensive yards gained'
    )
    
    TOTAL_PLAYS = MetricDefinition(
        key='total_plays',
        display_name='Total Plays',
        short_name='Plays',
        export_name='Total_Plays',
        unit='plays',
        higher_is_better=True,
        metric_type=MetricType.VOLUME,
        description='Total number of offensive plays'
    )

    # Games played
    GAMES_PLAYED = MetricDefinition(
        key='games_played',
        display_name='Games Played',
        short_name='Games',
        export_name='Games_Played',
        unit='games',
        higher_is_better=True,
        metric_type=MetricType.VOLUME,
        description='Number of games played in the season'
    )

    @classmethod
    def get_all_metrics(cls) -> List[MetricDefinition]:
        """Get all metric definitions."""
        return [
            cls.AVG_YARDS_PER_PLAY,
            cls.SUCCESS_RATE,
            cls.COMPLETION_PCT,
            cls.RUSH_YPC,
            cls.TURNOVERS_PER_GAME,
            cls.SACKS_PER_GAME,
            cls.THIRD_DOWN_PCT,
            cls.FIRST_DOWNS_PER_GAME,
            cls.POINTS_PER_DRIVE,
            cls.REDZONE_TD_PCT,
            cls.PENALTY_YARDS_PER_GAME,
            cls.TOER,
            cls.TOTAL_YARDS,
            cls.TOTAL_PLAYS,
            cls.GAMES_PLAYED
        ]
    
    @classmethod
    def get_metric_by_key(cls, key: str) -> MetricDefinition:
        """Get metric definition by key."""
        for metric in cls.get_all_metrics():
            if metric.key == key:
                return metric
        raise ValueError(f"Unknown metric key: {key}")
    
    @classmethod
    def get_key_to_display_map(cls) -> Dict[str, str]:
        """Get mapping from metric keys to display names."""
        return {metric.key: metric.display_name for metric in cls.get_all_metrics()}
    
    @classmethod
    def get_key_to_short_map(cls) -> Dict[str, str]:
        """Get mapping from metric keys to short names."""
        return {metric.key: metric.short_name for metric in cls.get_all_metrics()}
    
    @classmethod
    def get_key_to_export_map(cls) -> Dict[str, str]:
        """Get mapping from metric keys to export names."""
        return {metric.key: metric.export_name for metric in cls.get_all_metrics()}
    
    @classmethod
    def get_ranking_metrics(cls) -> List[Tuple[str, bool]]:
        """Get list of (metric_key, ascending) tuples for ranking calculations."""
        return [(metric.key, not metric.higher_is_better) for metric in cls.get_all_metrics() 
                if metric.metric_type in [MetricType.EFFICIENCY, MetricType.RATE, MetricType.PERCENTAGE]]
    
    @classmethod
    def get_metrics_by_type(cls, metric_type: MetricType) -> List[MetricDefinition]:
        """Get all metrics of a specific type."""
        return [metric for metric in cls.get_all_metrics() if metric.metric_type == metric_type]


