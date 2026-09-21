"""Regression coverage for audit findings in displayed and exported analyses."""

from copy import deepcopy
from dataclasses import replace
from io import BytesIO
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pandas as pd
import pytest

from src.application.dto import TeamAnalysisRequest, TeamAnalysisResponse
from src.domain.entities import Game, GameStats, GameType, Location, OffensiveStats, Season, SeasonStats, Team
from src.presentation.streamlit.components import methodology_renderer, metrics_renderer, tab_manager
from src.presentation.streamlit.controllers.team_analysis_controller import TeamAnalysisController
from src.presentation.streamlit.services.chart_generation_service import ChartGenerationService
from src.presentation.streamlit.services.export_service import EXCEL_AVAILABLE, ExportService
from src.utils.configuration_utils import get_configuration
from src.utils.ranking_utils import calculate_performance_rank


@pytest.fixture
def response():
    team, opponent, season = Team.from_abbreviation('DET'), Team.from_abbreviation('WAS'), Season(2024)
    offense = replace(OffensiveStats.empty(), yards_per_play=6.1, toer=90.0, success_rate=50.0)
    defense = replace(OffensiveStats.empty(), yards_per_play=5.0, toer=65.0)
    game = Game('2024_20_WAS_DET', season, 20, '2025-01-18', team, opponent, GameType.PLAYOFF)
    season_stats = SeasonStats(
        team=team, season=season, games_played=1, avg_yards_per_play=6.1,
        total_yards=366, total_plays=60, turnovers_per_game=0.0, completion_pct=0.0,
        rush_ypc=0.0, sacks_per_game=0.0, third_down_pct=0.0, success_rate=50.0,
        first_downs_per_game=0.0, points_per_drive=0.0, redzone_td_pct=0.0,
        penalty_yards_per_game=0.0, toer=90.0, toer_allowed=65.0,
        first_down_successful_plays=10, first_down_total_plays=20,
        second_down_successful_plays=10, second_down_total_plays=20,
        third_down_successful_plays=8, third_down_total_plays=16,
        fourth_down_successful_plays=2, fourth_down_total_plays=4,
    )
    return TeamAnalysisResponse(
        team, season, season_stats, [GameStats(game, team, opponent, Location.HOME, offense, defense)],
        rankings={'avg_yards_per_play': calculate_performance_rank(14, 14)},
        league_averages={'avg_yards_per_play': 5.8},
        configuration=get_configuration('analytics_clean'), season_type_filter='POST',
    )


def _streamlit():
    ui = MagicMock()
    ui.get_option.side_effect = lambda key: "light" if key == "theme.base" else "#1f77b4"
    ui.tabs.side_effect = lambda labels: [MagicMock() for _ in labels]
    ui.columns.side_effect = lambda count: [MagicMock() for _ in range(count)]
    return ui


def test_controller_preserves_an_independent_settings_snapshot(response):
    orchestrator = Mock()
    orchestrator.calculate_team_analysis.return_value = SimpleNamespace(
        season_stats=response.season_stats, game_stats=response.game_stats, team_record=None,
        raw_rankings={'avg_yards_per_play': 14}, league_averages=response.league_averages,
        league_team_count=14,
    )
    config = get_configuration('analytics_clean')
    config['custom_metadata'] = {'label': 'original'}
    expected = deepcopy(config)
    request = TeamAnalysisRequest('DET', 2024, 'POST', config)

    result = TeamAnalysisController(orchestrator).analyze_team(request)
    request.configuration['custom_metadata']['label'] = 'changed'

    assert result.configuration == expected
    assert result.season_type_filter == 'POST'
    assert result.rankings['avg_yards_per_play'].total_teams == 14


@pytest.mark.parametrize('filter_name,expected_weeks', [
    ('POST', ['P2']),
    ('ALL', [str(week) for week in range(1, 19)] + ['P2']),
    ('REG', [str(week) for week in range(1, 19)]),
])
def test_game_and_toer_tables_only_create_rows_for_selected_season_type(monkeypatch, response, filter_name, expected_weeks):
    ui = _streamlit()
    monkeypatch.setattr(tab_manager, 'st', ui)
    manager = object.__new__(tab_manager.TabManager)
    response.season_type_filter = filter_name
    if filter_name == 'REG':
        response.game_stats[0].game = replace(response.game_stats[0].game, week=1, game_type=GameType.REGULAR)
    manager._render_game_log_tab(response)
    manager._render_toer_breakdown_tab(response)

    # Game log plus offensive and allowed TOER tables all use the selected rows.
    frames = [call.args[0].data for call in ui.dataframe.call_args_list]
    assert len(frames) == 3
    for frame in frames:
        assert frame['Week'].tolist() == expected_weeks
        if filter_name == 'POST':
            assert frame['Opponent'].tolist() == ['WAS']


