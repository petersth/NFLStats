# src/domain/entities.py - Core domain entities

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


class GameType(Enum):
    REGULAR = "REG"
    PLAYOFF = "POST"


class Location(Enum):
    HOME = "Home"
    AWAY = "Away"


@dataclass
class Team:
    """NFL Team entity with metadata."""
    abbreviation: str
    name: str
    colors: List[str]
    logo: str
    
    @classmethod
    def from_abbreviation(cls, abbreviation: str) -> 'Team':
        """Factory method to create Team from abbreviation."""
        from ..config.nfl_constants import TEAM_DATA
        if abbreviation not in TEAM_DATA:
            raise ValueError(f"Unknown team abbreviation: {abbreviation}")
        
        data = TEAM_DATA[abbreviation]
        return cls(
            abbreviation=abbreviation,
            name=data['name'],
            colors=data['colors'],
            logo=data['logo']
        )


@dataclass
class Season:
    """NFL Season entity."""
    year: int
    
    @property
    def is_current_season(self) -> bool:
        from datetime import datetime
        current_year = datetime.now().year
        current_month = datetime.now().month
        return self.year == (current_year if current_month >= 9 else current_year - 1)


@dataclass
class Game:
    """Individual NFL game entity."""
    game_id: str
    season: Season
    week: int
    game_date: str
    home_team: Team
    away_team: Team
    game_type: GameType


@dataclass
class GameStats:
    """Statistics for a single game."""
    game: Game
    team: Team
    opponent: Team
    location: Location
    yards_per_play: float
    total_yards: int
    total_plays: int
    turnovers: int
    completion_pct: float
    rush_ypc: float
    sacks_allowed: int
    third_down_pct: float
    success_rate: float
    first_downs: int
    points_per_drive: float
    redzone_td_pct: float
    penalty_yards: int


@dataclass
class SeasonStats:
    """Aggregated statistics for a full season."""
    team: Team
    season: Season
    games_played: int
    avg_yards_per_play: float
    total_yards: int
    total_plays: int
    turnovers_per_game: float
    completion_pct: float
    rush_ypc: float
    sacks_per_game: float
    third_down_pct: float
    success_rate: float
    first_downs_per_game: float
    points_per_drive: float
    redzone_td_pct: float
    penalty_yards_per_game: float
    
    # Raw input data for methodology display
    total_rush_yards: int = 0
    total_rush_attempts: int = 0
    total_pass_completions: int = 0
    total_pass_attempts: int = 0
    total_turnovers: int = 0
    total_sacks: int = 0
    total_third_downs: int = 0
    total_third_down_conversions: int = 0
    total_first_downs: int = 0
    total_drives: int = 0
    total_offensive_points: int = 0
    total_redzone_trips: int = 0
    total_redzone_tds: int = 0
    total_penalty_yards: int = 0
    
    # Success rate breakdown by down
    first_down_successful_plays: int = 0
    first_down_total_plays: int = 0
    second_down_successful_plays: int = 0
    second_down_total_plays: int = 0
    third_down_successful_plays: int = 0
    third_down_total_plays: int = 0
    
    # Scoring breakdown for Points Per Drive
    total_touchdowns: int = 0
    total_extra_points: int = 0  
    total_two_point_conversions: int = 0
    total_field_goals: int = 0
    
    # Turnover breakdown
    total_interceptions: int = 0
    total_fumbles_lost: int = 0
    
    # First down breakdown
    total_first_downs_rush: int = 0
    total_first_downs_pass: int = 0
    total_first_downs_penalty: int = 0
    
    # Third down conversion breakdown
    total_third_down_rush_conversions: int = 0
    total_third_down_pass_conversions: int = 0
    
    # Red zone outcome breakdown
    total_redzone_field_goals: int = 0
    total_redzone_failed: int = 0


@dataclass(frozen=True)
class TeamRecord:
    """Team's win-loss record."""
    regular_season_wins: int
    regular_season_losses: int
    playoff_wins: int
    playoff_losses: int
    
    @property
    def total_games(self) -> int:
        return (self.regular_season_wins + self.regular_season_losses + 
                self.playoff_wins + self.playoff_losses)


@dataclass
class PerformanceRank:
    """Performance ranking with context."""
    rank: int
    total_teams: int
    description: str
    percentile: str
    color: str
    
    @property
    def is_elite(self) -> bool:
        return self.rank <= 3
    
    @property
    def is_above_average(self) -> bool:
        return self.rank <= 16