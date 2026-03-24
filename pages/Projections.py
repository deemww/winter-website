import streamlit as st
import numpy as np
from pathlib import Path

# Import our custom loaders from the utilities folder
from src.utils.projections_loader import (
    load_site_data,
    append_projections_to_gdf,
    make_choropleth,
    render_projection_site_deep_dive,
    generate_aggregate_trajectory_charts
)
# Import map and UI utilities
from src.utils.data_loader import load_amazon_data

# --- Page Setup ---
st.set_page_config(page_title="Projections | Amazon Model", layout="wide")

# ── Styles (Harmonized with app.py) ───────────────────────────────────────────
try:
    css = Path("src/utils/styles.css").read_text()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass # Fails gracefully if CSS isn't found

# ── Back navigation ───────────────────────────────────────────────────────────
if st.button("← Back to Home", width="content"):
    st.switch_page("Home.py")

# ── Hero Section ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-wrapper" style="padding-bottom: 2rem;">
    <div class="eyebrow">Interactive Projections</div>
    <div class="hero-title">Deforestation Trajectories</div>
    <div class="hero-subtitle">Visualizing land allocation and carbon stock across 1,043 sites under different carbon pricing scenarios.</div>
</div>
""", unsafe_allow_html=True)

# Aligning these with the defaults in your Pyomo script
selected_pa = 44.75  # Price of cattle (Pa)
base_pe = 6.6        # Base price of emissions (Pe)

b_values = [0, 10, 15, 20, 25]
colors = ['#d62728', '#2ca02c', '#1f77b4', '#9467bd', '#17becf'] # Slightly softer, professional colors

# --- Load Baseline Data ---
with st.spinner(f"Loading baseline geographical data for 1,043 sites..."):
    # Using the exact loader from projections_loader to ensure site count matches
    zbar, z_init, forest_area_init = load_site_data(year=2017)
    # Calculate the total arable capacity across all sites for percentage scaling
    zbar_total = np.sum(zbar)

    # Load base geo-dataframe for the map
    amazon_df = load_amazon_data()

# ── Introduction Text ─────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)

st.markdown('<span class="section-label">Overview</span>', unsafe_allow_html=True)
st.markdown("""
<p class="body-text">To illustrate the potential impact of carbon pricing policies,
            we reproduce the authors’ visualizations in greater detail. The
            original model and visualizations that the authors used can be found
            <a href="https://lphansen.github.io/Amazon/solution/det.html"
            target="_blank" style="color: #2ca02c; text-decoration: none;
            border-bottom: 1px dotted #2ca02c;">here</a>. The projections utilize
            the 2017-level data as a baseline, and the projections evolve according
            to the authors’ model.</p>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

st.markdown('<span class="section-label">The b-value Parameter</span>', unsafe_allow_html=True)
st.markdown("""
<p class="body-text">The important parameter <strong>b</strong>, which is a focus
            of this paper, denotes the external payment to Brazil for each ton of
            CO<sub>2</sub>e sequestered. A <em>b</em>-value of 10 indicates that
            a policy where $10 is transferred to Brazil for each ton of CO<sub>2</sub>
            sequestered is implemented.</p>
<p class="body-text">This policy promotes reforestation and forest preservation
            by assigning a positive value for conservation and correcting
            externalities of forest destruction, so determining an optimal
            <em>b</em>-value is critical. Here, we show that even a modest <em>b
            </em>-value of 10 can significantly encourage reforestation and
            forest preservation.</p>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# --- SPATIAL MAP INTEGRATION ---
# ==========================================

st.markdown('<div class="ornamental-divider">✦ ✦ ✦</div>', unsafe_allow_html=True)
st.markdown('<span class="section-label">Spatial Projections</span>', unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

st.markdown(
    "<p style='text-align: center; font-size: 0.85rem; color: #737373; font-style: italic; margin-top: -10px;'>"
    "Scroll to zoom, drag to pan, click to select, double-click to reset."
    "</p>",
    unsafe_allow_html=True
)

# 1. Declare layout containers FIRST (This dictates visual order on the page)
map_cols = st.columns(2)                   # Maps go here at the top
control_cols = st.columns(2)               # Controls go here in the middle
deep_dive_container = st.container()       # Site clicks load here

# 2. Render Controls in their designated container
with control_cols[0]:
    b_val = st.selectbox("$ Transfer for each ton of CO2 captured (b)", options=[10, 15, 20, 25], index=0)
with control_cols[1]:
    proj_year = st.slider("Projection Year", min_value=2017, max_value=2067, value=2017)

# Calculate parameters for rendering
scenario_pe = base_pe + b_val
t = proj_year - 2017
color_col = f"Z_pct_yr{t}"
color_scale = "Reds"

try:
    with st.spinner("Loading maps..."):
        # Append projection data to copies of the base GDF to prevent column overlap
        gdf_baseline = append_projections_to_gdf(amazon_df.copy(), pe=base_pe, pa=selected_pa)
        gdf_scenario = append_projections_to_gdf(amazon_df.copy(), pe=scenario_pe, pa=selected_pa)

        # Generate Map Figures
        fig_base = make_choropleth(
            gdf_baseline,
            color_col=color_col,
            title="a) No carbon payments (business as usual)",
            color_scale=color_scale
        )

        fig_scenario = make_choropleth(
            gdf_scenario,
            color_col=color_col,
            title=f"b) ${scenario_pe - 6.6:.0f} Transfer payment for every tonne of CO2",
            color_scale=color_scale
        )

        # 3. Inject Maps into the top containers
        with map_cols[0]:
            base_click = st.plotly_chart(
                fig_base,
                width='stretch',
                on_select="rerun",
                selection_mode="points",
                key="base_map"
            )

        with map_cols[1]:
            scen_click = st.plotly_chart(
                fig_scenario,
                width='stretch',
                on_select="rerun",
                selection_mode="points",
                key="scen_map"
            )

        # 4. Determine which map was clicked (if any)
        selected_site = None

        if scen_click and scen_click.selection and scen_click.selection.points:
            selected_site = scen_click.selection.points[0].get("location")
        elif base_click and base_click.selection and base_click.selection.points:
            selected_site = base_click.selection.points[0].get("location")

        # 5. Inject Site Deep Dive into its container below the controls
        if selected_site is not None:
            with deep_dive_container:
                transfer_amount = scenario_pe - 6.6
                render_projection_site_deep_dive(selected_site, gdf_baseline, gdf_scenario, transfer_amount)

except FileNotFoundError:
    st.error("Projection data not found. Please run the Pyomo solver to generate `.npy` files for these scenarios.")
except Exception as e:
    st.error(f"Error rendering map: {e}")


# ==========================================
# --- AGGREGATE LINE CHARTS ---
# ==========================================

st.markdown('<div class="ornamental-divider">✦ ✦ ✦</div>', unsafe_allow_html=True)
st.markdown('<span class="section-label">Aggregate Biome Trajectories</span>', unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# Call the helper function from our loader to generate both Plotly figures
fig_z, fig_x, data_missing = generate_aggregate_trajectory_charts(
    b_values=b_values,
    base_pe=base_pe,
    selected_pa=selected_pa,
    zbar_total=zbar_total,
    colors=colors
)

# --- Display Line Charts ---
if data_missing:
    st.warning(f"Projections for some scenarios (Sites: 1043, Pa: {selected_pa}, Base Pe: {base_pe}) are missing. Run the Pyomo solver to generate the corresponding `.npy` files.")

col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(fig_z, use_container_width=True)
with col2:
    st.plotly_chart(fig_x, use_container_width=True)