def test_comparison_and_metric_cards_use_actual_rank_cohort(monkeypatch, response):
    ui = _streamlit()
    monkeypatch.setattr(tab_manager, 'st', ui)
    monkeypatch.setattr(metrics_renderer, 'st', ui)
    manager = object.__new__(tab_manager.TabManager)
    manager._render_league_comparison_tab(response)
    metrics_renderer.MetricsRenderer()._render_metric_with_rank('Yards/Play', '6.10', response.rankings['avg_yards_per_play'])

    assert ui.dataframe.call_args.args[0]['Rank'].tolist() == ['14/14']
    assert '#14/14' in ui.markdown.call_args.args[0]
    assert 'Worst in cohort' in ui.error.call_args.args[0]


@pytest.mark.parametrize('config_name,included', [('nfl_official', True), ('analytics_clean', False)])
def test_methodology_uses_selected_configuration(monkeypatch, response, config_name, included):
    ui = _streamlit()
    monkeypatch.setattr(methodology_renderer, 'st', ui)
    response.configuration = get_configuration(config_name)
    renderer = methodology_renderer.MethodologyRenderer()
    renderer.render_methodology_page(response)
    text = '\n'.join(call.args[0] for call in ui.markdown.call_args_list)
    action = 'Includes' if included else 'Excludes'
    assert f'{action} spikes in completion percentage.' in text
    assert f'{action} QB kneels in rushing.' in text
    assert '**Selected games:** Playoffs' in text
    assert 'including qualifying touchdown plays' in text
    assert 'Excludes touchdowns' not in text
    assert '30 ÷ 60' in text
    assert 'opposing return-team fumbles' in text
    assert 'kneel-only possessions' in text


def test_methodology_describes_mixed_settings_independently(monkeypatch, response):
    monkeypatch.setattr(methodology_renderer, 'st', _streamlit())
    response.configuration = dict(include_qb_kneels_rushing=False, include_qb_kneels_success_rate=True,
                                  include_spikes_completion=True, include_spikes_success_rate=False)
    renderer = methodology_renderer.MethodologyRenderer()
    renderer.analysis_response = response
    renderer._render_stat_card = Mock()
    renderer._render_core_metrics()
    renderer._render_efficiency_metrics()
    cards = {call.args[0]: call.args[2] for call in renderer._render_stat_card.call_args_list}
    assert 'Excludes QB kneels.' in cards['Rushing Yards Per Carry']
    assert 'Includes spikes.' in cards['Completion Percentage']
    assert 'Includes QB kneels.' in cards['Play Success Rate']
    assert 'Excludes spikes.' in cards['Play Success Rate']
    assert 'Excludes QB kneels.' in cards['Yards Per Play']
    assert 'Excludes spikes.' in cards['Yards Per Play']


def test_methodology_without_analysis_renders_example_cards(monkeypatch):
    ui = _streamlit()
    monkeypatch.setattr(methodology_renderer, 'st', ui)
    methodology_renderer.MethodologyRenderer().render_methodology_page()
    assert any('53.76%' in call.args[0] for call in ui.markdown.call_args_list)


