# tests/domain/test_toer_calculator.py

"""
Comprehensive unit tests for TOERCalculator.
Tests all scoring methods, edge cases, validation, and the main calculate_toer method.
"""

import pytest
from src.domain.toer_calculator import TOERCalculator, TOERValidationError


class TestTOERCalculatorValidation:
    """Test input validation for all TOER calculator methods."""
    
    def test_validate_negative_yards_per_play(self):
        with pytest.raises(TOERValidationError, match="yards_per_play cannot be negative"):
            TOERCalculator.calculate_yards_per_play_score(-1.0)
    
    def test_validate_unrealistic_yards_per_play(self):
        with pytest.raises(TOERValidationError, match="yards_per_play seems unrealistic"):
            TOERCalculator.calculate_yards_per_play_score(25.0)
    
    def test_validate_negative_turnovers(self):
        with pytest.raises(TOERValidationError, match="turnovers cannot be negative"):
            TOERCalculator.calculate_turnovers_score(-1)
    
    def test_validate_unrealistic_turnovers(self):
        with pytest.raises(TOERValidationError, match="turnovers seems unrealistic"):
            TOERCalculator.calculate_turnovers_score(15)
    
    def test_validate_completion_percentage_negative(self):
        with pytest.raises(TOERValidationError, match="completion_percentage must be between 0 and 100"):
            TOERCalculator.calculate_completion_pct_score(-5.0)
    
    def test_validate_completion_percentage_over_100(self):
        with pytest.raises(TOERValidationError, match="completion_percentage must be between 0 and 100"):
            TOERCalculator.calculate_completion_pct_score(105.0)
    
    def test_validate_negative_rush_ypc(self):
        with pytest.raises(TOERValidationError, match="rush_yards_per_carry cannot be negative"):
            TOERCalculator.calculate_rush_ypc_score(-2.0)
    
    def test_validate_unrealistic_rush_ypc(self):
        with pytest.raises(TOERValidationError, match="rush_yards_per_carry seems unrealistic"):
            TOERCalculator.calculate_rush_ypc_score(20.0)
    
    def test_validate_negative_sacks(self):
        with pytest.raises(TOERValidationError, match="sacks cannot be negative"):
            TOERCalculator.calculate_sacks_score(-1)
    
    def test_validate_unrealistic_sacks(self):
        with pytest.raises(TOERValidationError, match="sacks seems unrealistic"):
            TOERCalculator.calculate_sacks_score(20)
    
    def test_validate_third_down_percentage_bounds(self):
        with pytest.raises(TOERValidationError, match="third_down_percentage must be between 0 and 100"):
            TOERCalculator.calculate_third_down_score(-10.0)
        
        with pytest.raises(TOERValidationError, match="third_down_percentage must be between 0 and 100"):
            TOERCalculator.calculate_third_down_score(150.0)
    
    def test_validate_success_rate_bounds(self):
        with pytest.raises(TOERValidationError, match="success_rate must be between 0 and 100"):
            TOERCalculator.calculate_success_rate_score(-5.0)
        
        with pytest.raises(TOERValidationError, match="success_rate must be between 0 and 100"):
            TOERCalculator.calculate_success_rate_score(110.0)
    
    def test_validate_negative_first_downs(self):
        with pytest.raises(TOERValidationError, match="first_downs cannot be negative"):
            TOERCalculator.calculate_first_downs_score(-3.0)
    
    def test_validate_unrealistic_first_downs(self):
        with pytest.raises(TOERValidationError, match="first_downs seems unrealistic"):
            TOERCalculator.calculate_first_downs_score(60.0)
    
    def test_validate_negative_points_per_drive(self):
        with pytest.raises(TOERValidationError, match="points_per_drive cannot be negative"):
            TOERCalculator.calculate_ppd_score(-1.0)
    
    def test_validate_unrealistic_points_per_drive(self):
        with pytest.raises(TOERValidationError, match="points_per_drive seems unrealistic"):
            TOERCalculator.calculate_ppd_score(10.0)
    
    def test_validate_redzone_percentage_bounds(self):
        with pytest.raises(TOERValidationError, match="redzone_td_percentage must be between 0 and 100"):
            TOERCalculator.calculate_redzone_score(-10.0)
        
        with pytest.raises(TOERValidationError, match="redzone_td_percentage must be between 0 and 100"):
            TOERCalculator.calculate_redzone_score(120.0)
    
    def test_validate_negative_penalty_yards(self):
        with pytest.raises(TOERValidationError, match="penalty_yards cannot be negative"):
            TOERCalculator.calculate_penalty_yards_adjustment(-5)
    
    def test_validate_unrealistic_penalty_yards(self):
        with pytest.raises(TOERValidationError, match="penalty_yards seems unrealistic"):
            TOERCalculator.calculate_penalty_yards_adjustment(350)


