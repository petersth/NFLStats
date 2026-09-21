"""Scoped, theme-aware presentation for the NFL dashboard."""

import streamlit as st


def inject_custom_css():
    """Put the rating first, with consistent, explorable inputs underneath."""
    st.html("""
    <style>
    [data-testid="stMainBlockContainer"] {
        /* Streamlit's 60px header overlays the page; keep controls below it. */
        padding: 4.25rem clamp(1rem, 3vw, 3rem) 2rem;
        max-width: 1720px;
    }
    .app-wordmark { font-size: 1.1rem; font-weight: 800; letter-spacing: -0.045em; }
    .app-wordmark span { font-weight: 400; margin-left: 0.18em; opacity: 0.6; }
    .st-key-analysis_filters { margin-bottom: 0.25rem; }
    .st-key-analysis_filters > [data-testid="stLayoutWrapper"]:has(> .st-key-filter_settings) {
        margin-left: auto;
    }
    .st-key-analysis_filters [data-testid="stPopover"] button {
        min-height: 2.5rem;
        font-size: 0.8125rem;
    }
    .season-header, .season-overview { container-type: inline-size; }
    .season-team-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1.5rem;
        position: relative;
        isolation: isolate;
        overflow: hidden;
        padding: 1rem 1.5rem;
        border-radius: 16px;
        color: #fff;
        background: linear-gradient(115deg, var(--team-surface) 0%, var(--team-deep) 100%);
    }
    .season-team-header::before {
        content: "";
        position: absolute;
        inset: 0;
        z-index: -1;
        pointer-events: none;
        background: linear-gradient(118deg, transparent 48%,
            rgba(255,255,255,0.035) 48%, rgba(255,255,255,0.035) 61%,
            transparent 61%, transparent 64%, rgba(255,255,255,0.025) 64%,
            rgba(255,255,255,0.025) 78%, transparent 78%);
    }
    .season-team-topline {
        display: flex; flex: 1; align-items: center;
        min-width: 0;
    }
    .season-team-identity {
        display: flex; align-items: center; gap: 1rem; min-width: 0;
    }
    .season-team-logo {
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0; width: 76px; height: 76px;
    }
    .season-team-logo img {
        display: block; width: 100%; height: 100%; object-fit: contain;
        filter: drop-shadow(0 3px 8px rgba(0,0,0,0.2));
    }
    .season-team-monogram {
        display: grid; place-items: center; width: 100%; height: 100%;
        border: 1px solid rgba(255,255,255,0.25); border-radius: 10px;
        font-size: 1rem; font-weight: 650; letter-spacing: 0.04em;
    }
    .season-team-name { min-width: 0; }
    .season-team-identity h2 {
        margin: 0; padding: 0; color: inherit;
        font-size: clamp(1.5rem, 2cqi, 2rem); font-weight: 650;
        letter-spacing: -0.025em; line-height: 1.25;
    }
    .season-team-metadata {
        display: flex; flex-wrap: wrap; gap: 0.125rem 0.625rem;
        margin-top: 0.5rem; font-size: 0.75rem; line-height: 1.5; opacity: 0.8;
    }
    .season-team-metadata span + span::before { content: "·"; margin-right: 0.625rem; }
    .season-team-ratings {
        display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
        flex: 0 0 auto; width: 25rem; gap: 2.5rem;
        padding-left: 1.5rem; border-left: 1px solid rgba(255,255,255,0.18);
    }
    .season-rating { min-width: 0; position: relative; align-self: stretch; }
    .season-rating-secondary::before {
        content: ''; position: absolute; top: 0; bottom: 0; left: -1.25rem;
        width: 1px; background: rgba(255,255,255,0.18);
    }
    .season-rating h1, .season-rating h2 {
        font-size: 0.9375rem; font-weight: 600; line-height: 1.4;
        margin: 0 0 0.375rem; padding: 0; color: inherit; white-space: nowrap;
    }
    .season-rating [data-testid="stHeaderActionElements"] { display: none; }
    .season-rating-value {
        font-size: 3rem; font-weight: 650;
        letter-spacing: -0.055em; line-height: 1; font-variant-numeric: tabular-nums;
        white-space: nowrap;
    }
    .season-rating-direction { font-size: 0.75rem; font-weight: 400; opacity: 0.6; margin-left: 0.25rem; }
    .season-rating-context {
        display: flex; align-items: baseline; gap: 0.5rem;
        font-size: 0.75rem; line-height: 1.5; margin-top: 0.5rem; opacity: 0.8;
    }
    .season-rating-context span { white-space: nowrap; }
    .season-rating-context span + span::before { content: "·"; margin-right: 0.5rem; }
    .season-rating-context strong { font-weight: 600; }
    .season-overview {
        margin: 1rem 0 0.5rem;
        --rank-strong: color-mix(in srgb, #20b68a 76%, currentColor);
        --rank-neutral: color-mix(in srgb, #8594ac 70%, currentColor);
        --rank-weak: color-mix(in srgb, #e87962 80%, currentColor);
    }
    .season-overview-heading {
        display: flex; align-items: center; justify-content: space-between;
        flex-wrap: wrap; gap: 0.5rem 1rem; margin-bottom: 0.5rem;
    }
    .season-overview-heading h2 {
        font-size: 1.25rem; font-weight: 650; letter-spacing: -0.025em;
        margin: 0; padding: 0; line-height: 1.4;
    }
    .season-overview-legend {
        display: flex; align-items: center; flex-wrap: wrap; gap: 1rem;
        font-size: 0.75rem;
    }
    .season-overview-legend > span { display: inline-flex; align-items: center; gap: 0.4rem; }
    .rank-key { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--rank-accent); }
    .is-strong { --rank-accent: var(--rank-strong); }
    .is-neutral { --rank-accent: var(--rank-neutral); }
    .is-weak { --rank-accent: var(--rank-weak); }
    .season-metrics {
        display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.75rem; align-items: start;
    }
    .season-metric-group { min-width: 0; }
    .season-metric-group h3 {
        font-size: 0.75rem; font-weight: 600; line-height: 1.5;
        letter-spacing: 0.06em; text-transform: uppercase; opacity: 0.75;
        padding: 0 0.125rem; margin: 0 0 0.5rem;
    }
    .season-metric + .season-metric { margin-top: 0.625rem; }
    .season-metric {
        min-width: 0; overflow: hidden;
        border: 1px solid color-mix(in srgb, currentColor 12%, transparent);
        border-radius: 12px;
        background: color-mix(in srgb, currentColor 3.5%, transparent);
        box-shadow: 0 3px 14px rgba(0,0,0,0.035);
        transition: border-color 160ms ease, background 160ms ease, box-shadow 160ms ease;
    }
    .season-metric > summary { padding: 0.75rem 1rem; list-style: none; cursor: pointer; }
    .season-metric > summary::-webkit-details-marker { display: none; }
    .season-metric > summary::marker { content: ''; }
    .season-metric:hover, .season-metric[open] {
        border-color: color-mix(in srgb, var(--rank-accent) 55%, transparent);
        background: color-mix(in srgb, currentColor 5%, transparent);
        box-shadow: 0 5px 20px rgba(0,0,0,0.07);
    }
    .season-metric > summary:focus-visible {
        outline: 2px solid var(--rank-accent); outline-offset: -3px; border-radius: 12px;
    }
    .season-metric-label {
        display: flex; justify-content: space-between; align-items: center; gap: 0.5rem;
        font-size: 0.9375rem; font-weight: 550; line-height: 1.4;
    }
    .season-metric-reading {
        display: flex; align-items: center; justify-content: space-between;
        gap: 0.5rem; margin: 0.375rem 0 0.25rem; font-variant-numeric: tabular-nums;
    }
    .season-metric-value {
        font-size: 2rem; font-weight: 650; letter-spacing: -0.045em; line-height: 1.15;
    }
    .season-metric-unit { font-size: 1.25rem; font-weight: 500; opacity: 0.75; margin-left: 0.12rem; }
    .season-metric-rank { display: flex; flex-direction: column; align-items: flex-end; line-height: 1.1; }
    .season-metric-rank strong { font-size: 1.375rem; font-weight: 600; color: var(--rank-accent); }
    .season-metric-rank small { font-size: 0.6875rem; vertical-align: super; margin-left: 0.08rem; }
    .season-metric-rank > span { font-size: 0.6875rem; opacity: 0.72; margin-top: 0.15rem; }
    .season-metric-context {
        display: flex; justify-content: space-between; gap: 0.25rem;
        font-size: 0.75rem; line-height: 1.5; opacity: 0.78;
    }
    .season-metric-context strong { font-weight: 550; font-variant-numeric: tabular-nums; }
    .season-metric-context > span:last-child { white-space: nowrap; }
    .metric-chevron {
        width: 1rem; height: 1rem; opacity: 0.7;
        transition: transform 160ms ease; flex-shrink: 0;
    }
    .season-metric[open] .metric-chevron { transform: rotate(180deg); }
    .season-metric-detail {
        padding: 0 1rem 1rem; border-top: 1px solid color-mix(in srgb, currentColor 9%, transparent);
    }
    .season-metric-detail p { font-size: 0.8125rem; line-height: 1.55; opacity: 0.75; margin: 0.875rem 0; }
    .season-metric-detail h4 { font-size: 0.8125rem; font-weight: 600; padding: 0; margin: 1rem 0 0.5rem; }
    .metric-contribution {
        display: flex; align-items: center; justify-content: space-between; gap: 0.75rem;
        border-radius: 8px; padding: 0.75rem;
        background: color-mix(in srgb, currentColor 5%, transparent);
        font-variant-numeric: tabular-nums;
    }
    .metric-contribution > div > span { display: block; font-size: 0.6875rem; opacity: 0.75; }
    .metric-contribution strong { display: block; font-size: 1.5rem; font-weight: 650; line-height: 1.3; letter-spacing: -0.025em; }
    .metric-contribution strong small { display: inline-block; font-size: 0.625rem; font-weight: 400; line-height: 1.4; opacity: 0.7; letter-spacing: 0; white-space: nowrap; }
    .metric-point-range { text-align: right; font-size: 0.8125rem; white-space: nowrap; }
    .metric-point-range small { display: block; font-size: 0.625rem; opacity: 0.65; }
    .season-metric-detail .metric-contribution-note { font-size: 0.6875rem; margin: 0.5rem 0 0.75rem; }
    .season-metric-detail .metric-setting-note { font-size: 0.6875rem; }
    .metric-history-chart { width: 100%; height: 64px; overflow: visible; margin: 0.5rem 0; }
    .metric-history-chart polyline { fill: none; stroke: var(--rank-accent); stroke-width: 2; stroke-linejoin: round; }
    .metric-chart-baseline { stroke: currentColor; opacity: 0.15; }
    .metric-history-scroll { max-height: 200px; overflow: auto; }
    .season-metric-detail table { width: 100%; font-size: 0.75rem; border-collapse: collapse; font-variant-numeric: tabular-nums; }
    .season-metric-detail th, .season-metric-detail td {
        text-align: left; padding: 0.4rem 0; border: 0;
        border-bottom: 1px solid color-mix(in srgb, currentColor 8%, transparent);
    }
    .season-metric-detail th { opacity: 0.6; font-weight: 500; }
    .season-metric-detail td:last-child, .season-metric-detail th:last-child { text-align: right; }
    .metric-history-scroll td:nth-child(3), .metric-history-scroll th:nth-child(3) { text-align: right; padding-right: 0.75rem; }
    .metric-game-points { font-weight: 650; }
    .metric-scoring { margin-top: 1rem; font-size: 0.8125rem; }
    .metric-scoring > summary { cursor: pointer; font-weight: 550; }
    .metric-scoring > summary:focus-visible { outline: 2px solid currentColor; outline-offset: 4px; border-radius: 2px; }
    @container (max-width: 960px) {
        .season-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem 0.75rem; }
    }
    @container (max-width: 480px) {
        .season-metrics { grid-template-columns: minmax(0, 1fr); }
        .season-overview-legend { gap: 0.75rem; font-size: 0.6875rem; }
    }
    @media (prefers-reduced-motion: reduce) {
        .season-metric, .metric-chevron { transition: none; }
    }
    [data-testid="stTabs"] [role="tablist"] { gap: 1.5rem; }
    [data-testid="stTabs"] [role="tab"] { padding-bottom: 0.75rem; }
    [data-testid="stTabs"] [role="tab"] p { font-size: 0.8125rem; }
    .game-log-heading {
        display: flex; flex-wrap: wrap; align-items: center; gap: 0.75rem;
        margin: 0.75rem 0 0.25rem;
    }
    .game-log-heading h3 { margin: 0; padding: 0; font-size: 1rem; font-weight: 600; line-height: 1.4; }
    .game-log-heading > span {
        font-size: 0.6875rem; opacity: 0.65;
        background: rgba(128,128,128,0.1); border-radius: 5px; padding: 0.15rem 0.45rem;
    }
    .st-key-analysis_source_status { border-top: 1px solid rgba(128,128,128,0.16); padding-top: 0.5rem; }
    .st-key-analysis_source_status p { font-size: 0.6875rem; opacity: 0.7; }
    @container (max-width: 900px) {
        .season-team-header { flex-direction: column; align-items: stretch; padding: 1rem 1.25rem; gap: 1rem; }
        .season-team-ratings { width: 100%; padding-left: 0; border-left: 0; gap: 2rem; }
        .season-rating-secondary::before { left: -1rem; }
    }
    @container (max-width: 460px) {
        .season-team-header { padding: 1rem; }
        .season-team-logo { width: 56px; height: 56px; }
        .season-team-identity { gap: 0.875rem; }
        .season-team-identity h2 { font-size: 1.25rem; }
        .season-team-ratings { gap: 1.5rem; }
        .season-rating-secondary::before { left: -0.75rem; }
        .season-rating h1, .season-rating h2 { font-size: 0.8125rem; }
        .season-rating-value { font-size: clamp(1.875rem, 9cqi, 2.75rem); }
        .season-rating-context { flex-direction: column; gap: 0.125rem; font-size: 0.6875rem; }
        .season-rating-context span + span::before { content: none; }
        .season-overview-legend { margin-top: 0.25rem; }
    }
    @media (max-width: 640px) {
        .st-key-analysis_filters > [data-testid="stLayoutWrapper"]:has(> .st-key-filter_brand),
        .st-key-analysis_filters > [data-testid="stLayoutWrapper"]:has(> .st-key-filter_team),
        .st-key-analysis_filters > [data-testid="stLayoutWrapper"]:has(> .st-key-filter_settings) {
            flex: 0 0 100%; width: 100%; margin-left: 0;
        }
        .st-key-analysis_filters > [data-testid="stLayoutWrapper"]:has(> .st-key-filter_season) {
            flex: 0 0 96px; width: 96px;
        }
        .st-key-analysis_filters > [data-testid="stLayoutWrapper"]:has(> .st-key-filter_type) {
            flex: 1 1 170px; width: auto; min-width: 0;
        }
        [data-testid="stTabs"] [role="tablist"] { gap: 1rem; }
    }
    </style>
    """)
