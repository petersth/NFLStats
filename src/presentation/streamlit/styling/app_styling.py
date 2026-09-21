"""Shared presentation styles for the Streamlit dashboard."""

import streamlit as st


def inject_custom_css():
    """Use theme-inherited colors and scoped styles for the season overview."""
    st.html("""
    <style>
    [data-testid="stMainBlockContainer"] {
        padding: 4.5rem clamp(1.25rem, 4vw, 3.5rem) 2rem;
        max-width: 1500px;
    }

    [data-testid="stSidebarUserContent"] {
        padding-top: 0;
    }

    .season-header {
        container-type: inline-size;
    }

    .season-team-header {
        display: flex;
        align-items: center;
        gap: 1.5rem;
        padding: 0 0 1.25rem;
        border-bottom: 1px solid rgba(128, 128, 128, 0.25);
    }

    .season-team-identity {
        display: flex;
        flex: 1;
        align-items: center;
        gap: 0.875rem;
        min-width: 0;
    }

    .season-team-logo {
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        width: 48px;
        height: 48px;
    }

    .season-team-logo img {
        display: block;
        width: 100%;
        height: 100%;
        object-fit: contain;
    }

    .season-team-monogram {
        display: grid;
        place-items: center;
        width: 100%;
        height: 100%;
        border: 1px solid rgba(128, 128, 128, 0.35);
        border-radius: 8px;
        font-size: 0.875rem;
        font-weight: 650;
        letter-spacing: 0.04em;
    }

    .season-team-name {
        min-width: 0;
    }

    .season-team-identity h2 {
        margin: 0;
        padding: 0;
        color: inherit;
        font-size: 1.625rem;
        font-weight: 650;
        line-height: 1.3;
    }

    .season-team-metadata {
        display: flex;
        flex-wrap: wrap;
        gap: 0.125rem 0.5rem;
        margin-top: 0.375rem;
        font-size: 0.8125rem;
        line-height: 1.6;
        opacity: 0.75;
    }

    .season-team-metadata span + span::before {
        content: "·";
        margin-right: 0.5rem;
    }

    .season-team-ratings {
        display: flex;
        flex-shrink: 0;
        gap: 1.5rem;
    }

    .season-rating-label {
        font-size: 0.8125rem;
        opacity: 0.85;
        white-space: nowrap;
    }

    .season-rating-value {
        margin-top: 0.25rem;
        font-size: 1.5rem;
        font-weight: 650;
        line-height: 1.3;
        font-variant-numeric: tabular-nums;
    }

    .season-overview {
        container-type: inline-size;
        margin: 0.25rem 0 0.75rem;
    }

    .season-overview-heading {
        margin-bottom: 0.75rem;
        font-size: 0.875rem;
        font-weight: 600;
    }

    .season-metrics {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 1.5rem;
    }

    .season-metric-group {
        min-width: 0;
    }

    .season-metric-group h3 {
        margin: 0 0 0.75rem;
        padding: 0 0 0.5rem;
        font-size: 0.875rem;
        font-weight: 600;
        line-height: 1.4;
        border-bottom: 1px solid rgba(128, 128, 128, 0.25);
    }

    .season-metric + .season-metric {
        margin-top: 0.875rem;
    }

    .season-metric-label {
        font-size: 0.8125rem;
        line-height: 1.5;
        opacity: 0.85;
    }

    .season-metric-reading {
        display: flex;
        align-items: baseline;
        flex-wrap: wrap;
        gap: 0.25rem 0.625rem;
        font-variant-numeric: tabular-nums;
    }

    .season-metric-value {
        font-size: 1.5rem;
        font-weight: 650;
        line-height: 1.3;
    }

    .season-metric-rank {
        font-size: 0.75rem;
        white-space: nowrap;
        opacity: 0.7;
    }

    .game-log-heading {
        display: flex;
        flex-wrap: wrap;
        align-items: baseline;
        justify-content: flex-start;
        gap: 0.25rem 1rem;
        margin: 0.5rem 0 0.25rem;
    }

    .game-log-heading h3 {
        margin: 0;
        padding: 0;
        font-size: 1.25rem;
        line-height: 1.4;
    }

    .game-log-heading span {
        font-size: 0.8125rem;
        opacity: 0.7;
    }

    @container (max-width: 760px) {
        .season-team-header {
            flex-direction: column;
            align-items: stretch;
            gap: 1rem;
        }
        .season-team-ratings {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .season-metrics {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }

    @container (max-width: 380px) {
        .season-metrics {
            grid-template-columns: minmax(0, 1fr);
            gap: 1.25rem;
        }
        .season-metric {
            display: flex;
            flex-wrap: wrap;
            align-items: baseline;
            justify-content: space-between;
            gap: 0.125rem 0.75rem;
        }
        .season-metric-reading {
            margin-left: auto;
        }
        .season-metric-value {
            font-size: 1.25rem;
        }
    }

    @container (max-width: 380px) {
        .season-team-identity {
            gap: 0.75rem;
        }
        .season-team-identity h2 {
            font-size: 1.375rem;
        }
        .season-rating-value {
            font-size: 1.25rem;
        }
    }
    </style>
    """)
