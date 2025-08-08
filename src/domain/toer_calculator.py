# src/domain/toer_calculator.py

"""
Total Offensive Efficiency Rating (TOER) Calculator
Calculates a composite offensive efficiency score from 0-100 based on 11 key metrics.
"""

import logging
import yaml
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable, Tuple

logger = logging.getLogger(__name__)


class TOERValidationError(ValueError):
    """Raised when TOER calculation inputs are invalid."""
    pass


class TOERCalculator:
    """Calculates Total Offensive Efficiency Rating (TOER) from offensive metrics."""
    
    _config = None
    _scorers = None
    
    @classmethod
    def _load_config(cls) -> Dict[str, Any]:
        """Load scoring configuration from YAML file."""
        if cls._config is None:
            config_path = Path(__file__).parent.parent / "config" / "toer_scoring_config.yaml"
            with open(config_path, 'r') as f:
                cls._config = yaml.safe_load(f)
            logger.debug("Loaded TOER configuration from YAML file")
        return cls._config
    
    @classmethod
    def _parse_condition(cls, condition: str) -> Optional[Callable[[float], bool]]:
        """Parse a condition string into a callable test function."""
        original_condition = condition
        
        # Extract variable name from condition
        var_names = ['ypp', 'comp_pct', 'ypc', 'third_down_pct', 'success_rate', 
                    'first_downs', 'ppd', 'redzone_td_pct', 'penalty_yards']
        
        for var in var_names:
            if var in condition:
                condition = condition.replace(var, '').strip()
                break
        
        # Parse different condition types
        try:
            # Equality check
            if '==' in condition:
                value = float(condition.replace('==', '').strip())
                return lambda v: abs(v - value) < 1e-9 if not isinstance(v, int) else int(v) == int(value)
            
            # Greater than or equal
            elif '>=' in condition:
                value = float(condition.replace('>=', '').strip())
                return lambda v: v >= value
            
            # Greater than
            elif '>' in condition:
                value = float(condition.replace('>', '').strip())
                return lambda v: v > value
            
            # Less than or equal
            elif '<=' in condition and condition.count('<=') == 1:
                value = float(condition.replace('<=', '').strip())
                return lambda v: v <= value
            
            # Less than
            elif '<' in condition:
                value = float(condition.replace('<', '').strip())
                return lambda v: v < value
            
            # Range (e.g., "5.45 <= ypp <= 5.49")
            elif condition.count('<=') == 2:
                parts = original_condition.split('<=')
                if len(parts) == 3:
                    # Extract min and max values
                    min_val = float(re.findall(r'[\d.]+', parts[0])[0])
                    max_val = float(re.findall(r'[\d.]+', parts[2])[0])
                    return lambda v: min_val <= v <= max_val
            
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse condition '{original_condition}': {e}")
        
        return None
    
    @classmethod
    def _create_threshold_scorer(cls, rules: List[Tuple[Callable, int]], 
                                default_score: int, first_match: bool = False) -> Callable:
        """Create a scoring function from threshold rules."""
        def scorer(value: float) -> int:
            if first_match:
                for test_func, score in rules:
                    if test_func(value):
                        return score
            else:
                matching_scores = [score for test_func, score in rules if test_func(value)]
                if matching_scores:
                    return max(matching_scores)
            return default_score
        return scorer
    
    @classmethod
    def _build_scorers(cls) -> Dict[str, Callable]:
        """Build scoring functions for each metric."""
        if cls._scorers is not None:
            return cls._scorers
        
        config = cls._load_config()
        scorers = {}
        
        for metric_name, metric_config in config.items():
            if 'thresholds' in metric_config:
                rules = []
                default_score = 0
                
                for threshold in metric_config['thresholds']:
                    condition = threshold['condition']
                    score = threshold['score']
                    
                    if condition == 'default':
                        default_score = score
                    else:
                        parsed = cls._parse_condition(condition)
                        if parsed:
                            rules.append((parsed, score))
                
                scorers[metric_name] = cls._create_threshold_scorer(
                    rules, default_score, 
                    first_match=(metric_name == 'penalty_yards')
                )
            
            elif 'exact_values' in metric_config:
                exact_dict = {}
                for item in metric_config['exact_values']:
                    exact_dict[item['value']] = item['score']
                
                default = metric_config['default_score']
                scorers[metric_name] = lambda v, lookup=exact_dict, default_score=default: (
                    lookup.get(int(v) if isinstance(v, float) and v.is_integer() else v, default_score)
                )
        
        cls._scorers = scorers
        logger.debug("Built scoring functions")
        return scorers
    
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
    
    @classmethod
    def calculate_yards_per_play_score(cls, ypp: float) -> int:
        """Calculate YPP component score (0-10 points)."""
        cls._validate_non_negative(ypp, "yards_per_play", 20.0)
        scorers = cls._build_scorers()
        return scorers['yards_per_play'](ypp)
    
    @classmethod
    def calculate_turnovers_score(cls, turnovers: int) -> int:
        """Calculate turnovers component score (-5 to 10 points)."""
        if turnovers < 0:
            raise TOERValidationError(f"turnovers cannot be negative: {turnovers}")
        if turnovers > 10:
            raise TOERValidationError(f"turnovers seems unrealistic: {turnovers} (max reasonable: 10)")
        scorers = cls._build_scorers()
        return scorers['turnovers'](turnovers)
    
    @classmethod
    def calculate_completion_pct_score(cls, comp_pct: float) -> int:
        """Calculate completion percentage component score (0-10 points)."""
        cls._validate_percentage(comp_pct, "completion_percentage")
        scorers = cls._build_scorers()
        return scorers['completion_percentage'](comp_pct)
    
    @classmethod
    def calculate_rush_ypc_score(cls, ypc: float) -> int:
        """Calculate rushing YPC component score (0-10 points)."""
        cls._validate_non_negative(ypc, "rush_yards_per_carry", 15.0)
        scorers = cls._build_scorers()
        return scorers['rush_yards_per_carry'](ypc)
    
    @classmethod
    def calculate_sacks_score(cls, sacks: int) -> int:
        """Calculate sacks allowed component score (-3 to 10 points)."""
        if sacks < 0:
            raise TOERValidationError(f"sacks cannot be negative: {sacks}")
        if sacks > 15:
            raise TOERValidationError(f"sacks seems unrealistic: {sacks} (max reasonable: 15)")
        scorers = cls._build_scorers()
        return scorers['sacks'](sacks)
    
    @classmethod
    def calculate_third_down_score(cls, third_down_pct: float) -> int:
        """Calculate third down conversion component score (0-10 points)."""
        cls._validate_percentage(third_down_pct, "third_down_percentage")
        scorers = cls._build_scorers()
        return scorers['third_down_percentage'](third_down_pct)
    
    @classmethod
    def calculate_success_rate_score(cls, success_rate: float) -> int:
        """Calculate play success rate component score (0-10 points)."""
        cls._validate_percentage(success_rate, "success_rate")
        scorers = cls._build_scorers()
        return scorers['success_rate'](success_rate)
    
    @classmethod
    def calculate_first_downs_score(cls, first_downs: float) -> int:
        """Calculate first downs component score (0-10 points)."""
        cls._validate_non_negative(first_downs, "first_downs", 50.0)
        scorers = cls._build_scorers()
        return scorers['first_downs'](first_downs)
    
    @classmethod
    def calculate_ppd_score(cls, ppd: float) -> int:
        """Calculate points per drive component score (0-10 points)."""
        cls._validate_non_negative(ppd, "points_per_drive", 8.0)
        scorers = cls._build_scorers()
        return scorers['points_per_drive'](ppd)
    
    @classmethod
    def calculate_redzone_score(cls, redzone_td_pct: float) -> int:
        """Calculate red zone TD percentage component score (0-10 points)."""
        cls._validate_percentage(redzone_td_pct, "redzone_td_percentage")
        scorers = cls._build_scorers()
        return scorers['redzone_td_percentage'](redzone_td_pct)
    
    @classmethod
    def calculate_penalty_yards_adjustment(cls, penalty_yards: int) -> int:
        """Calculate penalty yards adjustment (-10 to +5 points)."""
        if penalty_yards < 0:
            raise TOERValidationError(f"penalty_yards cannot be negative: {penalty_yards}")
        if penalty_yards > 300:
            raise TOERValidationError(f"penalty_yards seems unrealistic: {penalty_yards} (max reasonable: 300)")
        scorers = cls._build_scorers()
        return scorers['penalty_yards'](penalty_yards)
    
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