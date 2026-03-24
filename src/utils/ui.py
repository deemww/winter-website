'''
Streamlit UI component functions for the Amazon Deforestation app.
'''

import numpy as np
import pandas as pd
import streamlit as st

from src.utils.config import YEARS
from src.utils.metrics import calculate_site_metrics, get_pressure_level, build_comparison_data
from src.utils.charts import make_ag_trend_chart, make_carbon_trend_chart, make_comparison_chart


def render_summary_metrics(amazon_df: pd.DataFrame, color_col: str, title: str):
    '''Render the summary metric cards above the map.'''
    st.markdown('<span class="section-label">Summary Statistics</span>', unsafe_allow_html=True)
    st.markdown(f'<p class="body-text" style="margin-bottom:1.2rem;"><strong>{title}</strong></p>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    avg = amazon_df[color_col].mean()
    min_val = amazon_df[color_col].min()
    max_val = amazon_df[color_col].max()

    with col1:
        st.markdown(f'''
        <div class="metric-card">
            <span class="metric-value">{len(amazon_df):,}</span>
            <span class="metric-label">Total Sites</span>
        </div>
        ''', unsafe_allow_html=True)

    with col2:
        avg_display = f"{avg:.2f}" if not np.isnan(avg) else "N/A"
        st.markdown(f'''
        <div class="metric-card">
            <span class="metric-value">{avg_display}</span>
            <span class="metric-label">Average</span>
        </div>
        ''', unsafe_allow_html=True)

    with col3:
        st.markdown(f'''
        <div class="metric-card">
            <span class="metric-value">{min_val:.1f} – {max_val:.1f}</span>
            <span class="metric-label">Range</span>
        </div>
        ''', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)


def render_pressure_box(pressure: dict):
    '''Render colored deforestation pressure interpretation box.'''
    text = f"**Deforestation Pressure:** \
        {pressure['level']}\n\n{pressure['description']}"
    if pressure["box_type"] == "error":
        st.error(text)
    elif pressure["box_type"] == "warning":
        st.warning(text)
    else:
        st.success(text)


def render_key_metrics(site_data: pd.Series, metrics: dict):
    '''Render the 4-column key metrics section.'''
    st.markdown('<span class="section-label">Key Metrics</span>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Productivity (θ)",
            f"{site_data['theta']:.2f}",
            delta=f"{metrics['theta_percentile']:.0f}th percentile",
        )
    with col2:
        st.metric(
            "Carbon Density (γ)",
            f"{site_data['gamma']:.0f} Mg/ha",
            delta=f"{metrics['gamma_percentile']:.0f}th percentile",
        )
    with col3:
        st.metric(
            "Deforestation Rate",
            f"{metrics['defor_rate']:.1f} ha/yr",
            delta=f"{metrics['pct_deforested']:+.1f}% of site (1995-2017)",
            delta_color="inverse",
        )
    with col4:
        carbon_lost = metrics["carbon_lost"]
        st.metric(
            "Carbon Lost",
            f"{carbon_lost / 1000:.1f}k Mg CO₂e",
            delta=f"{(carbon_lost / site_data['x_1995'] * 100):.1f}% \
                of 1995 stock",
            delta_color="inverse",
        )


def render_historical_trends(site_data: pd.Series):
    '''Render the two historical trend line charts.'''
    st.markdown('<span class="section-label">Historical Trends (1995-2017)</span>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<p class="body-text" style="font-weight:600;margin-bottom:0.3rem;">Agricultural Area Expansion</p>', unsafe_allow_html=True)
        st.caption("Shows how much land was converted to agriculture \
                   over time.")
        st.plotly_chart(make_ag_trend_chart(site_data, YEARS),
                        use_container_width=True)

    with col2:
        st.markdown('<p class="body-text" style="font-weight:600;margin-bottom:0.3rem;">Forest Carbon Stock Decline</p>', unsafe_allow_html=True)
        st.caption(
            "Shows how much CO₂ equivalence was released as forest was cleared.\
             CO₂ equivalence is the amount of greenhouse gas emissions \
            standardized to CO₂ emissions."
        )
        st.plotly_chart(make_carbon_trend_chart(site_data, YEARS),
                        use_container_width=True)


def render_site_comparison(site_data: pd.Series,
                           amazon_df: pd.DataFrame,
                           defor_rate: float):
    '''Render the comparison to Amazon-wide averages bar chart.'''
    st.markdown('<span class="section-label">Comparison to Other Sites</span>', unsafe_allow_html=True)
    st.caption("How this site compares to the Amazon-wide average.")
    comparison_df = build_comparison_data(site_data, amazon_df, defor_rate)
    st.plotly_chart(make_comparison_chart(comparison_df),
                    use_container_width=True)


def render_site_deep_dive(selected_site, amazon_df: pd.DataFrame):
    '''Render the full deep dive section for a selected site.'''
    st.markdown('<div class="ornamental-divider">✦ ✦ ✦</div>', unsafe_allow_html=True)

    st.markdown(f'''
    <div class="site-detail-card">
        <div class="site-detail-title">📍 Site {selected_site} Deep Dive</div>
    </div>
    ''', unsafe_allow_html=True)

    site_data = amazon_df[amazon_df['id'] == selected_site].iloc[0]
    metrics = calculate_site_metrics(site_data, amazon_df)
    pressure = get_pressure_level(metrics["ratio_percentile"],
                                  site_data,
                                  metrics)

    render_pressure_box(pressure)
    render_key_metrics(site_data, metrics)
    render_historical_trends(site_data)
    render_site_comparison(site_data, amazon_df, metrics["defor_rate"])


def render_data_table(amazon_df: pd.DataFrame, color_col: str):
    '''Render the expandable full data table.'''
    st.markdown('<span class="section-label">Data Explorer</span>', unsafe_allow_html=True)

    with st.expander("📊 View Full Data Table"):
        st.caption(
            "**id**: site id | \
            **ag_pct_1995/2008/2017**: % of site area used for agriculture \
            in that year | \
            **theta (θ)**: agricultural productivity | \
            **gamma (γ)**: average carbon density (Mg CO₂e/ha) | \
            **theta_gamma_ratio (θ/γ)**: agricultural productivity \
            per unit of carbon density"
        )
        st.dataframe(
            amazon_df[['id', 'ag_pct_1995', 'ag_pct_2008', 'ag_pct_2017',
                        'theta', 'gamma', 'theta_gamma_ratio']]
            .sort_values(color_col, ascending=False),
            use_container_width=True,
            hide_index=True,
        )