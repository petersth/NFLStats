# src/domain/game_processor.py - Process games once, store both perspectives

import logging
from typing import Callable, Dict, List, Tuple
import pandas as pd
from dataclasses import dataclass

from .entities import OffensiveStats

logger = logging.getLogger(__name__)


@dataclass
class GameResult:
    """Results from a single game containing both teams' offensive performances.
    
    This is a game-centric view storing both teams' offensive statistics.
    Each team's defensive performance is implicitly the opponent's offensive performance.
    """
    game_id: str
    home_team: str
    away_team: str
    home_team_offensive_stats: OffensiveStats  # Home team's offensive performance
    away_team_offensive_stats: OffensiveStats  # Away team's offensive performance
    week: int
    season_type: str


class GameProcessor:
    """Process each game once and calculate both teams' offensive TOERs."""
    
    def __init__(
        self,
        offensive_stats_calculator: Callable[[pd.DataFrame, str], OffensiveStats],
    ):
        self._offensive_stats_calculator = offensive_stats_calculator
    
    def process_all_games(self, pbp_data: pd.DataFrame) -> Dict[str, List[GameResult]]:
        """Process all games and return results organized by team.
        
        Returns:
            Dict mapping team abbreviation to list of GameResults
        """
        if pbp_data is None or len(pbp_data) == 0:
            return {}
        
        if 'game_id' not in pbp_data.columns:
            raise ValueError("Play-by-play data is missing required 'game_id' column")
            
        games = pbp_data.groupby('game_id', sort=False, observed=True)
        logger.info(f"Processing {games.ngroups} unique games")
        
        team_results = {}
        
        # Group once instead of scanning the full season for every game.  Groupby
        # preserves the original row order within each game, which is important
        # for consumers that inspect the first or final play.
        for game_id, game_data in games:
            first_play = game_data.iloc[0]
            home_team = first_play.get('home_team', '')
            away_team = first_play.get('away_team', '')
            week = int(first_play.get('week', 0))
            season_type = first_play.get('season_type', 'REG')
            
            if not home_team or not away_team:
                raise ValueError(f"Game {game_id} is missing its home or away team")
            
            home_team_offensive_stats = self._calculate_team_offensive_stats(game_data, home_team)
            away_team_offensive_stats = self._calculate_team_offensive_stats(game_data, away_team)
            
            game_result = GameResult(
                game_id=game_id,
                home_team=home_team,
                away_team=away_team,
                home_team_offensive_stats=home_team_offensive_stats,
                away_team_offensive_stats=away_team_offensive_stats,
                week=week,
                season_type=season_type
            )
            
            if home_team not in team_results:
                team_results[home_team] = []
            team_results[home_team].append(game_result)
            
            if away_team not in team_results:
                team_results[away_team] = []
            team_results[away_team].append(game_result)
        
        logger.info(f"Processed games for teams: {list(team_results.keys())[:5]}... Total teams: {len(team_results)}")
        
        return team_results
    
    def _calculate_team_offensive_stats(self, game_data: pd.DataFrame, team_abbr: str) -> OffensiveStats:
        """Calculate one team's game stats through the shared metric engine."""
        team_offensive_data = game_data[game_data['posteam'] == team_abbr]
        return self._offensive_stats_calculator(team_offensive_data, team_abbr)
    
    @staticmethod
    def get_team_toer_stats(team_results: List[GameResult], team_abbr: str) -> Tuple[float, float]:
        """Calculate average TOER and TOER Allowed for a team.
        
        Returns:
            Tuple of (avg_toer, avg_toer_allowed)
        """
        if not team_results:
            return 0.0, 0.0
        
        offensive_toers = []
        toers_allowed = []
        
        for game in team_results:
            if game.home_team == team_abbr:
                # We were home team
                offensive_toers.append(game.home_team_offensive_stats.toer)
                toers_allowed.append(game.away_team_offensive_stats.toer)  # Opponent's TOER is our TOER Allowed
            elif game.away_team == team_abbr:
                # We were away team
                offensive_toers.append(game.away_team_offensive_stats.toer)
                toers_allowed.append(game.home_team_offensive_stats.toer)  # Opponent's TOER is our TOER Allowed
        
        avg_toer = sum(offensive_toers) / len(offensive_toers) if offensive_toers else 0.0
        avg_toer_allowed = sum(toers_allowed) / len(toers_allowed) if toers_allowed else 0.0
        
        return avg_toer, avg_toer_allowed
