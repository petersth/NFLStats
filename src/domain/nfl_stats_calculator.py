# src/domain/nfl_stats_calculator.py - NFL statistics calculator

import logging
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

from .entities import Team, Season, SeasonStats, GameStats, TeamRecord
from .utilities import PlayFilter
from .toer_calculator import TOERCalculator
from ..config.nfl_constants import (
    TOUCHDOWN_POINTS, EXTRA_POINT_POINTS, TWO_POINT_CONVERSION_POINTS,
    FIELD_GOAL_POINTS, RED_ZONE_YARDLINE, FIRST_DOWN_SUCCESS_THRESHOLD,
    SECOND_DOWN_SUCCESS_THRESHOLD, CONVERSION_SUCCESS_THRESHOLD
)
from ..infrastructure.cache.simple_cache import SimpleCache

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
        
        # Cache for game stats with reasonable TTL and size limits
        self._game_stats_cache = SimpleCache(
            default_ttl=86400,  # 1 day TTL for game stats
            max_size=1000       # Reasonable limit for game stats
        )
        
        logger.debug("Initialized NFLStatsCalculator with game stats caching")
    
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
            
            # Calculate average TOER from individual game TOER scores
            # Optimize by only calculating TOER scores, not full game stats
            toer_scores = self._calculate_game_toer_scores(team_data, team.abbreviation)
            if toer_scores:
                avg_toer = sum(toer_scores) / len(toer_scores)
                stats['avg_toer'] = avg_toer
            else:
                stats['avg_toer'] = 0.0
            
            return self._build_season_stats(team, season, games_played, stats)
            
        except Exception as e:
            logger.error(f"Error calculating season stats for {team.abbreviation}: {e}")
            return self._create_empty_season_stats(team, season)
    
    
    def _calculate_game_toer_scores(self, team_data: pd.DataFrame, team_abbr: str) -> List[float]:
        """Calculate only TOER scores for each game (optimized for averaging)."""
        try:
            if len(team_data) == 0 or 'game_id' not in team_data.columns:
                return []
            
            toer_scores = []
            for game_id in team_data['game_id'].unique():
                game_data = team_data[team_data['game_id'] == game_id]
                
                # Calculate just what we need for TOER
                game_stats_dict = self._calculate_all_stats(game_data, team_abbr)
                
                offensive_plays = self._play_filter.get_offensive_plays(game_data)
                total_yards = int(offensive_plays['yards_gained'].sum()) if len(offensive_plays) > 0 else 0
                total_plays = len(offensive_plays)
                yards_per_play = total_yards / total_plays if total_plays > 0 else 0.0
                
                # Calculate TOER for this game
                toer_score = TOERCalculator.calculate_toer(
                    avg_yards_per_play=yards_per_play,
                    turnovers=int(game_stats_dict.get('total_turnovers', 0)),
                    completion_pct=game_stats_dict.get('completion_pct', 0.0),
                    rush_ypc=game_stats_dict.get('rush_ypc', 0.0),
                    sacks=int(game_stats_dict.get('sacks', 0)),
                    third_down_pct=game_stats_dict.get('third_down_pct', 0.0),
                    success_rate=game_stats_dict.get('success_rate', 0.0),
                    first_downs=float(game_stats_dict.get('first_downs_total', 0)),
                    points_per_drive=game_stats_dict.get('points_per_drive', 0.0),
                    redzone_td_pct=game_stats_dict.get('redzone_td_pct', 0.0),
                    penalty_yards=int(game_stats_dict.get('penalty_yards', 0))
                )
                
                toer_scores.append(toer_score)
            
            return toer_scores
            
        except Exception as e:
            logger.error(f"Error calculating game TOER scores for {team_abbr}: {e}")
            return []
    
    def calculate_game_stats(self, team_data: pd.DataFrame, team: Team) -> List[GameStats]:
        """Calculate game-by-game statistics with caching."""
        try:
            if len(team_data) == 0 or 'game_id' not in team_data.columns:
                return []
            
            # Create a cache key based on team and data characteristics
            import hashlib
            data_hash = f"{team.abbreviation}_{len(team_data)}_{team_data.index.min()}_{team_data.index.max()}"
            cache_key = hashlib.md5(data_hash.encode()).hexdigest()
            
            def compute_game_stats():
                """Compute game statistics for the team."""
                return self._compute_all_game_stats(team_data, team)
            
            def validate_game_stats(stats):
                """Validate computed game statistics."""
                return (isinstance(stats, list) and 
                       all(isinstance(stat, GameStats) for stat in stats))
            
            # Use cached computation
            return self._game_stats_cache.get_or_compute(
                key=cache_key,
                compute_func=compute_game_stats,
                validator=validate_game_stats
            )
            
        except Exception as e:
            logger.error(f"Error calculating game stats for {team.abbreviation}: {e}")
            return []
    
    def _compute_all_game_stats(self, team_data: pd.DataFrame, team: Team) -> List[GameStats]:
        """Compute game statistics without caching (used by cache)."""
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
            
            # Calculate TOER for this game
            toer_score = TOERCalculator.calculate_toer(
                avg_yards_per_play=yards_per_play,
                turnovers=int(turnovers),
                completion_pct=completion_pct,
                rush_ypc=rush_ypc,
                sacks=int(sacks_allowed),
                third_down_pct=third_down_pct,
                success_rate=success_rate,
                first_downs=float(first_downs),
                points_per_drive=points_per_drive,
                redzone_td_pct=redzone_td_pct,
                penalty_yards=int(penalty_yards)
            )
            
            # Determine opponent
            opponent = self._get_opponent_from_game_data(game_data, team.abbreviation)
            opponent_team = Team.from_abbreviation(opponent) if opponent != "Unknown" else team
            
            # Extract game information from data
            week = int(game_data['week'].iloc[0]) if 'week' in game_data.columns else 0
            season_year = int(game_data['season'].iloc[0]) if 'season' in game_data.columns else 0
            game_date = str(game_data['game_date'].iloc[0]) if 'game_date' in game_data.columns else ""
            season_type = str(game_data['season_type'].iloc[0]) if 'season_type' in game_data.columns else "REG"
            home_team_abbr = str(game_data['home_team'].iloc[0]) if 'home_team' in game_data.columns else ""
            away_team_abbr = str(game_data['away_team'].iloc[0]) if 'away_team' in game_data.columns else ""
            
            # Create Game object
            from .entities import Game, Season, GameType
            game_obj = Game(
                game_id=game_id,
                season=Season(season_year),
                week=week,
                game_date=game_date,
                home_team=Team.from_abbreviation(home_team_abbr) if home_team_abbr else team,
                away_team=Team.from_abbreviation(away_team_abbr) if away_team_abbr else opponent_team,
                game_type=GameType.PLAYOFF if season_type == "POST" else GameType.REGULAR
            )
            
            # Create game stats object
            game_stat = GameStats(
                game=game_obj,
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
                toer=toer_score
            )
            game_stats.append(game_stat)
        
        # Sort games by week number
        game_stats.sort(key=lambda x: x.game.week if x.game else 0)
        
        logger.debug(f"Computed game stats for {team.abbreviation}: {len(game_stats)} games")
        return game_stats
    
    def get_cache_stats(self) -> Dict:
        """Get game stats cache statistics."""
        return {
            'cache_type': 'nfl_stats_game_cache',
            'description': 'Game statistics cache with TTL validation',
            'stats': self._game_stats_cache.get_stats()
        }

    def calculate_team_record(self, team_data: pd.DataFrame, team_abbreviation: str) -> Optional[TeamRecord]:
        """Calculate team's win-loss record."""
        try:
            if len(team_data) == 0 or 'game_id' not in team_data.columns:
                return None
            
            # Get unique games and try to determine wins/losses, separated by season type
            games = team_data['game_id'].unique()
            reg_wins = reg_losses = reg_ties = 0
            playoff_wins = playoff_losses = 0
            
            for game_id in games:
                game_data = team_data[team_data['game_id'] == game_id]
                
                # Try to determine game result from score columns if available
                if 'home_score' in game_data.columns and 'away_score' in game_data.columns:
                    final_play = game_data.iloc[-1]
                    home_score = final_play['home_score']
                    away_score = final_play['away_score']
                    home_team = final_play.get('home_team', '')
                    away_team = final_play.get('away_team', '')
                    season_type = final_play.get('season_type', 'REG')
                    
                    # Determine if our team won based on whether they were home or away
                    if home_team == team_abbreviation:
                        team_score = home_score
                        opp_score = away_score
                    elif away_team == team_abbreviation:
                        team_score = away_score
                        opp_score = home_score
                    else:
                        # Skip this game if we can't determine the team
                        continue
                    
                    # Determine win/loss/tie
                    if team_score > opp_score:
                        if season_type == 'POST':
                            playoff_wins += 1
                        else:
                            reg_wins += 1
                    elif team_score < opp_score:
                        if season_type == 'POST':
                            playoff_losses += 1
                        else:
                            reg_losses += 1
                    else:
                        if season_type != 'POST':
                            reg_ties += 1            

            return TeamRecord(
                regular_season_wins=reg_wins, 
                regular_season_losses=reg_losses,
                regular_season_ties=reg_ties,
                playoff_wins=playoff_wins,
                playoff_losses=playoff_losses
            )
            
        except Exception as e:
            logger.error(f"Error calculating team record for {team_abbreviation}: {e}")
            return TeamRecord(
                regular_season_wins=0, 
                regular_season_losses=0,
                regular_season_ties=0,
                playoff_wins=0,
                playoff_losses=0
            )
    
    # === Consolidated Calculation Methods ===
    
    def _calculate_all_stats(self, data: pd.DataFrame, team_abbr: str) -> Dict:
        """Calculate all statistics in one consolidated method with single-pass filtering."""
        # Pre-filter all play types once to avoid redundant filtering
        offensive_plays = self._play_filter.get_offensive_plays(data)
        passing_plays = self._play_filter.get_passing_plays(data)
        rushing_plays = self._play_filter.get_rushing_plays(data)
        third_down_attempts = self._play_filter.get_third_down_attempts(data)
        
        # Calculate success-eligible plays
        success_eligible_plays = offensive_plays[offensive_plays['ydstogo'].notna()].copy()
        success_eligible_plays = self._play_filter.apply_success_rate_exclusions(success_eligible_plays)
        
        return {
            'total_plays': len(offensive_plays),
            'total_yards': self._safe_sum(offensive_plays['yards_gained']),
            'avg_yards_per_play': self._safe_mean(offensive_plays['yards_gained']),
            **self._calculate_passing_rushing_stats_optimized(passing_plays, rushing_plays),
            **self._calculate_turnover_stats(data),
            **self._calculate_down_stats(data),  # Use original method to get first downs
            **self._calculate_success_stats_optimized(success_eligible_plays),
            **self._calculate_team_specific_stats(data, team_abbr)
        }
    
    def _calculate_passing_rushing_stats_optimized(self, passing_plays: pd.DataFrame, rushing_plays: pd.DataFrame) -> Dict:
        """Calculate passing and rushing stats using pre-filtered data."""
        return {
            'pass_attempts': len(passing_plays),
            'pass_completions': self._safe_sum(passing_plays.get('complete_pass', pd.Series(dtype='int64'))),
            'completion_pct': self._safe_percentage(
                self._safe_sum(passing_plays.get('complete_pass', pd.Series(dtype='int64'))), len(passing_plays)
            ),
            'rush_attempts': len(rushing_plays),
            'rush_yards': self._safe_sum(rushing_plays['yards_gained']),
            'rush_ypc': self._safe_mean(rushing_plays['yards_gained'])
        }
    
    def _calculate_down_stats_optimized(self, third_down_attempts: pd.DataFrame) -> Dict:
        """Calculate down-specific statistics using pre-filtered data."""
        required_cols = ['first_down', 'touchdown']
        
        if not all(col in third_down_attempts.columns for col in required_cols):
            third_down_conversions = 0
            third_down_pct = 0.0
        else:
            third_down_conversions = self._safe_sum(
                (third_down_attempts['first_down'] == 1) | (third_down_attempts['touchdown'] == 1)
            )
            third_down_pct = self._safe_percentage(third_down_conversions, len(third_down_attempts))
        
        return {
            'third_down_conversions': third_down_conversions,
            'third_down_attempts': len(third_down_attempts),
            'third_down_pct': third_down_pct
        }
    
    def _calculate_success_stats_optimized(self, success_eligible_plays: pd.DataFrame) -> Dict:
        """Calculate success rate statistics using pre-filtered data."""
        if len(success_eligible_plays) == 0:
            return {
                'success_rate': 0.0,
                'first_down_successful': 0, 'first_down_total': 0,
                'second_down_successful': 0, 'second_down_total': 0,
                'third_down_successful': 0, 'third_down_total': 0
            }
        
        # Calculate success for each play
        success_eligible_plays = success_eligible_plays.copy()
        success_eligible_plays['success'] = self._identify_successful_plays(success_eligible_plays)
        
        # Overall success rate
        successful_plays = self._safe_sum(success_eligible_plays['success'])
        success_rate = self._safe_percentage(successful_plays, len(success_eligible_plays))
        
        # Down-specific success rates
        first_downs = success_eligible_plays[success_eligible_plays['down'] == 1]
        second_downs = success_eligible_plays[success_eligible_plays['down'] == 2]
        third_downs = success_eligible_plays[success_eligible_plays['down'] == 3]
        
        return {
            'success_rate': success_rate,
            'first_down_successful': self._safe_sum(first_downs['success']),
            'first_down_total': len(first_downs),
            'second_down_successful': self._safe_sum(second_downs['success']),
            'second_down_total': len(second_downs),
            'third_down_successful': self._safe_sum(third_downs['success']),
            'third_down_total': len(third_downs)
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
        
        # First downs - apply exclusion filtering for accuracy
        first_down_cols = ['first_down_rush', 'first_down_pass', 'first_down_penalty']
        if all(col in data.columns for col in first_down_cols):
            # Apply exclusion filtering to first downs data
            filtered_first_downs_data = self._apply_first_downs_exclusions(data)
            
            first_downs_rush = self._safe_sum(filtered_first_downs_data['first_down_rush'] == 1)
            first_downs_pass = self._safe_sum(filtered_first_downs_data['first_down_pass'] == 1)
            first_downs_penalty = self._safe_sum(filtered_first_downs_data['first_down_penalty'] == 1)
            first_downs_total = self._safe_sum(
                (filtered_first_downs_data['first_down_rush'] == 1) | 
                (filtered_first_downs_data['first_down_pass'] == 1) | 
                (filtered_first_downs_data['first_down_penalty'] == 1)
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
        
        # Calculate TOER score as average of individual game TOER scores
        toer_score = stats.get('avg_toer', 0.0)
        
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
            toer=toer_score,
            first_down_successful_plays=stats.get('first_down_successful', 0),
            first_down_total_plays=stats.get('first_down_total', 0),
            second_down_successful_plays=stats.get('second_down_successful', 0),
            second_down_total_plays=stats.get('second_down_total', 0),
            third_down_successful_plays=stats.get('third_down_successful', 0),
            third_down_total_plays=stats.get('third_down_total', 0),
            total_third_down_rush_conversions=stats.get('third_down_rush_conversions', 0),
            total_third_down_pass_conversions=stats.get('third_down_pass_conversions', 0)
        )
    
    
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
        """Identify which plays meet NFL success rate criteria by down.
        
        Success rate methodology follows established NFL analytics standards:
        - 1st down: Gain >= 40% of yards to go (establishes manageable down & distance)
        - 2nd down: Gain >= 60% of yards to go (puts team in favorable 3rd down position)  
        - 3rd/4th down: Gain >= 100% of yards to go (achieves conversion)
        
        This creates a context-aware success metric that accounts for down and distance
        situations, providing better insight than raw yards per play.
        
        Args:
            plays: DataFrame containing plays with 'down', 'yards_gained', and 'ydstogo' columns
            
        Returns:
            Series of boolean values indicating whether each play was "successful"
        """
        if len(plays) == 0:
            return pd.Series([], dtype=bool)
        
        # Apply down-specific success thresholds using NFL analytics standards
        success_mask = np.where(
            plays['down'] == 1,
            plays['yards_gained'] >= self._constants.FIRST_DOWN_SUCCESS_THRESHOLD * plays['ydstogo'],
            np.where(
                plays['down'] == 2,
                plays['yards_gained'] >= self._constants.SECOND_DOWN_SUCCESS_THRESHOLD * plays['ydstogo'],
                # 3rd/4th down: must achieve conversion (100% of yards needed)
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
    
    def _apply_first_downs_exclusions(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply configuration-based exclusions for first downs calculations.
        
        First downs can be affected by kneels and spikes since they represent
        plays that achieved first downs but may be excluded based on configuration.
        """
        if len(data) == 0:
            return data
        
        filtered_data = data.copy()
        
        # Apply QB kneel filtering - exclude when configured for rushing or success rate exclusion
        if '_qb_kneel_context' in filtered_data.columns:
            # First downs from rushing can be affected by kneel exclusions
            # First downs from passing can be affected by success rate exclusions
            filtered_data = filtered_data[
                ~filtered_data['_qb_kneel_context'].isin(['exclude_rushing', 'exclude_success_rate'])
            ]
        
        # Apply spike filtering - exclude when configured for completion or success rate exclusion
        if '_spike_context' in filtered_data.columns:
            # First downs from passing can be affected by spike exclusions
            filtered_data = filtered_data[
                ~filtered_data['_spike_context'].isin(['exclude_completion', 'exclude_success_rate', 'exclude_both'])
            ]
        
        return filtered_data
    
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
            penalty_yards_per_game=0.0,
            toer=0.0
        )