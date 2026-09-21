# src/config/nfl_constants.py - Centralized NFL constants and configuration

# NFL Teams
NFL_TEAMS = [
    'ARI', 'ATL', 'BAL', 'BUF', 'CAR', 'CHI', 'CIN', 'CLE', 'DAL', 'DEN', 
    'DET', 'GB', 'HOU', 'IND', 'JAX', 'KC', 'LA', 'LAC', 'LV', 'MIA', 
    'MIN', 'NE', 'NO', 'NYG', 'NYJ', 'PHI', 'PIT', 'SEA', 'SF', 'TB', 'TEN', 'WAS'
]

# Current team palettes from nflverse (2026-09-21); see team_colors.md.
# Presentation uses the primary for the banner and secondary for its trim.
TEAM_DATA = {
    'ARI': {'name': 'Arizona Cardinals', 'colors': ['#97233F', '#000000', '#FFB612', '#A5ACAF'], 'logo': '🦅'},
    'ATL': {'name': 'Atlanta Falcons', 'colors': ['#A71930', '#000000', '#A5ACAF', '#A30D2D'], 'logo': '🦅'},
    'BAL': {'name': 'Baltimore Ravens', 'colors': ['#241773', '#9E7C0C', '#C60C30'], 'logo': '🐦‍⬛'},
    'BUF': {'name': 'Buffalo Bills', 'colors': ['#00338D', '#C60C30', '#0C2E82', '#D50A0A'], 'logo': '🦬'},
    'CAR': {'name': 'Carolina Panthers', 'colors': ['#0085CA', '#000000', '#BFC0BF'], 'logo': '🐾'},
    'CHI': {'name': 'Chicago Bears', 'colors': ['#0B162A', '#E64100'], 'logo': '🐻'},
    'CIN': {'name': 'Cincinnati Bengals', 'colors': ['#FB4F14', '#000000', '#D32F1E'], 'logo': '🐅'},
    'CLE': {'name': 'Cleveland Browns', 'colors': ['#FF3C00', '#311D00', '#A5ACAF', '#D32F1E'], 'logo': '🟤'},
    'DAL': {'name': 'Dallas Cowboys', 'colors': ['#002244', '#B0B7BC', '#ACC0C6', '#A5ACAF'], 'logo': '⭐'},
    'DEN': {'name': 'Denver Broncos', 'colors': ['#002244', '#FB4F14', '#00234C', '#FF5200'], 'logo': '🐴'},
    'DET': {'name': 'Detroit Lions', 'colors': ['#0076B6', '#B0B7BC', '#000000', '#004E89'], 'logo': '🦁'},
    'GB': {'name': 'Green Bay Packers', 'colors': ['#203731', '#FFB612', '#1C2D25', '#EEAD1E'], 'logo': '🧀'},
    'HOU': {'name': 'Houston Texans', 'colors': ['#03202F', '#A71930', '#00071C', '#A30D2D'], 'logo': '🤠'},
    'IND': {'name': 'Indianapolis Colts', 'colors': ['#002C5F', '#A5ACAF', '#013369', '#9BA1A2'], 'logo': '🐎'},
    'JAX': {'name': 'Jacksonville Jaguars', 'colors': ['#006778', '#000000', '#9F792C', '#D7A22A'], 'logo': '🐆'},
    'KC': {'name': 'Kansas City Chiefs', 'colors': ['#E31837', '#FFB612', '#000000'], 'logo': '🏹'},
    'LA': {'name': 'Los Angeles Rams', 'colors': ['#003594', '#FFD100', '#001532', '#AF925D'], 'logo': '🐏'},
    'LAC': {'name': 'Los Angeles Chargers', 'colors': ['#007BC7', '#FFC20E', '#FFB612', '#001532'], 'logo': '⚡'},
    'LV': {'name': 'Las Vegas Raiders', 'colors': ['#000000', '#A5ACAF', '#A6AEB0'], 'logo': '🏴‍☠️'},
    'MIA': {'name': 'Miami Dolphins', 'colors': ['#008E97', '#F58220', '#005778'], 'logo': '🐬'},
    'MIN': {'name': 'Minnesota Vikings', 'colors': ['#4F2683', '#FFC62F', '#E9BF9B', '#000000'], 'logo': '⚔️'},
    'NE': {'name': 'New England Patriots', 'colors': ['#002244', '#C60C30', '#B0B7BC', '#001532'], 'logo': '🦅'},
    'NO': {'name': 'New Orleans Saints', 'colors': ['#D3BC8D', '#000000', '#9F8958'], 'logo': '⚜️'},
    'NYG': {'name': 'New York Giants', 'colors': ['#0B2265', '#A71930', '#A5ACAF', '#012352'], 'logo': '🗽'},
    'NYJ': {'name': 'New York Jets', 'colors': ['#003F2D', '#000000'], 'logo': '✈️'},
    'PHI': {'name': 'Philadelphia Eagles', 'colors': ['#004C54', '#A5ACAF', '#ACC0C6', '#000000'], 'logo': '🦅'},
    'PIT': {'name': 'Pittsburgh Steelers', 'colors': ['#000000', '#FFB612', '#C60C30', '#00539B'], 'logo': '🔧'},
    'SEA': {'name': 'Seattle Seahawks', 'colors': ['#002244', '#69BE28', '#A5ACAF', '#001532'], 'logo': '🦅'},
    'SF': {'name': 'San Francisco 49ers', 'colors': ['#AA0000', '#B3995D', '#000000', '#A5ACAF'], 'logo': '🏔️'},
    'TB': {'name': 'Tampa Bay Buccaneers', 'colors': ['#A71930', '#322F2B', '#000000', '#FF7900'], 'logo': '🏴‍☠️'},
    'TEN': {'name': 'Tennessee Titans', 'colors': ['#4495D2', '#D50A0A'], 'logo': '⚔️'},
    'WAS': {'name': 'Washington Commanders', 'colors': ['#5A1414', '#FFB612', '#000000', '#5B2B2F'], 'logo': '🏛️'}
}