class TestYardsPerPlayScoring:
    """Test yards per play scoring logic."""
    
    def test_excellent_ypp(self):
        assert TOERCalculator.calculate_yards_per_play_score(6.0) == 10
        assert TOERCalculator.calculate_yards_per_play_score(5.51) == 10
    
    def test_perfect_ypp_boundary(self):
        assert TOERCalculator.calculate_yards_per_play_score(5.5) == 9
    
    def test_ypp_scoring_ranges(self):
        assert TOERCalculator.calculate_yards_per_play_score(5.47) == 8
        assert TOERCalculator.calculate_yards_per_play_score(5.42) == 7
        assert TOERCalculator.calculate_yards_per_play_score(5.37) == 6
        assert TOERCalculator.calculate_yards_per_play_score(5.32) == 5
        assert TOERCalculator.calculate_yards_per_play_score(5.27) == 4
        assert TOERCalculator.calculate_yards_per_play_score(5.22) == 3
        assert TOERCalculator.calculate_yards_per_play_score(5.17) == 2
        assert TOERCalculator.calculate_yards_per_play_score(5.12) == 1
    
    def test_poor_ypp(self):
        assert TOERCalculator.calculate_yards_per_play_score(5.05) == 0
        assert TOERCalculator.calculate_yards_per_play_score(4.0) == 0
        assert TOERCalculator.calculate_yards_per_play_score(0.0) == 0
    
    def test_critical_boundary_precision_issues(self):
        """Test the exact boundary precision issue that was discovered with Arizona Cardinals."""
        # This is the EXACT value that failed - 5.509090909090909
        # After rounding fix: rounds to 5.51 and should score 10 points
        assert TOERCalculator.calculate_yards_per_play_score(5.509090909090909) == 10
        
        # Test display consistency - values that display the same should score the same
        # All these round to 5.50 when displayed, so should have same score
        assert TOERCalculator.calculate_yards_per_play_score(5.504) == 9   # rounds to 5.50
        assert TOERCalculator.calculate_yards_per_play_score(5.500) == 9   # exactly 5.50
        assert TOERCalculator.calculate_yards_per_play_score(5.496) == 9   # rounds to 5.50
        
        # Values that round to different displays should potentially score differently
        assert TOERCalculator.calculate_yards_per_play_score(5.51) == 10   # displays as 5.51
        assert TOERCalculator.calculate_yards_per_play_score(5.49) == 8    # displays as 5.49
        
        # Test all critical boundaries with floating point precision
        boundaries = [
            (5.51, 10),  # > 5.5
            (5.50, 9),   # 5.5
            (5.49, 8),   # 5.45-5.49
            (5.45, 8),
            (5.44, 7),   # 5.40-5.44
            (5.40, 7),
            (5.39, 6),   # 5.35-5.39
            (5.35, 6),
            (5.34, 5),   # 5.30-5.34
            (5.30, 5),
            (5.29, 4),   # 5.25-5.29
            (5.25, 4),
            (5.24, 3),   # 5.20-5.24
            (5.20, 3),
            (5.19, 2),   # 5.15-5.19
            (5.15, 2),
            (5.14, 1),   # 5.10-5.14
            (5.10, 1),
            (5.09, 0),   # < 5.10
        ]
        
        for value, expected_score in boundaries:
            assert TOERCalculator.calculate_yards_per_play_score(value) == expected_score, \
                f"YPP {value} should score {expected_score}"
    
    def test_real_world_ypp_values(self):
        """Test with actual YPP values that could occur in real games."""
        # These are realistic YPP values from actual games
        real_values = [
            (121 / 22, 9),    # 5.5 exactly (121 yards on 22 plays) - scores 9
            (385 / 70, 9),    # 5.5 exactly (385 yards on 70 plays) - scores 9
            (484 / 88, 9),    # 5.5 exactly (484 yards on 88 plays) - scores 9
            (606 / 110, 10),  # 5.509090909090909 - The Arizona Cardinals case! - scores 10
            (371 / 68, 8),    # 5.455882352941177
            (299 / 55, 7),    # 5.436363636363636
            (412 / 76, 7),    # 5.421052631578947
            (287 / 53, 7),    # 5.415094339622641
            (325 / 61, 5),    # 5.327868852459016
            (380 / 72, 4),    # 5.277777777777778
            (295 / 57, 2),    # 5.175438596491228
            (301 / 59, 1),    # 5.101694915254237
        ]
        
        for yards_plays_tuple, expected_score in real_values:
            ypp = yards_plays_tuple
            actual_score = TOERCalculator.calculate_yards_per_play_score(ypp)
            assert actual_score == expected_score, \
                f"YPP {ypp:.15f} should score {expected_score}, got {actual_score}"


