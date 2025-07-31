# src/presentation/streamlit/styling/app_styling.py - Application styling

import streamlit as st
from typing import List


def inject_custom_css():
    """Inject custom CSS for improved styling and UX."""
    st.markdown("""
    <style>
    
    /* Sticky header container */
    .sticky-header {
        position: sticky;
        top: 0;
        background: white;
        z-index: 999;
        padding: 10px 0;
        border-bottom: 1px solid #e0e0e0;
        margin-bottom: 20px;
    }
    
    /* Team header styling */
    .team-header {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
        color: white;
        font-weight: bold;
    }
    
    /* metric cards */
    .metric-card {
        background: white;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 10px;
    }

    
    /* Progress indicator styling */
    .progress-step {
        display: flex;
        align-items: center;
        padding: 10px;
        margin: 5px 0;
        border-radius: 5px;
        background: #f8f9fa;
    }
    
    .progress-step.active {
        background: #e3f2fd;
        color: #1976d2;
    }
    
    .progress-step.complete {
        background: #e8f5e8;
        color: #2e7d32;
    }
    
    
    /* sidebar */
    .sidebar-team-info {
        background: linear-gradient(135deg, var(--team-primary, #1f77b4), var(--team-secondary, #ff7f0e));
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
        text-align: center;
    }
    
    /* Loading states */
    .loading-container {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        padding: 20px;
    }
    
    /* Performance indicators */
    .perf-excellent { color: #2e7d32; font-weight: bold; }
    .perf-good { color: #388e3c; font-weight: bold; }
    .perf-average { color: #f57c00; font-weight: bold; }
    .perf-poor { color: #d32f2f; font-weight: bold; }
    
    </style>
    """, unsafe_allow_html=True)


def inject_team_colors(colors: List[str]):
    """Inject team-specific color variables into CSS."""
    primary_color = colors[0] if colors else '#1f77b4'
    secondary_color = colors[1] if len(colors) > 1 else primary_color
    tertiary_color = colors[2] if len(colors) > 2 else secondary_color
    
    st.markdown(f"""
    <style>
    :root {{
        --team-primary: {primary_color};
        --team-secondary: {secondary_color};
        --team-tertiary: {tertiary_color};
    }}
    
    /* Update team header with dynamic colors */
    .team-header-dynamic {{
        background: linear-gradient(135deg, var(--team-primary), var(--team-secondary)) !important;
        color: white;
        padding: 15px;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    
    /* Sidebar team info with dynamic colors */
    .sidebar-team-dynamic {{
        background: linear-gradient(135deg, var(--team-primary), var(--team-secondary)) !important;
        color: white;
        text-align: center;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }}
    </style>
    """, unsafe_allow_html=True)