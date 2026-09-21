"""Charts rendered by the analysis interface."""

import pandas as pd
import plotly.graph_objects as go


class ChartGenerationService:
    """Build figures without overriding the viewer's Streamlit theme."""

    @staticmethod
    def create_league_comparison_chart(comparison: pd.DataFrame, team_column: str) -> go.Figure:
        """Chart the same metric order and values as the league comparison table."""
        figure = go.Figure()
        for column, label in ((team_column, 'Your Team'), ('League Avg', 'League Average')):
            figure.add_trace(go.Bar(
                name=label,
                x=comparison['Metric'],
                y=comparison[column].astype(float),
                text=comparison[column],
                textposition='outside',
            ))
        figure.update_layout(
            template=None,
            title=dict(
                text='Team Performance vs League Average',
                x=0.5,
                xanchor='center',
                font=dict(size=18),
            ),
            xaxis=dict(title='Metrics', tickangle=-45),
            yaxis_title='Values',
            barmode='group',
            height=500,
            margin=dict(l=60, r=60, t=80, b=80),
        )
        return figure
