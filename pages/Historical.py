"""
Interactive Amazon deforestation explorer.
Fully self-contained — loaded directly by Streamlit's multi-page system
or via the CTA button on the homepage using st.switch_page().
"""

import streamlit as st
from pathlib import Path

from src.utils.data_loader import load_amazon_data
from src.utils.config import LAYER_CONFIG, LAYER_NAMES
from src.utils.charts import make_map
from src.utils.ui import render_summary_metrics, render_site_deep_dive, render_data_table

st.set_page_config(
    layout="wide",
    page_title="Amazon Deforestation Dashboard",
    page_icon="🌿",
    initial_sidebar_state="expanded",
)

# ── Load shared styles ────────────────────────────────────────────────────────
css = Path("src/utils/styles.css").read_text()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# ── Back navigation ───────────────────────────────────────────────────────────
if st.button("← Back to Home", width="content"):
    st.switch_page("Home.py")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="dashboard-header">
    <div class="eyebrow">Interactive Geospatial Dashboard</div>
    <div class="dashboard-title">Amazon Deforestation: Economic Drivers (1995–2017)</div>
</div>
""", unsafe_allow_html=True)

# ── Data ──────────────────────────────────────────────────────────────────────
amazon_df = load_amazon_data()
amazon_df["lon"] = amazon_df.geometry.centroid.x
amazon_df["lat"] = amazon_df.geometry.centroid.y

# ── Sidebar controls ──────────────────────────────────────────────────────────
st.sidebar.markdown('<h2 style="margin-bottom:1.5rem;">Map Controls</h2>', unsafe_allow_html=True)
layer = st.sidebar.radio("Layer", LAYER_NAMES)

cfg = LAYER_CONFIG[layer]
if layer == "Agricultural Area":
    year = st.sidebar.radio("Year", [1995, 2008, 2017], index=2)
    color_col = f"ag_pct_{year}"
    title = f"Agricultural Area – {year} (%)"
    color_scale = cfg["color_scale"]
else:
    color_col = cfg["color_col"]
    color_scale = cfg["color_scale"]
    title = cfg["title"]

# ── Summary metrics ───────────────────────────────────────────────────────────
render_summary_metrics(amazon_df, color_col, title)

# ── Map ───────────────────────────────────────────────────────────────────────
fig = make_map(amazon_df, color_col, color_scale, title)
selected_pts = st.plotly_chart(
    fig,
    width="stretch",
    on_select="rerun",
    selection_mode="points",
)

# ── Site deep-dive ────────────────────────────────────────────────────────────
selected_site = None
if (
    selected_pts
    and selected_pts.selection
    and selected_pts.selection.points
):
    point_idx = selected_pts.selection.points[0]["point_index"]
    selected_site = amazon_df.iloc[point_idx]["id"]

if selected_site:
    render_site_deep_dive(selected_site, amazon_df)

# ── Data table ────────────────────────────────────────────────────────────────
render_data_table(amazon_df, color_col)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer-strip">
    Brazilian Amazon Biome &nbsp;·&nbsp; Geospatial Optimization under Uncertainty
    &nbsp;·&nbsp; Data: 1995 · 2008 · 2017
</div>""", unsafe_allow_html=True)