class TestTurnoverScoring:
    """Test turnover scoring logic."""
    
    def test_no_turnovers(self):
        assert TOERCalculator.calculate_turnovers_score(0) == 10
    
    def test_turnover_scoring_progression(self):
        assert TOERCalculator.calculate_turnovers_score(1) == 5
        assert TOERCalculator.calculate_turnovers_score(2) == 0
        assert TOERCalculator.calculate_turnovers_score(3) == -3
        assert TOERCalculator.calculate_turnovers_score(4) == -4
    
    def test_many_turnovers(self):
        assert TOERCalculator.calculate_turnovers_score(5) == -5
        assert TOERCalculator.calculate_turnovers_score(10) == -5


class TestCompletionPercentageScoring:
    """Test completion percentage scoring logic."""
    
    def test_excellent_completion_rate(self):
        assert TOERCalculator.calculate_completion_pct_score(70.0) == 10
        assert TOERCalculator.calculate_completion_pct_score(67.5) == 10
    
    def test_completion_percentage_ranges(self):
        assert TOERCalculator.calculate_completion_pct_score(67.25) == 9
        assert TOERCalculator.calculate_completion_pct_score(66.75) == 8
        assert TOERCalculator.calculate_completion_pct_score(66.25) == 7
        assert TOERCalculator.calculate_completion_pct_score(65.75) == 6
        assert TOERCalculator.calculate_completion_pct_score(65.25) == 5
        assert TOERCalculator.calculate_completion_pct_score(64.75) == 4
        assert TOERCalculator.calculate_completion_pct_score(64.25) == 3
        assert TOERCalculator.calculate_completion_pct_score(63.75) == 2
        assert TOERCalculator.calculate_completion_pct_score(63.25) == 1
    
    def test_poor_completion_rate(self):
        assert TOERCalculator.calculate_completion_pct_score(62.0) == 0
        assert TOERCalculator.calculate_completion_pct_score(50.0) == 0


class TestRushYPCScoring:
    """Test rushing yards per carry scoring logic."""
    
    def test_excellent_rush_ypc(self):
        assert TOERCalculator.calculate_rush_ypc_score(5.0) == 10
        assert TOERCalculator.calculate_rush_ypc_score(4.7) == 10
    
    def test_rush_ypc_ranges(self):
        assert TOERCalculator.calculate_rush_ypc_score(4.67) == 9
        assert TOERCalculator.calculate_rush_ypc_score(4.62) == 8
        assert TOERCalculator.calculate_rush_ypc_score(4.57) == 7
        assert TOERCalculator.calculate_rush_ypc_score(4.52) == 6
        assert TOERCalculator.calculate_rush_ypc_score(4.47) == 5
        assert TOERCalculator.calculate_rush_ypc_score(4.42) == 4
        assert TOERCalculator.calculate_rush_ypc_score(4.37) == 3
        assert TOERCalculator.calculate_rush_ypc_score(4.32) == 2  # Fixed range
        assert TOERCalculator.calculate_rush_ypc_score(4.25) == 1
    
    def test_poor_rush_ypc(self):
        assert TOERCalculator.calculate_rush_ypc_score(4.15) == 0
        assert TOERCalculator.calculate_rush_ypc_score(3.0) == 0
        assert TOERCalculator.calculate_rush_ypc_score(0.0) == 0


class TestSacksScoring:
    """Test sacks allowed scoring logic."""
    
    def test_no_sacks(self):
        assert TOERCalculator.calculate_sacks_score(0) == 10
    
    def test_sacks_scoring_progression(self):
        assert TOERCalculator.calculate_sacks_score(1) == 8
        assert TOERCalculator.calculate_sacks_score(2) == 5
        assert TOERCalculator.calculate_sacks_score(3) == 0
        assert TOERCalculator.calculate_sacks_score(4) == -1
    
    def test_many_sacks(self):
        assert TOERCalculator.calculate_sacks_score(5) == -3
        assert TOERCalculator.calculate_sacks_score(10) == -3


