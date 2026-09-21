"""Operation lifecycle and browser-independent figure styling regressions."""

from unittest.mock import MagicMock, Mock

import pandas as pd
import pytest
import streamlit as st

from src.presentation.streamlit.components import progress_manager
from src.presentation.streamlit.services.chart_generation_service import ChartGenerationService


@pytest.fixture
def status_ui(monkeypatch):
    ui = MagicMock()
    monkeypatch.setattr(progress_manager, 'st', ui)
    return ui


def test_loading_status_follows_callbacks_and_only_completes_after_work(status_ui):
    manager = progress_manager.ProgressManager()
    with manager.track_progress(100, 'Loading analysis'):
        status_ui.status.assert_called_once_with(
            'Loading analysis', state='running', type='compact'
        )
        manager.update(100, 'Source data loaded')
        manager.update(30, 'Calculating team statistics')
        # A nested source can report 100% while the overall operation is unfinished.
        assert all(call.kwargs.get('state') != 'complete'
                   for call in status_ui.status.return_value.update.call_args_list)
        assert manager.current_step == 30
        status_ui.progress.assert_not_called()
    status_ui.status.return_value.update.assert_called_with(state='complete')
    status_ui.empty.return_value.empty.assert_called_once_with()
    assert manager.status is None
    assert manager.current_step == 100


def test_failed_work_is_never_marked_complete_and_original_error_survives_cleanup(status_ui):
    status_ui.empty.return_value.empty.side_effect = RuntimeError('Cleanup failed')
    failure = ValueError('Analysis failed')
    manager = progress_manager.ProgressManager()
    with pytest.raises(ValueError) as caught:
        with manager.track_progress():
            manager.update(100, 'Data loaded')
            raise failure
    assert caught.value is failure
    assert manager.status is None
    status_ui.status.return_value.update.assert_called_with(state='error')
    assert all(call.kwargs.get('state') != 'complete'
               for call in status_ui.status.return_value.update.call_args_list)
    status_ui.empty.return_value.empty.assert_called_once_with()
    # Cleanup is idempotent, including when Streamlit could not remove the element.
    manager._cleanup_progress()
    status_ui.empty.return_value.empty.assert_called_once_with()


def test_cancellation_cleans_status_without_claiming_success(status_ui):
    class Cancelled(BaseException):
        pass

    with pytest.raises(Cancelled):
        with progress_manager.ProgressManager().track_progress():
            raise Cancelled()
    status_ui.status.return_value.update.assert_not_called()
    status_ui.empty.return_value.empty.assert_called_once_with()


def test_details_replace_in_place_and_disappear_when_next_operation_has_none(status_ui):
    with progress_manager.ProgressManager().track_progress() as manager:
        manager.update(5, 'Checking data', {'Downloaded': True, 'Rankings': False})
        manager.update(10, 'Computing', {'Teams': 12})
        details = status_ui.status.return_value.empty.return_value
        assert [call.args[0] for call in details.text.call_args_list] == [
            'Downloaded: Complete\nRankings: In progress', 'Teams: 12'
        ]
        manager.update(20, 'Preparing display')
        details.empty.assert_called_once_with()
        status_ui.status.return_value.empty.assert_called_once_with()
        status_ui.markdown.assert_not_called()


@pytest.mark.parametrize('total', [0, -1, float('nan'), float('inf'), '100', True])
def test_invalid_totals_do_not_create_a_loading_indicator(status_ui, total):
    with pytest.raises(ValueError):
        with progress_manager.ProgressManager().track_progress(total):
            pytest.fail('Invalid total entered operation')
    status_ui.status.assert_not_called()


def test_steps_are_clamped_and_nonfinite_values_rejected(status_ui):
    manager = progress_manager.ProgressManager()
    with manager.track_progress(10):
        manager.update(-2)
        assert manager.current_step == 0
        manager.update(50)
        assert manager.current_step == 10
        with pytest.raises(ValueError):
            manager.update(float('nan'))
        with pytest.raises(ValueError):
            manager.update(float('inf'))
    with pytest.raises(RuntimeError):
        manager.update(1)


def test_stage_failure_does_not_count_as_completed_and_tracker_can_be_reused(status_ui):
    progress = progress_manager.MultiStageProgress({'Loading': 30, 'Computing': 70})
    with pytest.raises(ValueError, match='Bad data'):
        with progress.track_overall_progress():
            with progress.stage('Loading'):
                pass
            with progress.stage('Computing') as stage:
                stage.update(0.5, 'Processing teams')
                raise ValueError('Bad data')
    assert progress.completed_weight == 30
    assert progress.current_stage is None
    assert progress.pm is None
    labels = [call.kwargs.get('label') for call in status_ui.status.return_value.update.call_args_list]
    assert 'Loading complete' in labels
    assert 'Computing complete' not in labels
    with progress.track_overall_progress():
        assert progress.completed_weight == 0
        with progress.stage('Loading'):
            pass
        with progress.stage('Computing'):
            pass
    assert progress.completed_weight == 100


def test_stage_fraction_cannot_overrun_its_own_stage():
    manager = Mock()
    stage = progress_manager.StageProgress(manager, 30, 20, 'Computing')
    stage.update(-1, 'Starting')
    stage.update(2, 'Finishing')
    assert [call.args[0] for call in manager.update.call_args_list] == [30, 50]
    with pytest.raises(ValueError):
        stage.update(float('nan'))


def test_live_comparison_figure_leaves_background_and_text_theme_to_streamlit(monkeypatch):
    def forbidden_config_read(*args):
        pytest.fail('Server theme configuration does not identify the viewer theme')

    monkeypatch.setattr(st, 'get_option', forbidden_config_read)
    comparison = pd.DataFrame({
        'Metric': ['Yards / play', 'Points / drive'],
        'DET': ['6.10', '2.20'],
        'League Avg': ['5.80', '2.10'],
    })
    figure = ChartGenerationService.create_league_comparison_chart(comparison, 'DET')
    assert [trace.name for trace in figure.data] == ['Your Team', 'League Average']
    assert list(figure.data[0].x) == list(figure.data[1].x) == comparison['Metric'].tolist()
    assert list(figure.data[0].y) == [6.1, 2.2]
    assert list(figure.data[1].y) == [5.8, 2.1]
    assert list(figure.data[0].text) == ['6.10', '2.20']
    # No baked-in Plotly light/dark template can override the browser's theme.
    assert figure.layout.template.to_plotly_json() == {}
    assert figure.layout.paper_bgcolor is None
    assert figure.layout.plot_bgcolor is None
    assert figure.layout.font.color is None
