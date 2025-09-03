# src/domain/game_processor.py - Process games once, store both perspectives

import logging
from typing import Dict, List, Tuple
import pandas as pd
from dataclasses import dataclass

from .entities import Team, OffensiveStats
from .toer_calculator import TOERCalculator
from .utilities import PlayFilter

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
    
    def __init__(self):
        self._play_filter = PlayFilter()
    
    def process_all_games(self, pbp_data: pd.DataFrame) -> Dict[str, List[GameResult]]:
        """Process all games and return results organized by team.
        
        Returns:
            Dict mapping team abbreviation to list of GameResults
        """
        if pbp_data is None or len(pbp_data) == 0:
            return {}
        
        if 'game_id' not in pbp_data.columns:
            logger.error("No game_id column in data")
            return {}
            
        unique_games = pbp_data['game_id'].unique()
        logger.info(f"Processing {len(unique_games)} unique games")
        
        team_results = {}
        
        for game_id in unique_games:
            game_data = pbp_data[pbp_data['game_id'] == game_id]
            
            first_play = game_data.iloc[0]
            home_team = first_play.get('home_team', '')
            away_team = first_play.get('away_team', '')
            week = int(first_play.get('week', 0))
            season_type = first_play.get('season_type', 'REG')
            
            if not home_team or not away_team:
                continue
            
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
        """Calculate offensive stats for a team in a game."""
        try:
            team_offensive_data = game_data[game_data['posteam'] == team_abbr]
            offensive_plays = self._play_filter.get_offensive_plays(team_offensive_data)
            
            if len(offensive_plays) == 0:
                return self._create_empty_offensive_stats()
            
            total_yards = int(offensive_plays['yards_gained'].sum())
            total_plays = len(offensive_plays)
            yards_per_play = total_yards / total_plays if total_plays > 0 else 0.0
            
            stats = self._calculate_offensive_stats(team_offensive_data, team_abbr)
            
            toer = TOERCalculator.calculate_toer(
                avg_yards_per_play=yards_per_play,
                turnovers=stats.get('turnovers', 0),
                completion_pct=stats.get('completion_pct', 0.0),
                rush_ypc=stats.get('rush_ypc', 0.0),
                sacks=stats.get('sacks', 0),
                third_down_pct=stats.get('third_down_pct', 0.0),
                success_rate=stats.get('success_rate', 0.0),
                first_downs=float(stats.get('first_downs', 0)),
                points_per_drive=stats.get('points_per_drive', 0.0),
                redzone_td_pct=stats.get('redzone_td_pct', 0.0),
                penalty_yards=stats.get('penalty_yards', 0)
            )
            
            return OffensiveStats(
                yards_per_play=yards_per_play,
                total_yards=total_yards,
                total_plays=total_plays,
                turnovers=stats.get('turnovers', 0),
                completion_pct=stats.get('completion_pct', 0.0),
                rush_ypc=stats.get('rush_ypc', 0.0),
                sacks=stats.get('sacks', 0),
                third_down_pct=stats.get('third_down_pct', 0.0),
                success_rate=stats.get('success_rate', 0.0),
                first_downs=stats.get('first_downs', 0),
                points_per_drive=stats.get('points_per_drive', 0.0),
                redzone_td_pct=stats.get('redzone_td_pct', 0.0),
                penalty_yards=stats.get('penalty_yards', 0),
                toer=toer
            )
            
        except Exception as e:
            logger.error(f"Error calculating offensive stats for {team_abbr}: {e}")
            return self._create_empty_offensive_stats()
    
    def _create_empty_offensive_stats(self) -> OffensiveStats:
        """Create empty offensive stats object."""
        return OffensiveStats(
            yards_per_play=0.0,
            total_yards=0,
            total_plays=0,
            turnovers=0,
            completion_pct=0.0,
            rush_ypc=0.0,
            sacks=0,
            third_down_pct=0.0,
            success_rate=0.0,
            first_downs=0,
            points_per_drive=0.0,
            redzone_td_pct=0.0,
            penalty_yards=0,
            toer=0.0
        )
    def _calculate_offensive_stats(self, team_data: pd.DataFrame, team_abbr: str) -> Dict:
        """Calculate offensive statistics for TOER calculation using full methodology."""
        from ..config.nfl_constants import RED_ZONE_YARDLINE
        import numpy as np
        
        offensive_plays = self._play_filter.get_offensive_plays(team_data)
        passing_plays = self._play_filter.get_passing_plays(team_data)
        rushing_plays = self._play_filter.get_rushing_plays(team_data)
        third_downs = self._play_filter.get_third_down_attempts(team_data)
        
        # Initialize stats
        stats = {}
        
        # Turnovers
        interceptions = int((team_data.get('interception', 0) == 1).sum())
        fumbles_lost = int((team_data.get('fumble_lost', 0) == 1).sum())
        stats['turnovers'] = interceptions + fumbles_lost
        
        # Completion percentage
        if len(passing_plays) > 0:
            completions = (passing_plays.get('complete_pass', 0) == 1).sum()
            stats['completion_pct'] = (completions / len(passing_plays)) * 100
        else:
            stats['completion_pct'] = 0.0
        
        # Rush yards per carry
        if len(rushing_plays) > 0:
            rush_yards = rushing_plays['yards_gained'].sum()
            stats['rush_ypc'] = rush_yards / len(rushing_plays)
        else:
            stats['rush_ypc'] = 0.0
        
        # Sacks
        stats['sacks'] = int((team_data.get('sack', 0) == 1).sum())
        
        # Third down conversion percentage
        if len(third_downs) > 0 and 'first_down' in third_downs.columns and 'touchdown' in third_downs.columns:
            third_down_conversions = ((third_downs['first_down'] == 1) | (third_downs['touchdown'] == 1)).sum()
            stats['third_down_pct'] = (third_down_conversions / len(third_downs)) * 100
        else:
            stats['third_down_pct'] = 0.0
        
        # Success rate (simplified - would need full success rate logic)
        if len(offensive_plays) > 0 and 'down' in offensive_plays.columns and 'ydstogo' in offensive_plays.columns:
            # Apply success rate criteria
            success_mask = np.where(
                offensive_plays['down'] == 1,
                offensive_plays['yards_gained'] >= 0.4 * offensive_plays['ydstogo'],
                np.where(
                    offensive_plays['down'] == 2,
                    offensive_plays['yards_gained'] >= 0.6 * offensive_plays['ydstogo'],
                    offensive_plays['yards_gained'] >= offensive_plays['ydstogo']
                )
            )
            successful_plays = success_mask.sum()
            stats['success_rate'] = (successful_plays / len(offensive_plays)) * 100
        else:
            stats['success_rate'] = 0.0
        
        # First downs
        if 'first_down_rush' in team_data.columns and 'first_down_pass' in team_data.columns:
            stats['first_downs'] = int(
                ((team_data['first_down_rush'] == 1) | 
                 (team_data['first_down_pass'] == 1) | 
                 (team_data.get('first_down_penalty', 0) == 1)).sum()
            )
        else:
            stats['first_downs'] = 0
        
        # Points per drive (simplified)
        if 'drive' in team_data.columns and team_data['drive'].notna().any():
            num_drives = team_data['drive'].nunique()
            touchdowns = int((team_data.get('touchdown', 0) == 1).sum()) * 6
            field_goals = int((team_data.get('field_goal_result', '') == 'made').sum()) * 3
            extra_points = int((team_data.get('extra_point_result', '') == 'good').sum())
            total_points = touchdowns + field_goals + extra_points
            stats['points_per_drive'] = total_points / num_drives if num_drives > 0 else 0.0
        else:
            stats['points_per_drive'] = 0.0
        
        # Red zone TD percentage
        if 'yardline_100' in team_data.columns:
            rz_plays = team_data[(team_data['yardline_100'] <= RED_ZONE_YARDLINE) & (team_data['yardline_100'] > 0)]
            if len(rz_plays) > 0 and 'drive' in rz_plays.columns:
                rz_drives = rz_plays.groupby(['drive']).agg({
                    'touchdown': 'max'
                }).reset_index()
                rz_trips = len(rz_drives)
                rz_touchdowns = rz_drives['touchdown'].sum()
                stats['redzone_td_pct'] = (rz_touchdowns / rz_trips) * 100 if rz_trips > 0 else 0.0
            else:
                stats['redzone_td_pct'] = 0.0
        else:
            stats['redzone_td_pct'] = 0.0
        
        # Penalty yards
        if 'penalty_team' in team_data.columns and 'penalty_yards' in team_data.columns:
            penalties = team_data[(team_data['penalty_team'] == team_abbr) & 
                                 (team_data['posteam'] == team_abbr)]
            stats['penalty_yards'] = int(penalties['penalty_yards'].sum())
        else:
            stats['penalty_yards'] = 0
        
        return stats
    
    def get_team_toer_stats(self, team_results: List[GameResult], team_abbr: str) -> Tuple[float, float]:
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
            else:
                # We were away team
                offensive_toers.append(game.away_team_offensive_stats.toer)
                toers_allowed.append(game.home_team_offensive_stats.toer)  # Opponent's TOER is our TOER Allowed
        
        avg_toer = sum(offensive_toers) / len(offensive_toers) if offensive_toers else 0.0
        avg_toer_allowed = sum(toers_allowed) / len(toers_allowed) if toers_allowed else 0.0
        
        return avg_toer, avg_toer_allowed