class TestThirdDownScoring:
    """Test third down conversion scoring logic."""
    
    def test_excellent_third_down_rate(self):
        assert TOERCalculator.calculate_third_down_score(45.0) == 10
        assert TOERCalculator.calculate_third_down_score(43.0) == 10
    
    def test_third_down_ranges(self):
        assert TOERCalculator.calculate_third_down_score(42.5) == 9
        assert TOERCalculator.calculate_third_down_score(41.5) == 8
        assert TOERCalculator.calculate_third_down_score(40.5) == 7
        assert TOERCalculator.calculate_third_down_score(39.5) == 6
        assert TOERCalculator.calculate_third_down_score(38.5) == 5
        assert TOERCalculator.calculate_third_down_score(37.5) == 4
        assert TOERCalculator.calculate_third_down_score(36.5) == 3
        assert TOERCalculator.calculate_third_down_score(35.5) == 2
        assert TOERCalculator.calculate_third_down_score(34.0) == 1
        assert TOERCalculator.calculate_third_down_score(33.5) == 1  # Test middle of 33.0-34.99 range
        assert TOERCalculator.calculate_third_down_score(33.0) == 1  # Test boundary
    
    def test_poor_third_down_rate(self):
        assert TOERCalculator.calculate_third_down_score(32.99) == 0  # Test just below 33.0
        assert TOERCalculator.calculate_third_down_score(32.0) == 0
        assert TOERCalculator.calculate_third_down_score(25.0) == 0
        assert TOERCalculator.calculate_third_down_score(10.0) == 0


class TestSuccessRateScoring:
    """Test success rate scoring logic."""
    
    def test_excellent_success_rate(self):
        assert TOERCalculator.calculate_success_rate_score(50.0) == 10
        assert TOERCalculator.calculate_success_rate_score(47.0) == 10
    
    def test_success_rate_ranges(self):
        assert TOERCalculator.calculate_success_rate_score(46.5) == 9
        assert TOERCalculator.calculate_success_rate_score(45.5) == 8
        assert TOERCalculator.calculate_success_rate_score(44.5) == 7
        assert TOERCalculator.calculate_success_rate_score(43.5) == 6
        assert TOERCalculator.calculate_success_rate_score(42.5) == 5
        assert TOERCalculator.calculate_success_rate_score(41.5) == 4
        assert TOERCalculator.calculate_success_rate_score(40.5) == 3
    
    def test_poor_success_rate(self):
        assert TOERCalculator.calculate_success_rate_score(39.99) == 0  # Test just below 40.0
        assert TOERCalculator.calculate_success_rate_score(39.0) == 0
        assert TOERCalculator.calculate_success_rate_score(35.0) == 0
        assert TOERCalculator.calculate_success_rate_score(30.0) == 0
        assert TOERCalculator.calculate_success_rate_score(20.0) == 0
        assert TOERCalculator.calculate_success_rate_score(10.0) == 0


class TestFirstDownsScoring:
    """Test first downs scoring logic."""
    
    def test_first_downs_ranges(self):
        assert TOERCalculator.calculate_first_downs_score(25.0) == 10
        assert TOERCalculator.calculate_first_downs_score(22.0) == 10
        assert TOERCalculator.calculate_first_downs_score(21.5) == 9
        assert TOERCalculator.calculate_first_downs_score(20.5) == 8
        assert TOERCalculator.calculate_first_downs_score(19.5) == 7
        assert TOERCalculator.calculate_first_downs_score(18.5) == 6
        assert TOERCalculator.calculate_first_downs_score(17.5) == 5
        assert TOERCalculator.calculate_first_downs_score(17.0) == 5  # Test exact boundary
    
    def test_poor_first_downs(self):
        assert TOERCalculator.calculate_first_downs_score(16.99) == 0  # Test just below 17.0
        assert TOERCalculator.calculate_first_downs_score(16.0) == 0
        assert TOERCalculator.calculate_first_downs_score(12.0) == 0
        assert TOERCalculator.calculate_first_downs_score(10.0) == 0
        assert TOERCalculator.calculate_first_downs_score(5.0) == 0


