# src/domain/toer_calculator.py

"""
Total Offensive Efficiency Rating (TOER) Calculator
Calculates a composite offensive efficiency score from 0-100 based on 11 key metrics.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TOERValidationError(ValueError):
    """Raised when TOER calculation inputs are invalid."""
    pass


class TOERCalculator:
    """Calculates Total Offensive Efficiency Rating (TOER) from offensive metrics."""
    
    @staticmethod
    def _validate_non_negative(value: float, param_name: str, max_reasonable: Optional[float] = None) -> None:
        """Validate that a value is non-negative and within reasonable bounds."""
        if value < 0:
            raise TOERValidationError(f"{param_name} cannot be negative: {value}")
        if max_reasonable is not None and value > max_reasonable:
            raise TOERValidationError(f"{param_name} seems unrealistic: {value} (max reasonable: {max_reasonable})")
    
    @staticmethod
    def _validate_percentage(value: float, param_name: str) -> None:
        """Validate that a percentage value is between 0 and 100."""
        if value < 0 or value > 100:
            raise TOERValidationError(f"{param_name} must be between 0 and 100: {value}")
    
    @staticmethod
    def calculate_yards_per_play_score(ypp: float) -> int:
        """Calculate YPP component score (0-10 points)."""
        TOERCalculator._validate_non_negative(ypp, "yards_per_play", 20.0)
        if ypp > 5.5:
            return 10
        elif ypp == 5.5:
            return 9
        elif 5.45 <= ypp <= 5.49:
            return 8
        elif 5.40 <= ypp <= 5.44:
            return 7
        elif 5.35 <= ypp <= 5.39:
            return 6
        elif 5.30 <= ypp <= 5.34:
            return 5
        elif 5.25 <= ypp <= 5.29:
            return 4
        elif 5.20 <= ypp <= 5.24:
            return 3
        elif 5.15 <= ypp <= 5.19:
            return 2
        elif 5.10 <= ypp <= 5.14:
            return 1
        else:
            return 0
    
    @staticmethod
    def calculate_turnovers_score(turnovers: int) -> int:
        """Calculate turnovers component score (-5 to 10 points)."""
        if turnovers < 0:
            raise TOERValidationError(f"turnovers cannot be negative: {turnovers}")
        if turnovers > 10:
            raise TOERValidationError(f"turnovers seems unrealistic: {turnovers} (max reasonable: 10)")
        if turnovers == 0:
            return 10
        elif turnovers == 1:
            return 5
        elif turnovers == 2:
            return 0
        elif turnovers == 3:
            return -3
        elif turnovers == 4:
            return -4
        else:
            return -5
    
    @staticmethod
    def calculate_completion_pct_score(comp_pct: float) -> int:
        """Calculate completion percentage component score (0-10 points)."""
        TOERCalculator._validate_percentage(comp_pct, "completion_percentage")
        if comp_pct >= 67.5:
            return 10
        elif 67.0 <= comp_pct <= 67.49:
            return 9
        elif 66.5 <= comp_pct <= 66.99:
            return 8
        elif 66.0 <= comp_pct <= 66.49:
            return 7
        elif 65.5 <= comp_pct <= 65.99:
            return 6
        elif 65.0 <= comp_pct <= 65.49:
            return 5
        elif 64.5 <= comp_pct <= 64.99:
            return 4
        elif 64.0 <= comp_pct <= 64.49:
            return 3
        elif 63.5 <= comp_pct <= 63.99:
            return 2
        elif 63.0 <= comp_pct <= 63.49:
            return 1
        else:
            return 0
    
    @staticmethod
    def calculate_rush_ypc_score(ypc: float) -> int:
        """Calculate rushing YPC component score (0-10 points)."""
        TOERCalculator._validate_non_negative(ypc, "rush_yards_per_carry", 15.0)
        if ypc >= 4.7:
            return 10
        elif 4.65 <= ypc <= 4.69:
            return 9
        elif 4.60 <= ypc <= 4.64:
            return 8
        elif 4.55 <= ypc <= 4.59:
            return 7
        elif 4.50 <= ypc <= 4.54:
            return 6
        elif 4.45 <= ypc <= 4.49:
            return 5
        elif 4.40 <= ypc <= 4.44:
            return 4
        elif 4.35 <= ypc <= 4.39:
            return 3
        elif 4.30 <= ypc <= 4.34:
            return 2
        elif 4.20 <= ypc <= 4.29:
            return 1
        else:
            return 0
    
    @staticmethod
    def calculate_sacks_score(sacks: int) -> int:
        """Calculate sacks allowed component score (-3 to 10 points)."""
        if sacks < 0:
            raise TOERValidationError(f"sacks cannot be negative: {sacks}")
        if sacks > 15:
            raise TOERValidationError(f"sacks seems unrealistic: {sacks} (max reasonable: 15)")
        if sacks == 0:
            return 10
        elif sacks == 1:
            return 8
        elif sacks == 2:
            return 5
        elif sacks == 3:
            return 0
        elif sacks == 4:
            return -1
        else:
            return -3
    
    @staticmethod
    def calculate_third_down_score(third_down_pct: float) -> int:
        """Calculate third down conversion component score (0-10 points)."""
        TOERCalculator._validate_percentage(third_down_pct, "third_down_percentage")
        if third_down_pct >= 43.0:
            return 10
        elif 42.0 <= third_down_pct <= 42.99:
            return 9
        elif 41.0 <= third_down_pct <= 41.99:
            return 8
        elif 40.0 <= third_down_pct <= 40.99:
            return 7
        elif 39.0 <= third_down_pct <= 39.99:
            return 6
        elif 38.0 <= third_down_pct <= 38.99:
            return 5
        elif 37.0 <= third_down_pct <= 37.99:
            return 4
        elif 36.0 <= third_down_pct <= 36.99:
            return 3
        elif 35.0 <= third_down_pct <= 35.99:
            return 2
        elif 33.0 <= third_down_pct <= 34.99:
            return 1
        else:
            return 0
    
    @staticmethod
    def calculate_success_rate_score(success_rate: float) -> int:
        """Calculate play success rate component score (0-10 points)."""
        TOERCalculator._validate_percentage(success_rate, "success_rate")
        if success_rate >= 47.0:
            return 10
        elif 46.0 <= success_rate <= 46.99:
            return 9
        elif 45.0 <= success_rate <= 45.99:
            return 8
        elif 44.0 <= success_rate <= 44.99:
            return 7
        elif 43.0 <= success_rate <= 43.99:
            return 6
        elif 42.0 <= success_rate <= 42.99:
            return 5
        elif 41.0 <= success_rate <= 41.99:
            return 4
        elif 40.0 <= success_rate <= 40.99:
            return 3
        else:
            return 0
    
    @staticmethod
    def calculate_first_downs_score(first_downs: float) -> int:
        """Calculate first downs component score (0-10 points)."""
        TOERCalculator._validate_non_negative(first_downs, "first_downs", 50.0)
        if first_downs >= 22:
            return 10
        elif first_downs >= 21:
            return 9
        elif first_downs >= 20:
            return 8
        elif first_downs >= 19:
            return 7
        elif first_downs >= 18:
            return 6
        elif first_downs >= 17:
            return 5
        else:
            return 0
    
    @staticmethod
    def calculate_ppd_score(ppd: float) -> int:
        """Calculate points per drive component score (0-10 points)."""
        TOERCalculator._validate_non_negative(ppd, "points_per_drive", 8.0)
        if ppd >= 2.4:
            return 10
        elif 2.35 <= ppd <= 2.39:
            return 9
        elif 2.30 <= ppd <= 2.34:
            return 8
        elif 2.25 <= ppd <= 2.29:
            return 7
        elif 2.20 <= ppd <= 2.24:
            return 6
        elif 2.10 <= ppd <= 2.19:
            return 5
        elif 2.00 <= ppd <= 2.09:
            return 4
        elif 1.90 <= ppd <= 1.99:
            return 3
        elif 1.85 <= ppd <= 1.89:
            return 2
        elif 1.80 <= ppd <= 1.84:
            return 1
        else:
            return 0
    
    @staticmethod
    def calculate_redzone_score(redzone_td_pct: float) -> int:
        """Calculate red zone TD percentage component score (0-10 points)."""
        TOERCalculator._validate_percentage(redzone_td_pct, "redzone_td_percentage")
        if redzone_td_pct >= 63.0:
            return 10
        elif 61.0 <= redzone_td_pct <= 62.99:
            return 9
        elif 60.0 <= redzone_td_pct <= 60.99:
            return 8
        elif 59.0 <= redzone_td_pct <= 59.99:
            return 7
        elif 58.0 <= redzone_td_pct <= 58.99:
            return 6
        elif 57.0 <= redzone_td_pct <= 57.99:
            return 5
        else:
            return 0
    
    @staticmethod
    def calculate_penalty_yards_adjustment(penalty_yards: int) -> int:
        """Calculate penalty yards adjustment (-10 to +5 points)."""
        if penalty_yards < 0:
            raise TOERValidationError(f"penalty_yards cannot be negative: {penalty_yards}")
        if penalty_yards > 300:
            raise TOERValidationError(f"penalty_yards seems unrealistic: {penalty_yards} (max reasonable: 300)")
        if penalty_yards == 0:
            return 5
        elif 1 <= penalty_yards <= 10:
            return 3
        elif 11 <= penalty_yards <= 20:
            return 1
        elif 21 <= penalty_yards <= 30:
            return 0
        elif 31 <= penalty_yards <= 40:
            return -2
        elif 41 <= penalty_yards <= 50:
            return -4
        elif 51 <= penalty_yards <= 60:
            return -5
        elif 61 <= penalty_yards <= 70:
            return -6
        elif 71 <= penalty_yards <= 80:
            return -8
        elif 81 <= penalty_yards <= 90:
            return -9
        else:
            return -10
    
    @classmethod
    def calculate_toer(cls,
                      avg_yards_per_play: float,
                      turnovers: int,
                      completion_pct: float,
                      rush_ypc: float,
                      sacks: int,
                      third_down_pct: float,
                      success_rate: float,
                      first_downs: float,
                      points_per_drive: float,
                      redzone_td_pct: float,
                      penalty_yards: int) -> float:
        """
        Calculate Total Offensive Efficiency Rating (TOER).
        
        Args:
            avg_yards_per_play: Average yards per offensive play
            turnovers: Exact number of turnovers in the game (lower is better)
            completion_pct: Pass completion percentage
            rush_ypc: Rushing yards per carry
            sacks: Exact number of sacks allowed in the game (lower is better)
            third_down_pct: Third down conversion percentage
            success_rate: Play success rate percentage
            first_downs: First downs gained per game
            points_per_drive: Points scored per offensive drive
            redzone_td_pct: Red zone touchdown percentage
            penalty_yards: Exact penalty yards lost in the game (lower is better)
            
        Returns:
            TOER score between 0 and 100
        """
        try:
            # Calculate component scores
            scores = {
                'ypp': cls.calculate_yards_per_play_score(avg_yards_per_play),
                'turnovers': cls.calculate_turnovers_score(turnovers),
                'completion': cls.calculate_completion_pct_score(completion_pct),
                'rush_ypc': cls.calculate_rush_ypc_score(rush_ypc),
                'sacks': cls.calculate_sacks_score(sacks),
                'third_down': cls.calculate_third_down_score(third_down_pct),
                'success_rate': cls.calculate_success_rate_score(success_rate),
                'first_downs': cls.calculate_first_downs_score(first_downs),
                'ppd': cls.calculate_ppd_score(points_per_drive),
                'redzone': cls.calculate_redzone_score(redzone_td_pct),
                'penalty': cls.calculate_penalty_yards_adjustment(penalty_yards)
            }
            
            # Calculate total TOER
            # Base score from first 10 metrics
            base_score = sum([
                scores['ypp'],
                scores['turnovers'],
                scores['completion'],
                scores['rush_ypc'],
                scores['sacks'],
                scores['third_down'],
                scores['success_rate'],
                scores['first_downs'],
                scores['ppd'],
                scores['redzone']
            ])
            
            # Add penalty adjustment
            total_score = base_score + scores['penalty']
            
            # Ensure score is between 0 and 100
            toer = max(0, min(100, total_score))
            
            logger.debug(f"TOER Calculation - Components: {scores}, Base: {base_score}, Total: {total_score}, Final TOER: {toer}")
            
            return toer
            
        except Exception as e:
            logger.error(f"Error calculating TOER: {e}")
            return 0.0