# NFL Configuration Constants
TOTAL_NFL_TEAMS = 32
NFL_SEASON_START_MONTH = 9
NFL_DATA_START_YEAR = 1999
INCOMPLETE_SEASON_WARNING_MONTH = 12

# Data freshness thresholds (in days)
FRESH_DATA_DAYS = 7
SLIGHTLY_OUTDATED_DATA_DAYS = 14

# Scoring values
TOUCHDOWN_POINTS = 6
EXTRA_POINT_POINTS = 1
TWO_POINT_CONVERSION_POINTS = 2
FIELD_GOAL_POINTS = 3
SAFETY_POINTS = 2

# Field positions
RED_ZONE_YARDLINE = 20

# Season types
SEASON_TYPES = {
    'ALL': 'All Games',
    'REG': 'Regular Season',
    'POST': 'Playoffs'
}

# Success rate calculation thresholds
FIRST_DOWN_SUCCESS_THRESHOLD = 0.4
SECOND_DOWN_SUCCESS_THRESHOLD = 0.6
CONVERSION_SUCCESS_THRESHOLD = 1.0

# Valid team abbreviation set (for fast lookup)
VALID_TEAMS = set(NFL_TEAMS)

# Game count constants
NFL_REGULAR_SEASON_GAMES = 17  # Since 2021 season
NFL_REGULAR_SEASON_GAMES_PRE_2021 = 16  # 1978-2020 seasons

# Cache TTL constants (in hours)
CACHE_TTL_CURRENT_SEASON_HOURS = 24  # 24 hour cache for current season
CACHE_TTL_HISTORICAL_SEASON_HOURS = 24 * 365  # Essentially permanent for historical data

# Progress tracking milestones
PROGRESS_MILESTONES = {
    'validation_start': 0.1,
    'orchestration_start': 0.3,
    'data_fetch_start': 0.4,
    'filter_application': 0.7,
    'rankings_calculation': 0.7,
    'statistics_processing': 0.8,
    'finalization': 0.9,
    'league_averages': 0.95,
}

# UI Display constants
CHART_OPACITY = 0.7  # Opacity for bar charts
METRIC_FONT_SIZES = {
    'label': '0.8em',
    'value': '1.5em', 
    'rank': '0.75em'
}