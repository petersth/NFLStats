"""Read-only card details from the selected analysis and the actual TOER rules."""

import html
import re
from math import isfinite

from ....domain.toer_calculator import TOERCalculator, TOERValidationError
from ....utils.season_utils import get_regular_season_weeks


# Season aggregate -> per-game field, configuration key, public domain scorer.
_FIELDS = {
    'avg_yards_per_play': ('yards_per_play', 'yards_per_play', 'calculate_yards_per_play_score'),
    'points_per_drive': ('points_per_drive', 'points_per_drive', 'calculate_ppd_score'),
    'success_rate': ('success_rate', 'success_rate', 'calculate_success_rate_score'),
    'completion_pct': ('completion_pct', 'completion_percentage', 'calculate_completion_pct_score'),
    'rush_ypc': ('rush_ypc', 'rush_yards_per_carry', 'calculate_rush_ypc_score'),
    'third_down_pct': ('third_down_pct', 'third_down_percentage', 'calculate_third_down_score'),
    'redzone_td_pct': ('redzone_td_pct', 'redzone_td_percentage', 'calculate_redzone_score'),
    'first_downs_per_game': ('first_downs', 'first_downs', 'calculate_first_downs_score'),
    'turnovers_per_game': ('turnovers', 'turnovers', 'calculate_turnovers_score'),
    'sacks_per_game': ('sacks', 'sacks', 'calculate_sacks_score'),
    'penalty_yards_per_game': ('penalty_yards', 'penalty_yards', 'calculate_penalty_yards_adjustment'),
}


def metric_details_html(metric, response):
    """Use native disclosures so opening a card needs no server rerun."""
    game_field, config_key, scorer_name = _FIELDS[metric.key]
    scorer = getattr(TOERCalculator, scorer_name)
    unit = '%' if metric.unit == '%' else ''
    games = response.game_stats or []
    # Preserve source order and use game numbers if any week metadata is missing.
    has_weeks = bool(games) and all(item.game is not None for item in games)
    if has_weeks:
        games = sorted(games, key=lambda item: item.game.week)
    rows, values, scores = [], [], []
    for index, game in enumerate(games, 1):
        value = getattr(game.offensive_stats, game_field)
        try:
            score = scorer(value)
        except TOERValidationError:
            score = None
        if score is not None:
            scores.append(score)
            values.append(value)
        label = f'G{index}'
        if has_weeks:
            week = game.game.week
            regular_weeks = get_regular_season_weeks(game.game.season.year)
            label = f'W{week}' if week <= regular_weeks else f'P{week - regular_weeks}'
        opponent = html.escape(game.opponent.abbreviation)
        value_display = f'{value:.2f}{unit}' if isinstance(value, (int, float)) and isfinite(value) else '—'
        score_display = f'{score:+d}' if score is not None else '—'
        rows.append(
            f'<tr><td>{label}</td><td>{opponent}</td><td>{value_display}</td>'
            f'<td class="metric-game-points">{score_display}</td></tr>'
        )

    chart = ''
    if len(values) > 1 and len(values) == len(games):
        low, high = min(values), max(values)
        spread = high - low or 1
        points = ' '.join(f'{6 + i * 228 / (len(values) - 1):.1f},{54 - (v - low) * 44 / spread:.1f}' for i, v in enumerate(values))
        chart = (
            '<svg class="metric-history-chart" viewBox="0 0 240 64" role="img" '
            'aria-label="Game values in table order; exact values are in the table below">'
            '<path d="M6 58H234" class="metric-chart-baseline"/>'
            f'<polyline points="{points}"/></svg>'
        )
    history = (
        f'{chart}<div class="metric-history-scroll" tabindex="0" role="region" aria-label="Game history">'
        '<table><thead><tr><th scope="col">Game</th><th scope="col">Opp.</th>'
        '<th scope="col">Value</th><th scope="col">TOER pts</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
        if rows else '<p>No game history available.</p>'
    )

    config = TOERCalculator._load_config()[config_key]
    rules = []
    if 'thresholds' in config:
        for rule in config['thresholds']:
            condition = rule['condition']
            readable = 'Otherwise' if condition == 'default' else re.sub(r'\b[a-z_]+\b', 'Value', condition)
            rules.append((readable, rule['score']))
    else:
        rules = [(f'Value = {rule["value"]}', rule['score']) for rule in config['exact_values']]
        rules.append(('Otherwise', config['default_score']))
    rule_rows = ''.join(f'<tr><td>{html.escape(label)}</td><td>{score:+d}</td></tr>' for label, score in rules)
    minimum, maximum = min(score for _, score in rules), max(score for _, score in rules)
    average = f'{sum(scores) / len(scores):+.2f}' if scores and len(scores) == len(games) else '—'
    contribution = (
        '<div class="metric-contribution"><div><span>Average input points</span>'
        f'<strong>{average}<small> pts / game</small></strong></div>'
        f'<span class="metric-point-range">{minimum:+d} to {maximum:+d}<small>per-game range</small></span></div>'
    )
    contribution_note = (
        f'Points averaged across {len(games)} selected {"game" if len(games) == 1 else "games"}, '
        'before each game’s total is limited to 0–100.'
        if scores and len(scores) == len(games)
        else 'A complete set of valid game values is needed to show average input points.'
    )
    settings = response.configuration or {}
    setting_notes = []
    for key, subject in {
        'completion_pct': [('include_spikes_completion', 'QB spikes')],
        'rush_ypc': [('include_qb_kneels_rushing', 'QB kneels')],
        'success_rate': [('include_qb_kneels_success_rate', 'QB kneels'),
                         ('include_spikes_success_rate', 'QB spikes')],
    }.get(metric.key, []):
        setting_notes.append(f'{"Includes" if settings.get(key, True) else "Excludes"} {subject}.')
    settings_html = f'<p class="metric-setting-note">{" ".join(setting_notes)}</p>' if setting_notes else ''
    rule_note = (
        'Use the first matching rule.' if config_key == 'penalty_yards'
        else 'Use the highest matching score; otherwise use the fallback.'
        if 'thresholds' in config else 'Use the exact game count; otherwise use the fallback.'
    )
    if 'thresholds' in config and config_key != 'penalty_yards':
        rule_note += ' Game values are rounded to two decimals before scoring.'
    return (
        f'<p>{html.escape(metric.description)}.</p>'
        + contribution + f'<p class="metric-contribution-note">{contribution_note}</p>'
        + settings_html
        + '<h4>Game values → TOER points</h4>' + history
        + '<details class="metric-scoring"><summary>Scoring thresholds &amp; points</summary>'
        f'<p>{rule_note}</p>'
        '<table><thead><tr><th scope="col">Game value</th><th scope="col">Points</th></tr></thead>'
        f'<tbody>{rule_rows}</tbody></table></details>'
    )
