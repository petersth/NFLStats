# src/domain/nfl_stats_calculator.py - NFL statistics calculator

import logging
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

from .entities import Team, Season, SeasonStats, GameStats, TeamRecord
from .exceptions import StatisticsCalculationError
from .utilities import PlayFilter
from ..config.nfl_constants import (
    TOUCHDOWN_POINTS, EXTRA_POINT_POINTS, TWO_POINT_CONVERSION_POINTS,
    FIELD_GOAL_POINTS, RED_ZONE_YARDLINE, FIRST_DOWN_SUCCESS_THRESHOLD,
    SECOND_DOWN_SUCCESS_THRESHOLD, CONVERSION_SUCCESS_THRESHOLD
)

logger = logging.getLogger(__name__)

class NFLStatsCalculator:
    """NFL statistics calculator."""
    
    def __init__(self):
        self._constants = type('Constants', (), {
            'TOUCHDOWN_POINTS': TOUCHDOWN_POINTS,
            'EXTRA_POINT_POINTS': EXTRA_POINT_POINTS,
            'TWO_POINT_CONVERSION_POINTS': TWO_POINT_CONVERSION_POINTS,
            'FIELD_GOAL_POINTS': FIELD_GOAL_POINTS,
            'RED_ZONE_YARDLINE': RED_ZONE_YARDLINE,
            'FIRST_DOWN_SUCCESS_THRESHOLD': FIRST_DOWN_SUCCESS_THRESHOLD,
            'SECOND_DOWN_SUCCESS_THRESHOLD': SECOND_DOWN_SUCCESS_THRESHOLD,
            'CONVERSION_SUCCESS_THRESHOLD': CONVERSION_SUCCESS_THRESHOLD
        })()
        self._play_filter = PlayFilter()
    
    def _safe_sum(self, series, default=0):
        """Safely sum a pandas series with default."""
        return int(series.sum()) if len(series) > 0 else default
    
    def _safe_mean(self, series, default=0.0):
        """Safely calculate mean with default."""
        return float(series.mean()) if len(series) > 0 else default
    
    def _safe_percentage(self, numerator, denominator, default=0.0):
        """Safely calculate percentage with default."""
        return (numerator / denominator) * 100.0 if denominator > 0 else default
    
    # === Main Interface Methods ===
    
    def calculate_season_stats(self, team_data: pd.DataFrame, team: Team, 
                              season: Season, pre_calculated: Optional[Dict] = None) -> SeasonStats:
        """Calculate complete season statistics from raw play data."""
        try:
            if len(team_data) == 0:
                return self._create_empty_season_stats(team, season)
            
            games_played = self._count_games(team_data)
            if games_played == 0:
                return self._create_empty_season_stats(team, season)
            
            # Calculate all stats in one pass
            stats = self._calculate_all_stats(team_data, team.abbreviation)
            return self._build_season_stats(team, season, games_played, stats)
            
        except Exception as e:
            logger.error(f"Error calculating season stats for {team.abbreviation}: {e}")
            return self._create_empty_season_stats(team, season)
    
    # NOTE: calculate_from_aggregates method removed to prevent confusion.
    # This orchestrator only uses raw data calculations to ensure identical results
    # between fresh NFL and database-optimized strategies.
    
    def calculate_game_stats(self, team_data: pd.DataFrame, team: Team) -> List[GameStats]:
        """Calculate game-by-game statistics."""
        try:
            if len(team_data) == 0 or 'game_id' not in team_data.columns:
                return []
            
            game_stats = []
            for game_id in team_data['game_id'].unique():
                game_data = team_data[team_data['game_id'] == game_id]
                
                # Calculate actual game statistics
                offensive_plays = self._play_filter.get_offensive_plays(game_data)
                
                # Basic stats
                total_yards = int(offensive_plays['yards_gained'].sum()) if len(offensive_plays) > 0 else 0
                total_plays = len(offensive_plays)
                yards_per_play = total_yards / total_plays if total_plays > 0 else 0.0
                
                game_stats_dict = self._calculate_all_stats(game_data, team.abbreviation)
                
                # Extract the specific stats needed for GameStats
                turnovers = game_stats_dict.get('total_turnovers', 0)
                completion_pct = game_stats_dict.get('completion_pct', 0.0)
                rush_ypc = game_stats_dict.get('rush_ypc', 0.0)
                sacks_allowed = game_stats_dict.get('sacks', 0)
                third_down_pct = game_stats_dict.get('third_down_pct', 0.0)
                success_rate = game_stats_dict.get('success_rate', 0.0)
                first_downs = game_stats_dict.get('first_downs_total', 0)
                penalty_yards = game_stats_dict.get('penalty_yards', 0)
                points_per_drive = game_stats_dict.get('points_per_drive', 0.0)
                redzone_td_pct = game_stats_dict.get('redzone_td_pct', 0.0)
                
                # Determine opponent
                opponent = self._get_opponent_from_game_data(game_data, team.abbreviation)
                opponent_team = Team.from_abbreviation(opponent) if opponent != "Unknown" else team
                
                # Create game stats object
                game_stat = GameStats(
                    game=None,  # Game entity not needed for stats display
                    team=team,
                    opponent=opponent_team,
                    location=self._determine_location(game_data, team.abbreviation),
                    yards_per_play=yards_per_play,
                    total_yards=total_yards,
                    total_plays=total_plays,
                    turnovers=turnovers,
                    completion_pct=completion_pct,
                    rush_ypc=rush_ypc,
                    sacks_allowed=sacks_allowed,
                    third_down_pct=third_down_pct,
                    success_rate=success_rate,
                    first_downs=first_downs,
                    points_per_drive=points_per_drive,
                    redzone_td_pct=redzone_td_pct,
                    penalty_yards=penalty_yards,
                )
                game_stats.append(game_stat)
            
            return game_stats
            
        except Exception as e:
            logger.error(f"Error calculating game stats for {team.abbreviation}: {e}")
            return []
    
    def calculate_team_record(self, team_data: pd.DataFrame, team_abbreviation: str) -> Optional[TeamRecord]:
        """Calculate team's win-loss record."""
        try:
            if len(team_data) == 0 or 'game_id' not in team_data.columns:
                return None
            
            # Get unique games and try to determine wins/losses
            games = team_data['game_id'].unique()
            wins = 0
            losses = 0
            ties = 0
            
            for game_id in games:
                game_data = team_data[team_data['game_id'] == game_id]
                
                # Try to determine game result from score columns if available
                if 'posteam_score_post' in game_data.columns and 'defteam_score_post' in game_data.columns:
                    final_play = game_data.iloc[-1]  # Last play of game
                    team_score = final_play['posteam_score_post']
                    opp_score = final_play['defteam_score_post']
                    
                    if team_score > opp_score:
                        wins += 1
                    elif team_score < opp_score:
                        losses += 1
                    else:
                        ties += 1
            
            return TeamRecord(
                regular_season_wins=wins, 
                regular_season_losses=losses,
                playoff_wins=0,  # We don't have playoff data in this context
                playoff_losses=0
            )
            
        except Exception as e:
            logger.error(f"Error calculating team record for {team_abbreviation}: {e}")
            return TeamRecord(
                regular_season_wins=0, 
                regular_season_losses=0,
                playoff_wins=0,
                playoff_losses=0
            )
    
    # === Consolidated Calculation Methods ===
    
    def _calculate_all_stats(self, data: pd.DataFrame, team_abbr: str) -> Dict:
        """Calculate all statistics in one consolidated method."""
        offensive_plays = self._play_filter.get_offensive_plays(data)
        
        return {
            'total_plays': len(offensive_plays),
            'total_yards': self._safe_sum(offensive_plays['yards_gained']),
            'avg_yards_per_play': self._safe_mean(offensive_plays['yards_gained']),
            **self._calculate_passing_rushing_stats(data),
            **self._calculate_turnover_stats(data),
            **self._calculate_down_stats(data),
            **self._calculate_success_stats(data),
            **self._calculate_team_specific_stats(data, team_abbr)
        }
    
    def _calculate_passing_rushing_stats(self, data: pd.DataFrame) -> Dict:
        """Calculate passing and rushing stats together."""
        pass_plays = self._play_filter.get_passing_plays(data)
        rush_plays = self._play_filter.get_rushing_plays(data)
        
        return {
            'pass_attempts': len(pass_plays),
            'pass_completions': self._safe_sum(pass_plays.get('complete_pass', pd.Series(dtype='int64'))),
            'completion_pct': self._safe_percentage(
                self._safe_sum(pass_plays.get('complete_pass', pd.Series(dtype='int64'))), len(pass_plays)
            ),
            'rush_attempts': len(rush_plays),
            'rush_yards': self._safe_sum(rush_plays['yards_gained']),
            'rush_ypc': self._safe_mean(rush_plays['yards_gained'])
        }
    
    def _calculate_down_stats(self, data: pd.DataFrame) -> Dict:
        """Calculate down-specific statistics."""
        third_downs = self._play_filter.get_third_down_attempts(data)
        required_cols = ['first_down', 'touchdown']
        
        if not all(col in third_downs.columns for col in required_cols):
            third_down_conversions = 0
            third_down_pct = 0.0
        else:
            third_down_conversions = self._safe_sum(
                (third_downs['first_down'] == 1) | (third_downs['touchdown'] == 1)
            )
            third_down_pct = self._safe_percentage(third_down_conversions, len(third_downs))
        
        # First downs
        first_down_cols = ['first_down_rush', 'first_down_pass', 'first_down_penalty']
        if all(col in data.columns for col in first_down_cols):
            first_downs_rush = self._safe_sum(data['first_down_rush'] == 1)
            first_downs_pass = self._safe_sum(data['first_down_pass'] == 1)
            first_downs_penalty = self._safe_sum(data['first_down_penalty'] == 1)
            first_downs_total = self._safe_sum(
                (data['first_down_rush'] == 1) | 
                (data['first_down_pass'] == 1) | 
                (data['first_down_penalty'] == 1)
            )
        else:
            first_downs_rush = first_downs_pass = first_downs_penalty = first_downs_total = 0
        
        # Third down conversion breakdown by play type
        third_down_rush_conversions = 0
        third_down_pass_conversions = 0
        
        if len(third_downs) > 0 and all(col in third_downs.columns for col in ['rush_attempt', 'pass_attempt', 'first_down', 'touchdown']):
            # Third down conversions on rushing plays
            third_down_rush_plays = third_downs[third_downs['rush_attempt'] == 1]
            third_down_rush_conversions = self._safe_sum(
                (third_down_rush_plays['first_down'] == 1) | (third_down_rush_plays['touchdown'] == 1)
            )
            
            # Third down conversions on passing plays
            third_down_pass_plays = third_downs[third_downs['pass_attempt'] == 1]
            third_down_pass_conversions = self._safe_sum(
                (third_down_pass_plays['first_down'] == 1) | (third_down_pass_plays['touchdown'] == 1)
            )
        
        return {
            'third_down_attempts': len(third_downs),
            'third_down_conversions': third_down_conversions,
            'third_down_pct': third_down_pct,
            'third_down_rush_conversions': third_down_rush_conversions,
            'third_down_pass_conversions': third_down_pass_conversions,
            'first_downs_rush': first_downs_rush,
            'first_downs_pass': first_downs_pass,
            'first_downs_penalty': first_downs_penalty,
            'first_downs_total': first_downs_total
        }
    
    def _calculate_success_stats(self, data: pd.DataFrame) -> Dict:
        """Calculate success rate statistics."""
        plays = self._play_filter.get_offensive_plays(data)
        eligible_plays = plays[plays['ydstogo'].notna()].copy()
        eligible_plays = self._play_filter.apply_success_rate_exclusions(eligible_plays)
        
        if len(eligible_plays) == 0:
            return {
                'success_rate': 0.0,
                'first_down_successful': 0, 'first_down_total': 0,
                'second_down_successful': 0, 'second_down_total': 0,
                'third_down_successful': 0, 'third_down_total': 0
            }
        
        # Calculate success for each play
        eligible_plays['success'] = self._identify_successful_plays(eligible_plays)
        overall_success_rate = self._safe_percentage(eligible_plays['success'].sum(), len(eligible_plays))
        
        # Group by down
        first_down_plays = eligible_plays[eligible_plays['down'] == 1]
        second_down_plays = eligible_plays[eligible_plays['down'] == 2]
        third_down_plays = eligible_plays[eligible_plays['down'] >= 3]
        
        return {
            'success_rate': overall_success_rate,
            'first_down_successful': self._safe_sum(first_down_plays['success']),
            'first_down_total': len(first_down_plays),
            'second_down_successful': self._safe_sum(second_down_plays['success']),
            'second_down_total': len(second_down_plays),
            'third_down_successful': self._safe_sum(third_down_plays['success']),
            'third_down_total': len(third_down_plays)
        }
    
    def _calculate_team_specific_stats(self, data: pd.DataFrame, team_abbr: str) -> Dict:
        """Calculate team-specific statistics (sacks, penalties, scoring, redzone)."""
        # Sacks
        sacks = self._safe_sum(data.get('sack', pd.Series(dtype='int64')))
        
        # Penalties
        if all(col in data.columns for col in ['penalty_team', 'penalty_yards', 'posteam']):
            penalties = data[(data['penalty_team'] == team_abbr) & (data['posteam'] == team_abbr)]
            penalty_yards = self._safe_sum(penalties['penalty_yards'])
        else:
            penalty_yards = 0
        
        # Scoring and redzone stats
        scoring_stats = self._calculate_scoring_and_redzone_stats(data, team_abbr)
        
        return {
            'sacks': sacks,
            'penalty_yards': penalty_yards,
            **scoring_stats
        }
    
    def _calculate_scoring_and_redzone_stats(self, data: pd.DataFrame, team_abbr: str) -> Dict:
        """Calculate scoring and redzone statistics together."""
        if 'drive' not in data.columns:
            return {
                'drives': 0, 'touchdowns': 0, 'extra_points': 0, 'two_point_conversions': 0,
                'field_goals': 0, 'points': 0, 'points_per_drive': 0.0,
                'redzone_trips': 0, 'redzone_touchdowns': 0, 'redzone_field_goals': 0, 
                'redzone_failed': 0, 'redzone_td_pct': 0.0
            }
        
        drives_data = data[data['drive'].notna()]
        if len(drives_data) == 0:
            return {
                'drives': 0, 'touchdowns': 0, 'extra_points': 0, 'two_point_conversions': 0,
                'field_goals': 0, 'points': 0, 'points_per_drive': 0.0,
                'redzone_trips': 0, 'redzone_touchdowns': 0, 'redzone_field_goals': 0,
                'redzone_failed': 0, 'redzone_td_pct': 0.0
            }
        
        # Process drives
        drive_points = []
        total_touchdowns = total_extra_points = total_two_point_conversions = total_field_goals = 0
        
        for _, drive_plays in drives_data.groupby(['game_id', 'drive']):
            drive_total = 0
            
            # Touchdowns
            offensive_tds = self._play_filter.get_offensive_touchdowns(drive_plays, team_abbr)
            drive_touchdowns = len(offensive_tds)
            drive_total += drive_touchdowns * self._constants.TOUCHDOWN_POINTS
            total_touchdowns += drive_touchdowns
            
            # Other scoring
            if 'extra_point_result' in drive_plays.columns:
                drive_extra_points = self._safe_sum(drive_plays['extra_point_result'] == 'good')
                drive_total += drive_extra_points * self._constants.EXTRA_POINT_POINTS
                total_extra_points += drive_extra_points
            
            if 'two_point_conv_result' in drive_plays.columns:
                drive_two_points = self._safe_sum(drive_plays['two_point_conv_result'] == 'success')
                drive_total += drive_two_points * self._constants.TWO_POINT_CONVERSION_POINTS
                total_two_point_conversions += drive_two_points
            
            if 'field_goal_result' in drive_plays.columns:
                drive_field_goals = self._safe_sum(drive_plays['field_goal_result'] == 'made')
                drive_total += drive_field_goals * self._constants.FIELD_GOAL_POINTS
                total_field_goals += drive_field_goals
            
            drive_points.append(drive_total)
        
        # Redzone stats
        redzone_stats = self._calculate_redzone_only(data)
        
        return {
            'drives': len(drive_points),
            'touchdowns': total_touchdowns,
            'extra_points': total_extra_points,
            'two_point_conversions': total_two_point_conversions,
            'field_goals': total_field_goals,
            'points': sum(drive_points),
            'points_per_drive': sum(drive_points) / len(drive_points) if drive_points else 0.0,
            **redzone_stats
        }
    
    def _calculate_redzone_only(self, data: pd.DataFrame) -> Dict:
        """Calculate redzone statistics only."""
        required_cols = ['yardline_100', 'drive', 'touchdown']
        if not all(col in data.columns for col in required_cols):
            return {'redzone_trips': 0, 'redzone_touchdowns': 0, 'redzone_field_goals': 0, 'redzone_failed': 0, 'redzone_td_pct': 0.0}
        
        rz_plays = data[(data['yardline_100'] <= self._constants.RED_ZONE_YARDLINE) & (data['yardline_100'] > 0)]
        if len(rz_plays) == 0:
            return {'redzone_trips': 0, 'redzone_touchdowns': 0, 'redzone_field_goals': 0, 'redzone_failed': 0, 'redzone_td_pct': 0.0}
        
        try:
            rz_drives = rz_plays.groupby(['game_id', 'drive']).agg({
                'touchdown': 'max',
                'field_goal_result': lambda x: (x == 'made').any() if 'field_goal_result' in rz_plays.columns else False
            }).reset_index()
            
            trips = len(rz_drives)
            touchdowns = self._safe_sum(rz_drives['touchdown'])
            field_goals = self._safe_sum(rz_drives['field_goal_result']) if 'field_goal_result' in rz_drives.columns else 0
            failed = max(0, trips - touchdowns - field_goals)
            td_pct = self._safe_percentage(touchdowns, trips)
            
            return {
                'redzone_trips': trips, 'redzone_touchdowns': touchdowns,
                'redzone_field_goals': field_goals, 'redzone_failed': failed, 'redzone_td_pct': td_pct
            }
        except Exception as e:
            logger.warning(f"Error calculating redzone stats: {e}")
            return {'redzone_trips': 0, 'redzone_touchdowns': 0, 'redzone_field_goals': 0, 'redzone_failed': 0, 'redzone_td_pct': 0.0}
    
    def _build_season_stats(self, team: Team, season: Season, games_played: int, 
                           stats: Dict) -> SeasonStats:
        """Build SeasonStats object from calculated statistics."""
        per_game = lambda x: x / games_played if games_played > 0 else 0.0
        
        return SeasonStats(
            team=team, season=season, games_played=games_played,
            total_plays=stats['total_plays'], total_yards=stats['total_yards'],
            avg_yards_per_play=stats['avg_yards_per_play'],
            total_pass_attempts=stats.get('pass_attempts', 0),
            total_pass_completions=stats.get('pass_completions', 0),
            completion_pct=stats.get('completion_pct', 0.0),
            total_rush_attempts=stats.get('rush_attempts', 0),
            total_rush_yards=stats.get('rush_yards', 0),
            rush_ypc=stats.get('rush_ypc', 0.0),
            total_turnovers=stats['total_turnovers'],
            total_interceptions=stats['interceptions'],
            total_fumbles_lost=stats['fumbles_lost'],
            turnovers_per_game=per_game(stats['total_turnovers']),
            total_third_downs=stats.get('third_down_attempts', 0),
            total_third_down_conversions=stats.get('third_down_conversions', 0),
            third_down_pct=stats.get('third_down_pct', 0.0),
            success_rate=stats.get('success_rate', 0.0),
            total_first_downs=stats.get('first_downs_total', 0),
            total_first_downs_rush=stats.get('first_downs_rush', 0),
            total_first_downs_pass=stats.get('first_downs_pass', 0),
            total_first_downs_penalty=stats.get('first_downs_penalty', 0),
            first_downs_per_game=per_game(stats.get('first_downs_total', 0)),
            total_sacks=stats.get('sacks', 0),
            sacks_per_game=per_game(stats.get('sacks', 0)),
            total_penalty_yards=stats.get('penalty_yards', 0),
            penalty_yards_per_game=per_game(stats.get('penalty_yards', 0)),
            total_drives=stats.get('drives', 0),
            total_touchdowns=stats.get('touchdowns', 0),
            total_offensive_points=stats.get('points', 0),
            total_extra_points=stats.get('extra_points', 0),
            total_two_point_conversions=stats.get('two_point_conversions', 0),
            total_field_goals=stats.get('field_goals', 0),
            points_per_drive=stats.get('points_per_drive', 0.0),
            total_redzone_trips=stats.get('redzone_trips', 0),
            total_redzone_tds=stats.get('redzone_touchdowns', 0),
            total_redzone_field_goals=stats.get('redzone_field_goals', 0),
            total_redzone_failed=stats.get('redzone_failed', 0),
            redzone_td_pct=stats.get('redzone_td_pct', 0.0),
            first_down_successful_plays=stats.get('first_down_successful', 0),
            first_down_total_plays=stats.get('first_down_total', 0),
            second_down_successful_plays=stats.get('second_down_successful', 0),
            second_down_total_plays=stats.get('second_down_total', 0),
            third_down_successful_plays=stats.get('third_down_successful', 0),
            third_down_total_plays=stats.get('third_down_total', 0),
            total_third_down_rush_conversions=stats.get('third_down_rush_conversions', 0),
            total_third_down_pass_conversions=stats.get('third_down_pass_conversions', 0)
        )
    
    # NOTE: _extract_aggregate_stats method removed to prevent confusion.
    # This calculator only uses raw play-by-play data to ensure consistent results.
    
    # === Helper Methods ===
    
    def _count_games(self, data: pd.DataFrame) -> int:
        """Count unique games played."""
        if 'game_id' not in data.columns:
            return 0
        return len(data['game_id'].unique())
    
    
    def _calculate_turnover_stats(self, data: pd.DataFrame) -> Dict:
        """Calculate turnover statistics using original logic."""
        interceptions = self._safe_sum(data.get('interception', pd.Series(dtype='int64')) == 1)
        fumbles_lost = self._safe_sum(data.get('fumble_lost', pd.Series(dtype='int64')) == 1)
        
        # Calculate total using logical OR to avoid double-counting
        required_cols = ['interception', 'fumble_lost']
        if all(col in data.columns for col in required_cols):
            total_turnovers = self._safe_sum((data['interception'] == 1) | (data['fumble_lost'] == 1))
        else:
            total_turnovers = interceptions + fumbles_lost
        
        return {
            'interceptions': interceptions,
            'fumbles_lost': fumbles_lost,
            'total_turnovers': total_turnovers
        }
    
    
    def _identify_successful_plays(self, plays: pd.DataFrame) -> pd.Series:
        """Identify which plays meet success criteria by down."""
        if len(plays) == 0:
            return pd.Series([], dtype=bool)
        
        success_mask = np.where(
            plays['down'] == 1,
            plays['yards_gained'] >= self._constants.FIRST_DOWN_SUCCESS_THRESHOLD * plays['ydstogo'],
            np.where(
                plays['down'] == 2,
                plays['yards_gained'] >= self._constants.SECOND_DOWN_SUCCESS_THRESHOLD * plays['ydstogo'],
                plays['yards_gained'] >= self._constants.CONVERSION_SUCCESS_THRESHOLD * plays['ydstogo']
            )
        )
        
        return pd.Series(success_mask, index=plays.index)
    
    
    
    def _get_opponent_from_game_data(self, game_data: pd.DataFrame, team_abbr: str) -> str:
        """Extract opponent from game data."""
        if 'defteam' in game_data.columns:
            opponents = game_data['defteam'].dropna().unique()
            if len(opponents) > 0:
                return str(opponents[0])
        
        if 'home_team' in game_data.columns and 'away_team' in game_data.columns:
            first_row = game_data.iloc[0]
            home_team = first_row.get('home_team')
            away_team = first_row.get('away_team')
            
            if home_team == team_abbr:
                return str(away_team)
            elif away_team == team_abbr:
                return str(home_team)
        
        return "Unknown"
    
    def _determine_location(self, game_data: pd.DataFrame, team_abbr: str):
        """Determine if team was home or away for this game."""
        from .entities import Location
        
        if 'home_team' in game_data.columns:
            first_row = game_data.iloc[0]
            home_team = first_row.get('home_team')
            if home_team == team_abbr:
                return Location.HOME
            else:
                return Location.AWAY
        
        return Location.HOME  # Default fallback
    
    def _create_empty_season_stats(self, team: Team, season: Season) -> SeasonStats:
        """Create empty season stats for error cases."""
        return SeasonStats(
            team=team,
            season=season,
            games_played=0,
            avg_yards_per_play=0.0,
            total_yards=0,
            total_plays=0,
            turnovers_per_game=0.0,
            completion_pct=0.0,
            rush_ypc=0.0,
            sacks_per_game=0.0,
            third_down_pct=0.0,
            success_rate=0.0,
            first_downs_per_game=0.0,
            points_per_drive=0.0,
            redzone_td_pct=0.0,
            penalty_yards_per_game=0.0
        )