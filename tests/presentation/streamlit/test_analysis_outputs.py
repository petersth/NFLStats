"""Regression coverage for audit findings in displayed and exported analyses."""

from copy import deepcopy
from dataclasses import replace
from functools import partial
from io import BytesIO
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock
from xml.etree import ElementTree

import pandas as pd
import pytest
from streamlit import column_config
from streamlit.testing.v1 import AppTest

from src.application.dto import TeamAnalysisRequest, TeamAnalysisResponse
from src.domain.entities import Game, GameStats, GameType, Location, OffensiveStats, Season, SeasonStats, Team
from src.presentation.streamlit.components import methodology_renderer, metrics_renderer, tab_manager
from src.presentation.streamlit.controllers.team_analysis_controller import TeamAnalysisController
from src.presentation.streamlit.services import export_service
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
    ui.tabs.side_effect = lambda labels, **kwargs: [MagicMock() for _ in labels]
    ui.session_state = {}
    ui.columns.side_effect = lambda count: [MagicMock() for _ in range(count)]
    ui.column_config = column_config
    return ui


def _display_frame(value):
    return value if isinstance(value, pd.DataFrame) else value.data


def test_controller_preserves_an_independent_settings_snapshot(response):
    orchestrator = Mock()
    orchestrator.calculate_team_analysis.return_value = SimpleNamespace(
        season_stats=response.season_stats, game_stats=response.game_stats, team_record=None,
        raw_rankings={'avg_yards_per_play': 14}, league_averages=response.league_averages,
        league_team_count=14, source_data_timestamp=None, source_data_expires_at=None,
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
    ('ALL', ['P2']),
    ('REG', ['1']),
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
    frames = [_display_frame(call.args[0]) for call in ui.dataframe.call_args_list]
    assert len(frames) == 3
    for frame in frames:
        assert frame['Week'].tolist() == expected_weeks
        assert frame['Opponent'].tolist() == ['WAS']


@pytest.mark.parametrize('year,last_regular_week', [(2020, 17), (2024, 18)])
def test_game_and_toer_tables_sort_available_games_and_preserve_scores(monkeypatch, response, year, last_regular_week):
    ui = _streamlit()
    monkeypatch.setattr(tab_manager, 'st', ui)
    response.season = Season(year)
    response.season_type_filter = 'ALL'
    original = response.game_stats[0]
    # Include a gap and an absent playoff round, with source games out of order.
    weeks = [last_regular_week + 2, 3, last_regular_week, 1]
    response.game_stats = [
        replace(
            original,
            game=replace(original.game, season=response.season, week=week,
                         game_type=GameType.REGULAR if week <= last_regular_week else GameType.PLAYOFF),
            offensive_stats=replace(original.offensive_stats, toer=float(week)),
            defensive_stats=replace(original.defensive_stats, toer=float(week + 20)),
        )
        for week in weeks
    ]
    manager = object.__new__(tab_manager.TabManager)
    manager._render_game_log_tab(response)
    manager._render_toer_breakdown_tab(response)

    frames = [_display_frame(call.args[0]) for call in ui.dataframe.call_args_list]
    assert len(frames) == 3
    for frame in frames:
        assert frame['Week'].tolist() == ['1', '3', str(last_regular_week), 'P2']
        assert frame['Opponent'].tolist() == ['WAS'] * 4
    for frame in frames[:2]:
        assert frame['TOER'].tolist() == sorted(weeks)
    for frame in (frames[0], frames[2]):
        assert frame['TOER Allowed'].tolist() == [week + 20 for week in sorted(weeks)]
    assert '4 games</span>' in ui.markdown.call_args_list[0].args[0]


def test_game_log_shows_all_original_statistics_together(monkeypatch, response):
    ui = _streamlit()
    monkeypatch.setattr(tab_manager, 'st', ui)
    response.game_stats[0].offensive_stats = replace(
        response.game_stats[0].offensive_stats,
        turnovers=2, completion_pct=67.89, rush_ypc=4.56, sacks=3,
        third_down_pct=41.23, first_downs=24, points_per_drive=2.78,
        redzone_td_pct=66.67, penalty_yards=35,
    )
    expected = {
        'Week': 'P2', 'Opponent': 'WAS', 'Location': 'Home', 'Yds/Play': 6.1,
        'Turnovers': 2, 'Pass Comp%': 67.89, 'Rush YPC': 4.56, 'Sacks': 3,
        '3rd Down%': 41.23, 'Success%': 50.0, '1st Downs': 24, 'Pts/Drive': 2.78,
        'RZ TD%': 66.67, 'Pen Yards': 35, 'TOER': 90.0, 'TOER Allowed': 65.0,
    }

    object.__new__(tab_manager.TabManager)._render_game_log_tab(response)

    frame = ui.dataframe.call_args.args[0]
    assert frame.columns.tolist() == list(expected)
    assert frame.iloc[0].to_dict() == expected
    ui.dataframe.assert_called_once()
    assert ui.dataframe.call_args.kwargs['placeholder'] == '-'
    ui.segmented_control.assert_not_called()
    ui.radio.assert_not_called()
    ui.caption.assert_not_called()
    heading = ui.markdown.call_args.args[0]
    assert '<div class="game-log-heading"><h3>Game log</h3>' in heading
    assert '<span title="Games with available statistics">1 game</span>' in heading

    columns = ui.dataframe.call_args.kwargs['column_config']
    assert columns['Week']['pinned'] is True
    assert columns['Week']['width'] == 45
    assert columns['Opponent']['pinned'] is True
    assert columns['Opponent']['width'] == 55
    assert sum(column['width'] for column in columns.values()) <= 1000
    order = ui.dataframe.call_args.kwargs['column_order']
    assert order[:5] == ['Week', 'Opponent', 'Location', 'TOER', 'TOER Allowed']
    assert set(order) == set(expected)
    assert columns['Turnovers']['label'] == 'TO'
    assert columns['TOER Allowed']['label'] == 'Allowed'
    assert "Opponent's" in columns['TOER Allowed']['help']
    for key in ('Pass Comp%', '3rd Down%', 'Success%', 'RZ TD%'):
        number_format = columns[key]['type_config']['format']
        assert number_format == '%.2f%%'
        assert number_format % frame.iloc[0][key] == f'{expected[key]:.2f}%'
    for key in ('Turnovers', 'Sacks', '1st Downs', 'Pen Yards'):
        assert columns[key]['type_config']['format'] == '%.0f'
        assert 'this game' in columns[key]['help']
    for key in ('Yds/Play', 'Rush YPC', 'Pts/Drive', 'TOER', 'TOER Allowed'):
        assert columns[key]['type_config']['format'] == '%.2f'


def test_game_log_without_game_metadata_keeps_all_statistics(monkeypatch, response):
    ui = _streamlit()
    monkeypatch.setattr(tab_manager, 'st', ui)
    response.game_stats[0].game = None

    object.__new__(tab_manager.TabManager)._render_game_log_tab(response)

    frame = ui.dataframe.call_args.args[0]
    assert frame['Game'].tolist() == [1]
    assert 'Week' not in frame
    assert frame['TOER'].tolist() == [90.0]
    assert frame['TOER Allowed'].tolist() == [65.0]
    assert len(frame.columns) == 16
    columns = ui.dataframe.call_args.kwargs['column_config']
    assert columns['Game']['pinned'] is True
    assert columns['Game']['width'] == 45
    assert columns['Game']['type_config']['format'] == '%.0f'
    assert 'Week' not in columns


def test_empty_game_log_has_no_table(monkeypatch, response):
    ui = _streamlit()
    monkeypatch.setattr(tab_manager, 'st', ui)
    response.game_stats = []

    object.__new__(tab_manager.TabManager)._render_game_log_tab(response)

    ui.info.assert_called_once_with('No game data available.')
    ui.dataframe.assert_not_called()
    assert '<h3>Game log</h3>' in ui.markdown.call_args.args[0]


def test_comparison_and_metric_cards_use_actual_rank_cohort(monkeypatch, response):
    ui = _streamlit()
    monkeypatch.setattr(tab_manager, 'st', ui)
    monkeypatch.setattr(metrics_renderer, 'st', ui)
    manager = object.__new__(tab_manager.TabManager)
    manager._render_league_comparison_tab(response)
    metrics_renderer.MetricsRenderer().render_season_metrics(response)

    assert ui.dataframe.call_args.args[0]['Rank'].tolist() == ['14/14']
    assert ui.dataframe.call_args.args[0]['Metric'].tolist() == ['Yards / play']
    assert '14th of 14' in ui.markdown.call_args.args[0]
    rendered = '\n'.join(call.args[0] for call in ui.markdown.call_args_list)
    assert 'Worst in cohort' not in rendered
    ui.error.assert_not_called()


def test_header_pairs_each_rating_with_its_own_league_context(monkeypatch, response):
    ui = _streamlit()
    monkeypatch.setattr(metrics_renderer, 'st', ui)
    metrics_renderer.MetricsRenderer().render_team_header(
        response.team, response.season, season_stats=response.season_stats,
        toer_rank=calculate_performance_rank(2, 14), league_toer=55.5,
        toer_allowed_rank=calculate_performance_rank(10, 14), league_toer_allowed=48.2,
    )
    rendered = ui.markdown.call_args.args[0]
    offense, defense = rendered.split('aria-label="Defensive TOER allowed"')
    assert 'title="League rank">Rank <strong>2 of 14</strong>' in offense
    assert 'title="League average">Avg <strong>55.5</strong>' in offense
    assert 'title="League rank">Rank <strong>10 of 14</strong>' in defense
    assert 'title="League average">Avg <strong>48.2</strong>' in defense
    assert 'No data available' not in rendered


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
    assert f'<h2>{expected_name}</h2>' in header
    metadata = header.split('<div class="season-team-metadata">', 1)[1].split('</div>', 1)[0]
    assert str(year) in metadata
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


def test_exports_are_deferred_and_download_the_rendered_response(monkeypatch, response):
    ui = _streamlit()
    ui.selectbox.return_value = 'Game Log'
    monkeypatch.setattr(tab_manager, 'st', ui)
    service = ExportService()
    service.export_to_csv = Mock(wraps=service.export_to_csv)
    service.export_to_excel = Mock(wraps=service.export_to_excel)
    service.export_to_json = Mock(wraps=service.export_to_json)
    manager = object.__new__(tab_manager.TabManager)
    manager._export_service = service
    manager._render_export_tab(response)

    for serializer in (service.export_to_csv, service.export_to_excel, service.export_to_json):
        serializer.assert_not_called()
    buttons = {call.kwargs['mime']: call.kwargs for call in ui.download_button.call_args_list}
    assert len(buttons) == (3 if EXCEL_AVAILABLE else 2)
    assert all(callable(button['data']) and button['on_click'] == 'ignore' for button in buttons.values())
    assert buttons['text/csv']['file_name'] == 'DET_2024_stats.csv'
    assert buttons['application/json']['file_name'] == 'DET_2024_data.json'

    expected_config = deepcopy(response.configuration)
    response.configuration['include_spikes_completion'] = True
    response.season_type_filter = 'REG'
    response.game_stats[0].offensive_stats = replace(response.game_stats[0].offensive_stats, toer=22.0)
    response.game_stats[0].game = replace(response.game_stats[0].game, week=1, game_type=GameType.REGULAR)

    # A callback captures what its visible button represented, even if another
    # session interaction has since changed the source response.
    csv = pd.read_csv(BytesIO(buttons['text/csv']['data']()))
    assert csv['Week'].tolist() == ['P2']
    assert csv['TOER'].tolist() == [90.0]
    assert csv['Season_Type_Filter'].tolist() == ['POST']
    assert json.loads(csv['Configuration'].iloc[0]) == expected_config
    service.export_to_json.assert_not_called()
    service.export_to_excel.assert_not_called()
    data = json.loads(buttons['application/json']['data']())
    assert data['analysis']['season_type_filter'] == 'POST'
    assert data['analysis']['configuration'] == expected_config
    assert data['game_stats'][0]['week'] == 20
    assert data['game_stats'][0]['toer'] == 90.0
    if EXCEL_AVAILABLE:
        excel = buttons['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']
        assert excel['file_name'] == 'DET_2024_analysis.xlsx'
        sheets = pd.read_excel(BytesIO(excel['data']()), sheet_name=None)
        assert sheets['Game_Log']['Week'].tolist() == ['P2']
        assert sheets['Game_Log']['TOER'].tolist() == [90.0]

    # The next render creates callbacks for the new filter and new statistics.
    ui.download_button.reset_mock()
    manager._render_export_tab(response)
    new_json = next(call.kwargs['data'] for call in ui.download_button.call_args_list
                    if call.kwargs['mime'] == 'application/json')
    updated = json.loads(new_json())
    assert updated['analysis']['season_type_filter'] == 'REG'
    assert updated['game_stats'][0]['week'] == 1
    assert updated['game_stats'][0]['toer'] == 22.0


def test_excel_unavailable_is_disabled_without_attempting_generation(monkeypatch, response):
    ui = _streamlit()
    ui.selectbox.return_value = 'Game Log'
    monkeypatch.setattr(tab_manager, 'st', ui)
    monkeypatch.setattr(export_service, 'EXCEL_AVAILABLE', False)
    manager = object.__new__(tab_manager.TabManager)
    manager._export_service = ExportService()
    manager._export_service.export_to_excel = Mock()

    manager._render_export_tab(response)

    manager._export_service.export_to_excel.assert_not_called()
    assert len(ui.download_button.call_args_list) == 2
    assert ui.button.call_args.kwargs['disabled'] is True
    assert ui.button.call_args.kwargs['label'] == 'Excel (Not Available)'


def test_native_tabs_render_only_active_content_and_refresh_response(response):
    app = AppTest.from_string('''
import streamlit as st
from src.presentation.streamlit.components.tab_manager import TabManager
TabManager(None).render_analysis_tabs(st.session_state['analysis_response'])
''')
    app.session_state['analysis_response'] = response
    app.run()
    assert not app.exception
    assert [tab.label for tab in app.tabs] == [
        'Game Log', 'TOER Breakdown', 'League Comparison', 'Methodology', 'Export Data',
    ]
    assert len(app.dataframe) == 1
    assert app.dataframe[0].value['Week'].tolist() == ['P2']
    assert len(app.get('plotly_chart')) == 0
    assert len(app.get('download_button')) == 0
    assert len(app.tabs[3].markdown) == 0

    app.session_state['analysis_tabs'] = 'TOER Breakdown'
    app.run()
    assert not app.exception
    assert len(app.dataframe) == 2
    assert len(app.tabs[0].dataframe) == 0
    assert len(app.get('download_button')) == 0

    app.session_state['analysis_tabs'] = 'League Comparison'
    app.run()
    assert not app.exception
    assert len(app.get('plotly_chart')) == 1
    assert len(app.dataframe) == 1
    assert app.dataframe[0].value['Rank'].tolist() == ['14/14']
    assert len(app.tabs[0].dataframe) == 0

    app.session_state['analysis_tabs'] = 'Methodology'
    app.run()
    assert not app.exception
    assert len(app.dataframe) == 0
    assert len(app.get('plotly_chart')) == 0
    assert any('**Selected games:** Playoffs' in item.value for item in app.markdown)

    app.session_state['analysis_tabs'] = 'Export Data'
    app.run()
    assert not app.exception
    assert len(app.dataframe) == 1
    assert len(app.get('download_button')) == (3 if EXCEL_AVAILABLE else 2)
    assert all(button.proto.ignore_rerun for button in app.get('download_button'))
    # AppTest currently represents tabs as containers, not widgets. Seed their
    # state before reruns because it cannot serialize a browser's tab selection.
    app.session_state['analysis_tabs'] = 'Export Data'
    app.selectbox[0].select('Season Summary').run()
    assert not app.exception
    assert app.dataframe[0].value['Season_Type_Filter'].tolist() == ['POST']

    app.session_state['analysis_tabs'] = 'Game Log'
    app.run()
    assert len(app.get('download_button')) == 0
    assert len(app.selectbox) == 0
    app.session_state['analysis_tabs'] = 'Export Data'
    app.run()
    assert app.selectbox[0].value == 'Season Summary'

    updated = deepcopy(response)
    updated.season_type_filter = 'REG'
    updated.configuration = get_configuration('nfl_official')
    updated.game_stats[0].game = replace(updated.game_stats[0].game, week=1, game_type=GameType.REGULAR)
    app.session_state['analysis_response'] = updated
    app.session_state['analysis_tabs'] = 'Export Data'
    app.run()
    assert not app.exception
    assert app.session_state['analysis_tabs'] == 'Export Data'
    assert app.selectbox[0].value == 'Season Summary'
    assert app.dataframe[0].value['Season_Type_Filter'].tolist() == ['REG']
    assert json.loads(app.dataframe[0].value['Configuration'].iloc[0]) == updated.configuration
    app.session_state['analysis_tabs'] = 'Export Data'
    app.selectbox[0].select('Game Log').run()
    assert app.dataframe[0].value['Week'].tolist() == ['1']


@pytest.mark.parametrize('cache_enabled,expiry,now,should_refresh', [
    (True, 1000.0, 999.9, False),
    (True, 1000.0, 1000.0, True),
    (True, 1000.0, 1000.1, True),
    (True, None, 1000.0, False),
    (False, 1000.0, 1000.1, False),
])
def test_tab_interaction_refreshes_only_expired_cached_source(
    monkeypatch, response, cache_enabled, expiry, now, should_refresh,
):
    ui = _streamlit()
    ui.rerun.side_effect = RuntimeError('Requested full app rerun')
    monkeypatch.setattr(tab_manager, 'st', ui)
    monkeypatch.setattr(tab_manager.time, 'time', lambda: now)
    response.source_data_expires_at = expiry
    manager = tab_manager.TabManager(None)
    # Exercise the fragment body without requiring Streamlit's private runtime.
    manager.render_tabs = partial(tab_manager.TabManager.render_tabs.__wrapped__, manager)
    for name in ('game_log', 'toer_breakdown', 'league_comparison', 'methodology', 'export'):
        setattr(manager, f'_render_{name}_tab', Mock())

    # A new full app render is allowed even if a slow analysis crossed expiry.
    manager.render_analysis_tabs(response, cache_nfl_data=cache_enabled)
    ui.rerun.assert_not_called()
    assert ui.tabs.call_count == 1

    if should_refresh:
        with pytest.raises(RuntimeError, match='Requested full app rerun'):
            manager.render_tabs(response, cache_nfl_data=cache_enabled)
        ui.rerun.assert_called_once_with(scope='app')
        assert ui.tabs.call_count == 1
    else:
        manager.render_tabs(response, cache_nfl_data=cache_enabled)
        ui.rerun.assert_not_called()
        assert ui.tabs.call_count == 2

    # Returning through the full-app entry point resets the render boundary.
    ui.rerun.reset_mock()
    manager.render_analysis_tabs(response, cache_nfl_data=cache_enabled)
    ui.rerun.assert_not_called()


def test_expired_fragment_requests_native_full_rerun_without_a_refresh_loop(response):
    response.source_data_expires_at = 1.0
    app = AppTest.from_string("""
import streamlit as st
from src.presentation.streamlit.components.tab_manager import TabManager
st.session_state['full_runs'] = st.session_state.get('full_runs', 0) + 1
manager = TabManager(None)
response = st.session_state['analysis_response']
manager.render_analysis_tabs(response, cache_nfl_data=True)
if st.session_state['full_runs'] == 1:
    # Invoke the captured fragment again as an interaction would. AppTest's
    # widget driver currently requests full app runs rather than fragment runs.
    manager.render_tabs(response, cache_nfl_data=True)
""")
    app.session_state['analysis_response'] = response
    app.run()
    assert not app.exception
    assert not app.error
    assert app.session_state['full_runs'] == 2
    assert len(app.dataframe) == 1
    assert app.dataframe[0].value['TOER'].tolist() == [90.0]


@pytest.mark.parametrize('team_value,league_value,expected_difference', [
    (0.0, 0.0, None),
    (3.0, 0.0, None),
    (0.0, 3.0, -100.0),
    (2.0, 2.0, 0.0),
    (3.0, 2.0, 50.0),
    (1.0, 2.0, -50.0),
])
def test_comparison_difference_distinguishes_zero_from_undefined(
    monkeypatch, response, team_value, league_value, expected_difference,
):
    ui = _streamlit()
    monkeypatch.setattr(tab_manager, 'st', ui)
    response.season_stats = replace(response.season_stats, avg_yards_per_play=team_value)
    response.league_averages = {'avg_yards_per_play': league_value}

    object.__new__(tab_manager.TabManager)._render_league_comparison_tab(response)

    table = ui.dataframe.call_args.args[0]
    row = table.iloc[0]
    assert row['DET'] == f'{team_value:.2f}'
    assert row['League Avg'] == f'{league_value:.2f}'
    if expected_difference is None:
        assert pd.isna(row['Difference'])
    else:
        assert row['Difference'] == pytest.approx(expected_difference)
    options = ui.dataframe.call_args.kwargs
    assert options['placeholder'] == '-'
    difference = options['column_config']['Difference']
    assert 'undefined' in difference['help']
    assert 'league average is zero' in difference['help']
    assert difference['type_config']['format'] == '%+.2f%%'

    # The live chart keeps actual zero values, not missing/undefined differences.
    figure = ui.plotly_chart.call_args.args[0]
    assert list(figure.data[0].x) == table['Metric'].tolist()
    assert list(figure.data[0].y) == [team_value]
    assert list(figure.data[1].y) == [league_value]
    assert ui.plotly_chart.call_args.kwargs['theme'] == 'streamlit'


def test_comparison_renders_missing_percentages_alone_and_with_defined_values(response):
    app = AppTest.from_string("""
import streamlit as st
from src.presentation.streamlit.components.tab_manager import TabManager
TabManager(None)._render_league_comparison_tab(st.session_state['analysis_response'])
""")
    response.league_averages = {'avg_yards_per_play': 0.0, 'turnovers_per_game': 0.0}
    app.session_state['analysis_response'] = response
    app.run()
    assert not app.exception
    assert not app.error
    assert app.dataframe[0].value['Difference'].isna().all()
    assert len(app.get('plotly_chart')) == 1

    response.league_averages['avg_yards_per_play'] = 5.8
    app.session_state['analysis_response'] = response
    app.run()
    assert not app.exception
    table = app.dataframe[0].value.set_index('Metric')
    assert table.loc['Yards / play', 'Difference'] == pytest.approx((6.1 - 5.8) / 5.8 * 100)
    assert pd.isna(table.loc['Turnovers / game', 'Difference'])


@pytest.mark.parametrize('has_metadata', [True, False])
def test_toer_breakdowns_preserve_all_component_scores_and_both_sides(monkeypatch, response, has_metadata):
    ui = _streamlit()
    monkeypatch.setattr(tab_manager, 'st', ui)
    game = response.game_stats[0]
    if not has_metadata:
        game.game = None
    game.offensive_stats = replace(
        game.offensive_stats, yards_per_play=6.1, turnovers=1, completion_pct=65.0,
        rush_ypc=4.5, sacks=2, third_down_pct=40.0, success_rate=46.0,
        first_downs=20, points_per_drive=2.1, redzone_td_pct=61.0, penalty_yards=35, toer=67.0,
    )
    game.defensive_stats = replace(
        game.defensive_stats, yards_per_play=5.2, turnovers=3, completion_pct=63.0,
        rush_ypc=4.2, sacks=4, third_down_pct=35.0, success_rate=40.0,
        first_downs=17, points_per_drive=1.85, redzone_td_pct=57.0, penalty_yards=80, toer=10.0,
    )
    game_column = 'Week' if has_metadata else 'Game'
    identity = {game_column: 'P2' if has_metadata else 1, 'Opponent': 'WAS', 'Location': 'Home'}
    offense = {
        **identity, 'Yds/Play': 10, 'Turnovers': 5, 'Pass Comp%': 5, 'Rush YPC': 6,
        'Sacks': 5, '3rd Down%': 7, 'Success%': 9, '1st Downs': 8, 'Pts/Drive': 5,
        'RZ TD%': 9, 'Pen Yards': -2, 'TOER': 67.0,
    }
    defense = {
        **identity, 'Yds/Play': 3, 'Turnovers': -3, 'Pass Comp%': 1, 'Rush YPC': 1,
        'Sacks': -1, '3rd Down%': 2, 'Success%': 3, '1st Downs': 5, 'Pts/Drive': 2,
        'RZ TD%': 5, 'Pen Yards': -8, 'TOER Allowed': 10.0,
    }

    object.__new__(tab_manager.TabManager)._render_toer_breakdown_tab(response)

    assert [call.args[0] for call in ui.subheader.call_args_list] == [
        'TOER Component Breakdown', 'TOER Allowed Component Breakdown',
    ]
    assert len(ui.dataframe.call_args_list) == 2
    for call, expected in zip(ui.dataframe.call_args_list, (offense, defense)):
        table = call.args[0]
        assert isinstance(table, pd.DataFrame)
        assert table.columns.tolist() == list(expected)
        assert table.iloc[0].to_dict() == expected
        assert call.kwargs['placeholder'] == '-'
        assert all(column['type_config']['format'] == '%.2f'
                   for column in call.kwargs['column_config'].values())


def test_partial_game_metadata_never_drops_a_row_from_game_or_toer_tables(monkeypatch, response):
    ui = _streamlit()
    monkeypatch.setattr(tab_manager, 'st', ui)
    original = response.game_stats[0]
    missing_metadata = replace(
        original, game=None, opponent=Team.from_abbreviation('GB'), location=Location.AWAY,
        offensive_stats=replace(original.offensive_stats, toer=20.0),
        defensive_stats=replace(original.defensive_stats, toer=30.0),
    )
    response.game_stats = [missing_metadata, original]
    manager = object.__new__(tab_manager.TabManager)
    manager._render_game_log_tab(response)
    manager._render_toer_breakdown_tab(response)

    frames = [call.args[0] for call in ui.dataframe.call_args_list]
    assert len(frames) == 3
    for table in frames:
        assert table['Game'].tolist() == [1, 2]
        assert table['Opponent'].tolist() == ['GB', 'WAS']
        assert table['Location'].tolist() == ['Away', 'Home']
        assert 'Week' not in table
    assert frames[0]['TOER'].tolist() == frames[1]['TOER'].tolist() == [20.0, 90.0]
    assert frames[0]['TOER Allowed'].tolist() == frames[2]['TOER Allowed'].tolist() == [30.0, 65.0]


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


@pytest.mark.parametrize('rank,expected', [(1,'1st'),(2,'2nd'),(3,'3rd'),(11,'11th'),(12,'12th'),(13,'13th'),(21,'21st'),(22,'22nd'),(23,'23rd'),(32,'32nd')])
def test_metric_rank_is_explicit_and_uses_ordinal_suffix(rank, expected):
    rendered = metrics_renderer.MetricsRenderer._metric_with_rank_html(
        'Turnovers / game', '0.50', calculate_performance_rank(rank, 32)
    )
    assert f'{expected} of 32' in rendered
    assert '0.50' in rendered
    assert f'Rank {rank} of 32 teams' in rendered


@pytest.mark.parametrize('rank,total', [(1, 32), (21, 32), (32, 32), (7, 14), (1, 1)])
@pytest.mark.parametrize('higher_is_better', [True, False])
def test_rank_bar_marks_one_whole_rank_slot(rank, total, higher_is_better):
    rendered = metrics_renderer.MetricsRenderer._metric_with_rank_html(
        'Metric', '34.62%', calculate_performance_rank(rank, total),
        higher_is_better=higher_is_better,
    )
    card = ElementTree.fromstring(rendered)
    track = card.find(".//div[@class='season-rank-track']")
    slots = list(track)
    assert [int(slot.get('data-rank')) for slot in slots] == list(range(total, 0, -1))
    current = [slot for slot in slots if 'is-current' in slot.get('class').split()]
    assert len(current) == 1
    assert int(current[0].get('data-rank')) == rank
    filled = [int(slot.get('data-rank')) for slot in slots if 'is-filled' in slot.get('class').split()]
    assert filled == list(range(total, rank - 1, -1))