@pytest.mark.parametrize('team_code,year,expected_name', [
    ('LA', 2015, 'St. Louis Rams'),
    ('WAS', 2019, 'Washington Redskins'),
    ('WAS', 2020, 'Washington Football Team'),
    ('WAS', 2021, 'Washington Football Team'),
    ('WAS', 2022, 'Washington Commanders'),
])
def test_historical_names_match_header_methodology_and_exports(monkeypatch, response, team_code, year, expected_name):
    ui = _streamlit()
    monkeypatch.setattr(metrics_renderer, 'st', ui)
    monkeypatch.setattr(methodology_renderer, 'st', ui)
    response.team = Team.from_abbreviation(team_code)
    response.season = Season(year)
    metrics_renderer.MetricsRenderer().render_team_header(response.team, response.season)
    header = '\n'.join(call.args[0] for call in ui.markdown.call_args_list)
    assert f'{expected_name} {year}' in header
    ui.markdown.reset_mock()
    methodology_renderer.MethodologyRenderer().render_methodology_page(response)
    text = '\n'.join(call.args[0] for call in ui.markdown.call_args_list)
    assert f'{expected_name} {year}' in text
    if expected_name != response.team.name:
        assert response.team.name not in header
        assert response.team.name not in text
    service = ExportService()
    exported = json.loads(service.export_to_json(response))
    assert exported['team']['name'] == expected_name
    assert exported['analysis']['team_name'] == expected_name
    assert service._prepare_season_summary(response).iloc[0]['Team'] == expected_name
    csv = pd.read_csv(BytesIO(service.export_to_csv(response)))
    assert csv.iloc[0]['Team'] == expected_name


def test_csv_and_json_preserve_game_scores_and_analysis_context(response):
    service = ExportService()
    csv = pd.read_csv(BytesIO(service.export_to_csv(response)))
    row = csv.iloc[0]
    assert row['TOER'] == 90.0
    assert row['TOER_Allowed'] == 65.0
    assert row['Game_ID'] == '2024_20_WAS_DET'
    assert row['Game_Date'] == '2025-01-18'
    assert row['Season_Type_Filter'] == 'POST'
    assert json.loads(row['Configuration']) == response.configuration
    data = json.loads(service.export_to_json(response))
    assert data['analysis']['configuration'] == response.configuration
    assert data['analysis']['season_type_filter'] == 'POST'
    assert data['season_stats']['toer_allowed'] == 65.0
    assert data['season_stats']['fourth_down_total_plays'] == 4
    assert data['game_stats'][0]['game_id'] == '2024_20_WAS_DET'
    assert data['game_stats'][0]['week'] == 20
    assert data['game_stats'][0]['game_date'] == '2025-01-18'
    assert data['game_stats'][0]['toer'] == 90.0
    assert data['game_stats'][0]['defensive_stats']['yards_per_play'] == 5.0
    assert data['game_stats'][0]['toer_allowed'] == 65.0
    assert data['rankings']['avg_yards_per_play']['total_teams'] == 14


@pytest.mark.skipif(not EXCEL_AVAILABLE, reason='Excel export requires openpyxl')
def test_excel_preserves_settings_and_both_toer_values(response):
    sheets = pd.read_excel(BytesIO(ExportService().export_to_excel(response)), sheet_name=None)
    assert sheets['Game_Log']['TOER'].tolist() == [90.0]
    assert sheets['Game_Log']['TOER_Allowed'].tolist() == [65.0]
    assert sheets['Season_Summary']['TOER_Allowed'].tolist() == [65.0]
    settings = sheets['Analysis_Settings'].set_index('Field')['Value']
    assert settings['season_type_filter'] == 'POST'
    assert json.loads(settings['configuration']) == response.configuration
    assert sheets['Rankings']['Total_Teams'].tolist() == [14]


def test_chart_helpers_read_nested_stats_and_cohort(response):
    charts = ChartGenerationService()
    trend = charts.create_trends_chart(response)
    assert list(trend.data[0].y) == [6.1]
    radar = charts.create_ranking_comparison_chart(response)
    assert list(radar.data[0].r) == pytest.approx([100 / 14, 100 / 14])
    response.rankings['avg_yards_per_play'] = calculate_performance_rank(1, 1)
    assert list(charts.create_ranking_comparison_chart(response).data[0].r) == [100, 100]


@pytest.mark.parametrize('rank,total,description,label', [
    (1, 14, 'Best in cohort', '1st'),
    (14, 14, 'Worst in cohort', 'Bottom 8%'),
    (7, 14, 'Above Average', 'Top 50%'),
    (8, 14, 'Below Average', 'Bottom 50%'),
    (2, 32, 'Elite', 'Top 7%'),
    (32, 32, 'Worst in NFL', 'Bottom 4%'),
    (1, 1, 'Best in cohort', '1st'),
])
def test_rank_descriptions_scale_to_cohort(rank, total, description, label):
    result = calculate_performance_rank(rank, total)
    assert result.description == description
    assert result.percentile == label
    assert result.is_above_average == (rank == 1 or rank <= total / 2)