class TestPointsPerDriveScoring:
    """Test points per drive scoring logic."""
    
    def test_excellent_ppd(self):
        assert TOERCalculator.calculate_ppd_score(3.0) == 10
        assert TOERCalculator.calculate_ppd_score(2.4) == 10
    
    def test_ppd_ranges(self):
        assert TOERCalculator.calculate_ppd_score(2.37) == 9
        assert TOERCalculator.calculate_ppd_score(2.32) == 8
        assert TOERCalculator.calculate_ppd_score(2.27) == 7
        assert TOERCalculator.calculate_ppd_score(2.22) == 6
        assert TOERCalculator.calculate_ppd_score(2.15) == 5
        assert TOERCalculator.calculate_ppd_score(2.05) == 4
        assert TOERCalculator.calculate_ppd_score(1.95) == 3
        assert TOERCalculator.calculate_ppd_score(1.87) == 2
        assert TOERCalculator.calculate_ppd_score(1.82) == 1
    
    def test_poor_ppd(self):
        assert TOERCalculator.calculate_ppd_score(1.75) == 0
        assert TOERCalculator.calculate_ppd_score(1.0) == 0


class TestRedZoneScoring:
    """Test red zone touchdown percentage scoring logic."""
    
    def test_excellent_redzone_rate(self):
        assert TOERCalculator.calculate_redzone_score(70.0) == 10
        assert TOERCalculator.calculate_redzone_score(63.0) == 10
    
    def test_redzone_ranges(self):
        assert TOERCalculator.calculate_redzone_score(62.0) == 9
        assert TOERCalculator.calculate_redzone_score(60.5) == 8
        assert TOERCalculator.calculate_redzone_score(59.5) == 7
        assert TOERCalculator.calculate_redzone_score(58.5) == 6
        assert TOERCalculator.calculate_redzone_score(57.5) == 5
        assert TOERCalculator.calculate_redzone_score(57.0) == 5  # Test exact boundary
    
    def test_poor_redzone_rate(self):
        assert TOERCalculator.calculate_redzone_score(56.99) == 0  # Test just below 57.0
        assert TOERCalculator.calculate_redzone_score(56.0) == 0
        assert TOERCalculator.calculate_redzone_score(50.0) == 0
        assert TOERCalculator.calculate_redzone_score(40.0) == 0
        assert TOERCalculator.calculate_redzone_score(30.0) == 0
        assert TOERCalculator.calculate_redzone_score(20.0) == 0


class TestPenaltyYardsAdjustment:
    """Test penalty yards adjustment scoring logic."""
    
    def test_no_penalties(self):
        assert TOERCalculator.calculate_penalty_yards_adjustment(0) == 5
    
    def test_penalty_ranges(self):
        assert TOERCalculator.calculate_penalty_yards_adjustment(5) == 3
        assert TOERCalculator.calculate_penalty_yards_adjustment(15) == 1
        assert TOERCalculator.calculate_penalty_yards_adjustment(25) == 0
        assert TOERCalculator.calculate_penalty_yards_adjustment(35) == -2
        assert TOERCalculator.calculate_penalty_yards_adjustment(45) == -4
        assert TOERCalculator.calculate_penalty_yards_adjustment(55) == -5
        assert TOERCalculator.calculate_penalty_yards_adjustment(65) == -6
        assert TOERCalculator.calculate_penalty_yards_adjustment(75) == -8
        assert TOERCalculator.calculate_penalty_yards_adjustment(85) == -9
    
    def test_many_penalty_yards(self):
        assert TOERCalculator.calculate_penalty_yards_adjustment(95) == -10
        assert TOERCalculator.calculate_penalty_yards_adjustment(150) == -10


