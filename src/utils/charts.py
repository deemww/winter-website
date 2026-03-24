'''
Plotly chart functions for the Amazon Deforestation app.
'''

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from src.utils.config import MAP_STYLE, MAP_ZOOM, MAP_HEIGHT


def make_map(amazon_df: pd.DataFrame,
             color_col: str,
             color_scale: str,
             title: str) -> go.Figure:
    '''Create the main scatter mapbox figure.'''
    fig = px.scatter_map(
        amazon_df,
        lat='lat',
        lon='lon',
        color=color_col,
        size=amazon_df['z_2017'] / 1000,
        color_continuous_scale=color_scale,
        hover_data={
            'id': True,
            color_col: ':.2f',
            'lat': False,
            'lon': False,
        },
        map_style=MAP_STYLE,
        zoom=MAP_ZOOM,
        height=MAP_HEIGHT,
        title=title,
    )
    fig.update_layout(
        mapbox_style=MAP_STYLE,
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
    )
    return fig


def make_ag_trend_chart(site_data: pd.Series, years: list) -> go.Figure:
    '''Create agricultural area expansion bar chart.'''
    ag_values = [site_data['z_1995'], site_data['z_2008'], site_data['z_2017']]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[str(y) for y in years],
        y=ag_values,
        marker_color='#1f77b4',
        hovertemplate='Year: %{x}<br>Area: %{y:.0f} ha<extra></extra>',
    ))
    fig.update_layout(
        height=300,
        margin=dict(l=100, t=30, r=30, b=60),
        xaxis=dict(
            type='category',
            categoryorder='array',
            categoryarray=[str(y) for y in years],
        ),
        xaxis_title="Year",
        yaxis_title="Agricultural Area (hectares)",
        showlegend=False,
    )
    return fig


def make_carbon_trend_chart(site_data: pd.Series, years: list) -> go.Figure:
    '''Create forest carbon stock bar chart.'''
    x_values = [site_data['x_1995'], site_data['x_2008'], site_data['x_2017']]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[str(y) for y in years],
        y=x_values,
        marker_color='#1f77b4',
        hovertemplate='Year: %{x}<br>Stock: %{y:.0f} Mg CO₂e<extra></extra>',
    ))
    fig.update_layout(
        height=300,
        margin=dict(l=100, t=30, r=30, b=60),
        xaxis=dict(
            type='category',
            categoryorder='array',
            categoryarray=[str(y) for y in years],
        ),
        xaxis_title="Year",
        yaxis_title="Carbon Stock (Mg CO₂e)",
        showlegend=False,
    )
    return fig


def make_comparison_chart(comparison_df: pd.DataFrame) -> go.Figure:
    '''Create grouped bar chart comparing site to Amazon average.'''
    fig = go.Figure(data=[
        go.Bar(
            name='This Site',
            x=comparison_df['Metric'],
            y=comparison_df['This Site_norm'],
            marker_color='#1f77b4',
        ),
        go.Bar(
            name='Amazon Average',
            x=comparison_df['Metric'],
            y=comparison_df['Amazon Average_norm'],
            marker_color='#ff7f0e',
        ),
    ])
    fig.update_layout(
        barmode='group',
        height=300,
        yaxis_title="Normalized Value (0-1)",
        showlegend=True,
        legend=dict(orientation="h",
                    yanchor="top",
                    y=-0.2,
                    xanchor="center",
                    x=0.5),
    )
    return fig