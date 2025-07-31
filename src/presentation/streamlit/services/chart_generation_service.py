# src/presentation/streamlit/services/chart_generation_service.py - Chart generation service

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import List, Dict, Any
from ....application import TeamAnalysisResponse
from ....domain import GameStats


class ChartGenerationService:
    """Service for generating interactive charts."""
    
    def __init__(self):
        # Get Streamlit theme colors - these might not work directly
        # Use Plotly's template system instead for better theme integration
        self.use_dark_theme = st.get_option('theme.base') == 'dark'
        
        if self.use_dark_theme:
            self.plot_template = "plotly_dark"
            self.primary_color = '#1f77b4'
            self.background_color = '#0e1117'
            self.secondary_bg_color = '#262730'
            self.text_color = '#fafafa'
        else:
            self.plot_template = "plotly_white"
            self.primary_color = st.get_option('theme.primaryColor') or '#1f77b4'
            self.background_color = '#ffffff'
            self.secondary_bg_color = '#f0f2f6'
            self.text_color = '#262730'
        
    def create_metric_trend_chart(self, metric_name: str, metric_display: str, values: List[float], unit: str = "", y_range: List[float] = None) -> go.Figure:
        """Create a trend chart for a single metric."""
        games = list(range(1, len(values) + 1))
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=games,
            y=values,
            mode='lines+markers',
            name=metric_display,
            line=dict(color=self.primary_color, width=3),
            marker=dict(size=8),
            hovertemplate=f'<b>{metric_display}</b><br>Game: %{{x}}<br>Value: %{{y:.2f}}{unit}<extra></extra>'
        ))
        
        avg_value = sum(values) / len(values) if values else 0
        fig.add_hline(
            y=avg_value, 
            line_dash="dash", 
            line_color="gray",
            annotation_text=f"Avg: {avg_value:.2f}{unit}",
            annotation_position="right"
        )
        
        fig.update_layout(
            template=self.plot_template,
            title=dict(
                text=f"<b>{metric_display}</b>",
                x=0,
                xanchor='left',
                font=dict(size=16)
            ),
            xaxis=dict(
                title="Game",
                showgrid=True,
                tickmode='linear',
                tick0=1,
                dtick=2 if len(games) > 10 else 1
            ),
            yaxis=dict(
                title=f"{metric_display}{unit}",
                showgrid=True,
                range=y_range if y_range else None
            ),
            showlegend=False,
            height=300,
            margin=dict(l=50, r=50, t=50, b=50)
        )
        
        return fig
    
    def create_metric_distribution_chart(self, metric_name: str, metric_display: str, values: List[float], unit: str = "", y_range: List[float] = None) -> go.Figure:
        """Create a compact distribution chart for a single metric."""
        fig = go.Figure()
        
        # Add horizontal histogram for better range alignment
        fig.add_trace(go.Histogram(
            y=values,
            orientation='h',
            marker_color=self.primary_color,
            opacity=0.7,
            showlegend=False,
            nbinsy=min(10, len(values))  # Limit bins for small datasets
        ))
        
        fig.update_layout(
            template=self.plot_template,
            yaxis=dict(
                showgrid=True,
                showticklabels=False,  # Hide labels to save space
                range=y_range if y_range else [0, 1]
            ),
            xaxis=dict(
                showticklabels=False,
                showgrid=False
            ),
            showlegend=False,
            height=300,
            margin=dict(l=5, r=5, t=5, b=5)  # Minimal margins
        )
        
        return fig
    
    def create_trends_chart(self, analysis_response: TeamAnalysisResponse) -> go.Figure:
        """Create a comprehensive trends chart for all offensive metrics."""
        if not analysis_response.game_stats:
            return self._create_empty_chart("No game data available")
        
        # Prepare data
        games = list(range(1, len(analysis_response.game_stats) + 1))
        
        fig = go.Figure()
        
        colors = px.colors.qualitative.Plotly
        metrics_config = [
            ('yards_per_play', 'Avg Yards/Play', colors[0], 'solid'),
            ('success_rate', 'Success Rate %', colors[1], 'solid'),
            ('points_per_drive', 'Points/Drive', colors[2], 'solid'),
            ('completion_pct', 'Completion %', colors[3], 'solid'),
            ('third_down_pct', '3rd Down %', colors[4], 'solid')
        ]
        
        for attr, name, color, line_style in metrics_config:
            values = [getattr(game_stat, attr) for game_stat in analysis_response.game_stats]
            
            fig.add_trace(go.Scatter(
                x=games,
                y=values,
                mode='lines+markers',
                name=name,
                line=dict(color=color, dash=line_style, width=2),
                marker=dict(size=6),
                hovertemplate=f'<b>{name}</b><br>Game: %{{x}}<br>Value: %{{y:.2f}}<extra></extra>'
            ))
        
        # Style the chart with theme colors
        fig.update_layout(
            template=self.plot_template,
            title=dict(
                text=f"{analysis_response.team.name} - Season Trends",
                x=0.5,
                xanchor='center',
                font=dict(size=18)
            ),
            xaxis=dict(
                title="Game Number",
                showgrid=True,
                tickmode='linear',
                tick0=1,
                dtick=1
            ),
            yaxis=dict(
                title="Metric Value",
                showgrid=True
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            hovermode='x unified',
            height=500,
            margin=dict(l=60, r=60, t=80, b=60)
        )
        
        return fig
    
    def create_performance_distribution_chart(self, analysis_response: TeamAnalysisResponse) -> go.Figure:
        """Create a distribution chart showing performance consistency."""
        if not analysis_response.game_stats:
            return self._create_empty_chart("No game data available")
        
        # Create box plots for key metrics
        metrics_data = {
            'Avg Yards/Play': [game.yards_per_play for game in analysis_response.game_stats],
            'Success Rate': [game.success_rate for game in analysis_response.game_stats],
            'Points/Drive': [game.points_per_drive for game in analysis_response.game_stats],
            'Completion %': [game.completion_pct for game in analysis_response.game_stats]
        }
        
        fig = go.Figure()
        
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
        
        for i, (metric, values) in enumerate(metrics_data.items()):
            fig.add_trace(go.Box(
                y=values,
                name=metric,
                boxpoints='all',
                jitter=0.3,
                pointpos=-1.8,
                marker_color=colors[i],
                line_color=colors[i]
            ))
        
        fig.update_layout(
            template=self.plot_template,
            title=dict(
                text=f"{analysis_response.team.name} - Performance Distribution",
                x=0.5,
                xanchor='center',
                font=dict(size=18)
            ),
            yaxis_title="Metric Values",
            showlegend=False,
            height=400,
            margin=dict(l=60, r=60, t=80, b=60)
        )
        
        return fig
    
    def create_opponent_difficulty_chart(self, analysis_response: TeamAnalysisResponse) -> go.Figure:
        """Create a chart showing performance vs opponent strength."""
        if not analysis_response.game_stats:
            return self._create_empty_chart("No game data available")
        
        # For now, create a simple scatter plot
        # In a real implementation, you'd factor in opponent defensive rankings
        
        games = list(range(1, len(analysis_response.game_stats) + 1))
        yards_per_play = [game.yards_per_play for game in analysis_response.game_stats]
        success_rates = [game.success_rate for game in analysis_response.game_stats]
        opponents = [game.opponent.abbreviation for game in analysis_response.game_stats]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=yards_per_play,
            y=success_rates,
            mode='markers+text',
            text=opponents,
            textposition="top center",
            marker=dict(
                size=12,
                color=games,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="Game Number")
            ),
            hovertemplate='<b>vs %{text}</b><br>Avg Yards/Play: %{x:.2f}<br>Success Rate: %{y:.2f}%<extra></extra>'
        ))
        
        fig.update_layout(
            template=self.plot_template,
            title=dict(
                text=f"{analysis_response.team.name} - Performance vs Opponents",
                x=0.5,
                xanchor='center',
                font=dict(size=18)
            ),
            xaxis_title="Yards per Play",
            yaxis_title="Success Rate (%)",
            height=500,
            margin=dict(l=60, r=60, t=80, b=60)
        )
        
        return fig
    
    def create_ranking_comparison_chart(self, analysis_response: TeamAnalysisResponse) -> go.Figure:
        """Create a radar chart for league ranking comparison."""
        if not analysis_response.rankings:
            return self._create_empty_chart("No ranking data available")
        
        # Extract rankings for radar chart
        categories = []
        values = []
        
        ranking_metrics = [
            ('avg_yards_per_play', 'Avg Yards/Play'),
            ('success_rate', 'Success Rate'),
            ('points_per_drive', 'Points/Drive'),
            ('completion_pct', 'Completion %'),
            ('third_down_pct', '3rd Down %'),
            ('redzone_td_pct', 'Red Zone TD%')
        ]
        
        for metric_key, display_name in ranking_metrics:
            if metric_key in analysis_response.rankings:
                rank = analysis_response.rankings[metric_key].rank
                # Convert rank to percentile (lower rank = higher percentile)
                percentile = ((32 - rank) / 32) * 100
                categories.append(display_name)
                values.append(percentile)
        
        if not categories:
            return self._create_empty_chart("No ranking data available")
        
        # Close the radar chart
        categories.append(categories[0])
        values.append(values[0])
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name=analysis_response.team.name,
            line_color='#1f77b4',
            fillcolor='rgba(31, 119, 180, 0.3)'
        ))
        
        fig.update_layout(
            template=self.plot_template,
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    ticksuffix='%'
                )
            ),
            title=dict(
                text=f"{analysis_response.team.name} - League Ranking Percentiles",
                x=0.5,
                xanchor='center',
                font=dict(size=18)
            ),
            showlegend=False,
            height=500,
            margin=dict(l=60, r=60, t=80, b=60)
        )
        
        return fig
    
    def _create_empty_chart(self, message: str) -> go.Figure:
        """Create an empty chart with a message."""
        fig = go.Figure()
        
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            xanchor='center', yanchor='middle',
            font=dict(size=16, color=self.text_color)
        )
        
        fig.update_layout(
            template=self.plot_template,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            height=400
        )
        
        return fig