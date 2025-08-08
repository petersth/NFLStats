# src/domain/toer_calculator.py

"""
Total Offensive Efficiency Rating (TOER) Calculator
Calculates a composite offensive efficiency score from 0-100 based on 11 key metrics.
"""

import logging
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Tuple

logger = logging.getLogger(__name__)


class TOERValidationError(ValueError):
    """Raised when TOER calculation inputs are invalid."""
    pass


class TOERCalculator:
    """Calculates Total Offensive Efficiency Rating (TOER) from offensive metrics."""
    
    _config = None
    _calculation_count = 0
    _lookup_tables = None
    
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
    def _build_lookup_tables(cls) -> Dict[str, Any]:
        """Build optimized lookup tables for fast scoring."""
        if cls._lookup_tables is not None:
            return cls._lookup_tables
        
        config = cls._load_config()
        tables = {}
        
        # For threshold-based metrics, create sorted lists for binary search
        for metric_name, metric_config in config.items():
            if 'thresholds' in metric_config:
                thresholds = metric_config['thresholds']
                # Convert conditions to numeric ranges for fast lookup
                ranges = []
                for threshold in thresholds:
                    condition = threshold['condition']
                    score = threshold['score']
                    
                    if condition == 'default':
                        ranges.append((float('-inf'), float('inf'), score, 'default'))
                    else:
                        # Parse common condition patterns into numeric ranges
                        range_data = cls._parse_condition_to_range(condition, score)
                        if range_data:
                            ranges.append(range_data)
                
                # Sort by lower bound for efficient lookup
                ranges.sort(key=lambda x: x[0])
                tables[metric_name] = {'type': 'ranges', 'data': ranges}
            
            elif 'exact_values' in metric_config:
                # For exact values, create a simple dict lookup
                exact_dict = {}
                for item in metric_config['exact_values']:
                    exact_dict[item['value']] = item['score']
                tables[metric_name] = {
                    'type': 'exact',
                    'data': exact_dict,
                    'default': metric_config['default_score']
                }
        
        cls._lookup_tables = tables
        logger.debug("Built optimized TOER lookup tables")
        return tables
    
    @staticmethod
    def _parse_condition_to_range(condition: str, score: int) -> Optional[Tuple[float, float, int, str]]:
        """Parse a condition string into a numeric range (min, max, score, condition)."""
        try:
            # Handle >= conditions
            if '>=' in condition and '<=' not in condition:
                parts = condition.split('>=')
                if len(parts) == 2:
                    threshold = float(parts[1].strip())
                    return (threshold, float('inf'), score, condition)
            
            # Handle > conditions  
            elif '>' in condition and '>=' not in condition:
                parts = condition.split('>')
                if len(parts) == 2:
                    threshold = float(parts[1].strip())
                    return (threshold + 1e-10, float('inf'), score, condition)
            
            # Handle == conditions
            elif '==' in condition:
                parts = condition.split('==')
                if len(parts) == 2:
                    value = float(parts[1].strip())
                    return (value - 1e-10, value + 1e-10, score, condition)
            
            # Handle range conditions (min <= value <= max)
            elif condition.count('<=') == 2:
                parts = condition.split('<=')
                if len(parts) == 3:
                    min_val = float(parts[0].strip())
                    max_val = float(parts[2].strip())
                    return (min_val, max_val, score, condition)
        
        except (ValueError, IndexError):
            pass
        
        return None
    
    @staticmethod
    def _evaluate_condition(condition: str, value: float) -> bool:
        """Efficiently evaluate threshold conditions without eval()."""
        # Handle common patterns without eval for performance
        if condition == 'default':
            return True
        
        # Cache parsed conditions for performance
        if not hasattr(TOERCalculator, '_parsed_conditions'):
            TOERCalculator._parsed_conditions = {}
        
        if condition in TOERCalculator._parsed_conditions:
            parsed = TOERCalculator._parsed_conditions[condition]
            return parsed(value)
        
        val_str = str(value)
        
        # Handle equality
        if '==' in condition:
            parts = condition.split('==')
            if len(parts) == 2:
                try:
                    threshold_val = float(parts[1].strip())
                    return abs(value - threshold_val) < 1e-10  # Handle floating point precision
                except:
                    return False
        
        # Handle single comparisons (>, >=, <, <=)
        if condition.count('<=') == 1 and condition.count('>=') == 0:
            if '<=' in condition:
                parts = condition.split('<=')
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip()
                    try:
                        if left.replace('.', '').replace('-', '').isdigit():
                            return float(left) <= value
                        else:
                            return value <= float(right)
                    except:
                        return False
        
        if condition.count('>=') == 1 and condition.count('<=') == 0:
            parts = condition.split('>=')
            if len(parts) == 2:
                left = parts[0].strip()
                right = parts[1].strip()
                try:
                    if left.replace('.', '').replace('-', '').isdigit():
                        return float(left) >= value
                    else:
                        return value >= float(right)
                except:
                    return False
        
        if '>' in condition and '>=' not in condition:
            parts = condition.split('>')
            if len(parts) == 2:
                try:
                    threshold_val = float(parts[1].strip())
                    return value > threshold_val
                except:
                    return False
        
        # Handle range conditions (min <= value <= max)
        if condition.count('<=') == 2:
            parts = condition.split('<=')
            if len(parts) == 3:
                try:
                    min_val = float(parts[0].strip())
                    max_val = float(parts[2].strip())
                    return min_val <= value <= max_val
                except:
                    return False
        
        # Fallback to eval only if necessary
        try:
            # Replace variable names
            condition_check = condition
            var_names = ['ypp', 'comp_pct', 'ypc', 'third_down_pct', 'success_rate', 
                        'first_downs', 'ppd', 'redzone_td_pct', 'penalty_yards']
            
            for var_name in var_names:
                if var_name in condition_check:
                    condition_check = condition_check.replace(var_name, val_str)
                    break
            
            return eval(condition_check)
        except:
            return False
    
    @staticmethod
    def _score_from_thresholds(value: float, thresholds: List[Dict[str, Union[str, int]]]) -> int:
        """Score a value based on condition expressions that mirror original if-else logic."""
        for threshold in thresholds:
            condition = threshold.get('condition')
            
            if condition == 'default':
                return threshold['score']
            
            if TOERCalculator._evaluate_condition(condition, value):
                return threshold['score']
        
        return 0  # Default fallback
    
    @classmethod
    def _fast_score_lookup(cls, metric_name: str, value: float) -> int:
        """Fast lookup using pre-built lookup tables."""
        tables = cls._build_lookup_tables()
        
        if metric_name not in tables:
            return 0
        
        table = tables[metric_name]
        
        if table['type'] == 'exact':
            # Exact value lookup
            exact_data = table['data']
            int_value = int(value) if isinstance(value, float) and value.is_integer() else value
            return exact_data.get(int_value, table['default'])
        
        elif table['type'] == 'ranges':
            # Range lookup - find BEST NON-DEFAULT matching range
            ranges = table['data']
            default_score = 0
            best_score = None
            
            for min_val, max_val, score, condition in ranges:
                if condition == 'default':
                    default_score = score
                    continue
                if min_val <= value <= max_val:
                    # For >= conditions, take the highest scoring match
                    # (ranges are sorted by min_val, so later matches are better for >=)
                    best_score = score
            
            return best_score if best_score is not None else default_score
        
        return 0
    
    @staticmethod
    def _score_from_exact_values(value: int, exact_values: List[Dict[str, int]], default_score: int) -> int:
        """Score a value based on exact value configuration."""
        for item in exact_values:
            if value == item['value']:
                return item['score']
        return default_score
    
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
        return cls._fast_score_lookup('yards_per_play', ypp)
    
    @classmethod
    def calculate_turnovers_score(cls, turnovers: int) -> int:
        """Calculate turnovers component score (-5 to 10 points)."""
        if turnovers < 0:
            raise TOERValidationError(f"turnovers cannot be negative: {turnovers}")
        if turnovers > 10:
            raise TOERValidationError(f"turnovers seems unrealistic: {turnovers} (max reasonable: 10)")
        return cls._fast_score_lookup('turnovers', turnovers)
    
    @classmethod
    def calculate_completion_pct_score(cls, comp_pct: float) -> int:
        """Calculate completion percentage component score (0-10 points)."""
        cls._validate_percentage(comp_pct, "completion_percentage")
        return cls._fast_score_lookup('completion_percentage', comp_pct)
    
    @classmethod
    def calculate_rush_ypc_score(cls, ypc: float) -> int:
        """Calculate rushing YPC component score (0-10 points)."""
        cls._validate_non_negative(ypc, "rush_yards_per_carry", 15.0)
        return cls._fast_score_lookup('rush_yards_per_carry', ypc)
    
    @classmethod
    def calculate_sacks_score(cls, sacks: int) -> int:
        """Calculate sacks allowed component score (-3 to 10 points)."""
        if sacks < 0:
            raise TOERValidationError(f"sacks cannot be negative: {sacks}")
        if sacks > 15:
            raise TOERValidationError(f"sacks seems unrealistic: {sacks} (max reasonable: 15)")
        return cls._fast_score_lookup('sacks', sacks)
    
    @classmethod
    def calculate_third_down_score(cls, third_down_pct: float) -> int:
        """Calculate third down conversion component score (0-10 points)."""
        cls._validate_percentage(third_down_pct, "third_down_percentage")
        return cls._fast_score_lookup('third_down_percentage', third_down_pct)
    
    @classmethod
    def calculate_success_rate_score(cls, success_rate: float) -> int:
        """Calculate play success rate component score (0-10 points)."""
        cls._validate_percentage(success_rate, "success_rate")
        return cls._fast_score_lookup('success_rate', success_rate)
    
    @classmethod
    def calculate_first_downs_score(cls, first_downs: float) -> int:
        """Calculate first downs component score (0-10 points)."""
        cls._validate_non_negative(first_downs, "first_downs", 50.0)
        return cls._fast_score_lookup('first_downs', first_downs)
    
    @classmethod
    def calculate_ppd_score(cls, ppd: float) -> int:
        """Calculate points per drive component score (0-10 points)."""
        cls._validate_non_negative(ppd, "points_per_drive", 8.0)
        return cls._fast_score_lookup('points_per_drive', ppd)
    
    @classmethod
    def calculate_redzone_score(cls, redzone_td_pct: float) -> int:
        """Calculate red zone TD percentage component score (0-10 points)."""
        cls._validate_percentage(redzone_td_pct, "redzone_td_percentage")
        return cls._fast_score_lookup('redzone_td_percentage', redzone_td_pct)
    
    @classmethod
    def calculate_penalty_yards_adjustment(cls, penalty_yards: int) -> int:
        """Calculate penalty yards adjustment (-10 to +5 points)."""
        if penalty_yards < 0:
            raise TOERValidationError(f"penalty_yards cannot be negative: {penalty_yards}")
        if penalty_yards > 300:
            raise TOERValidationError(f"penalty_yards seems unrealistic: {penalty_yards} (max reasonable: 300)")
        return cls._fast_score_lookup('penalty_yards', penalty_yards)
    
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