class TestTOERCalculation:
    """Test the main TOER calculation method."""
    
    def test_perfect_game_toer(self):
        """Test TOER calculation for a perfect offensive game."""
        toer = TOERCalculator.calculate_toer(
            avg_yards_per_play=6.0,      # 10 points
            turnovers=0,                 # 10 points
            completion_pct=70.0,         # 10 points
            rush_ypc=5.0,               # 10 points
            sacks=0,                    # 10 points
            third_down_pct=50.0,        # 10 points
            success_rate=50.0,          # 10 points
            first_downs=25.0,           # 10 points
            points_per_drive=3.0,       # 10 points
            redzone_td_pct=70.0,        # 10 points
            penalty_yards=0             # +5 points
        )
        # Base: 100, Penalty: +5, Capped at 100
        assert toer == 100.0
    
    def test_average_game_toer(self):
        """Test TOER calculation for an average offensive game."""
        toer = TOERCalculator.calculate_toer(
            avg_yards_per_play=5.3,      # 5 points
            turnovers=2,                 # 0 points
            completion_pct=65.0,         # 5 points
            rush_ypc=4.4,               # 4 points
            sacks=3,                    # 0 points
            third_down_pct=38.0,        # 5 points
            success_rate=42.0,          # 5 points
            first_downs=18.0,           # 6 points
            points_per_drive=2.1,       # 5 points
            redzone_td_pct=58.0,        # 6 points
            penalty_yards=50            # -4 points
        )
        # Base: 41, Penalty: -4, Total: 37
        assert toer == 37.0
    
    def test_terrible_game_toer(self):
        """Test TOER calculation for a terrible offensive game."""
        toer = TOERCalculator.calculate_toer(
            avg_yards_per_play=4.0,      # 0 points
            turnovers=5,                 # -5 points
            completion_pct=50.0,         # 0 points
            rush_ypc=3.0,               # 0 points
            sacks=6,                    # -3 points
            third_down_pct=25.0,        # 0 points
            success_rate=30.0,          # 0 points
            first_downs=12.0,           # 0 points
            points_per_drive=1.0,       # 0 points
            redzone_td_pct=40.0,        # 0 points
            penalty_yards=100          # -10 points
        )
        # Base: -8, Penalty: -10, Total: -18, Capped at 0
        assert toer == 0.0
    
    def test_toer_boundary_values(self):
        """Test TOER calculation at various boundary values."""
        # Test exact boundary values for different components
        toer = TOERCalculator.calculate_toer(
            avg_yards_per_play=5.5,      # 9 points (exact boundary)
            turnovers=1,                 # 5 points
            completion_pct=67.5,         # 10 points (exact boundary)
            rush_ypc=4.7,               # 10 points (exact boundary)
            sacks=1,                    # 8 points
            third_down_pct=43.0,        # 10 points (exact boundary)
            success_rate=47.0,          # 10 points (exact boundary)
            first_downs=22.0,           # 10 points (exact boundary)
            points_per_drive=2.4,       # 10 points (exact boundary)
            redzone_td_pct=63.0,        # 10 points (exact boundary)
            penalty_yards=0             # +5 points
        )
        # Base: 92, Penalty: +5, Total: 97
        assert toer == 97.0
    
    def test_toer_with_invalid_inputs_during_calculation(self):
        """Test that TOER calculation handles validation errors by returning 0."""
        # The calculate_toer method catches all exceptions and returns 0.0
        toer = TOERCalculator.calculate_toer(
            avg_yards_per_play=-1.0,  # Invalid negative value
            turnovers=0,
            completion_pct=65.0,
            rush_ypc=4.5,
            sacks=2,
            third_down_pct=40.0,
            success_rate=45.0,
            first_downs=20.0,
            points_per_drive=2.2,
            redzone_td_pct=60.0,
            penalty_yards=30
        )
        assert toer == 0.0
    
    def test_individual_methods_raise_validation_errors(self):
        """Test that individual scoring methods raise validation errors properly."""
        with pytest.raises(TOERValidationError):
            TOERCalculator.calculate_yards_per_play_score(-1.0)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_zero_values(self):
        """Test all zero values (where valid)."""
        toer = TOERCalculator.calculate_toer(
            avg_yards_per_play=0.0,      # 0 points
            turnovers=0,                 # 10 points
            completion_pct=0.0,          # 0 points
            rush_ypc=0.0,               # 0 points
            sacks=0,                    # 10 points
            third_down_pct=0.0,         # 0 points
            success_rate=0.0,           # 0 points
            first_downs=0.0,            # 0 points
            points_per_drive=0.0,       # 0 points
            redzone_td_pct=0.0,         # 0 points
            penalty_yards=0             # +5 points
        )
        # Base: 20, Penalty: +5, Total: 25
        assert toer == 25.0
    
    def test_maximum_valid_values(self):
        """Test with maximum reasonable values."""
        toer = TOERCalculator.calculate_toer(
            avg_yards_per_play=15.0,     # 10 points
            turnovers=0,                 # 10 points
            completion_pct=100.0,        # 10 points
            rush_ypc=10.0,              # 10 points
            sacks=0,                    # 10 points
            third_down_pct=100.0,       # 10 points
            success_rate=100.0,         # 10 points
            first_downs=40.0,           # 10 points
            points_per_drive=7.0,       # 10 points
            redzone_td_pct=100.0,       # 10 points
            penalty_yards=0             # +5 points
        )
        # Base: 100, Penalty: +5, Total: 105, Capped at 100
        assert toer == 100.0


if __name__ == "__main__":
    pytest.main([__file__])