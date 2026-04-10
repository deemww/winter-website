"""
Homepage for the Amazon Land Allocation Dashboard.
Streamlit treats this as the default landing page.
"""

import streamlit as st
from pathlib import Path

# Import your data loader from the app_utilities package
from src.utils.data_loader import load_amazon_data

# ── Page Configuration (Merged) ───────────────────────────────────────────────
st.set_page_config(
    page_title="Amazon Land Allocation Dashboard",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Styles ────────────────────────────────────────────────────────────────────
css = Path("src/utils/styles.css").read_text()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
DATA_SOURCES = [
    ("📍", "Site boundary coordinates"),
    ("🗂️", "Historical land use measurements"),
    ("🐄", "Agricultural productivity parameters"),
    ("🌿", "Forest carbon density parameters"),
]

RESEARCH_QUESTIONS = [
    ("Land Allocation",
     "How should land be optimally allocated across the Amazon biome between "
     "cattle ranching and forest preservation over time?"),
    ("Carbon Policy",
     "How do different levels of international carbon transfer payments affect "
     "deforestation and reforestation decisions?"),
    ("Productivity Uncertainty",
     "How does uncertainty in site-specific agricultural and carbon absorption "
     "productivities affect the planner's optimal decisions?"),
    ("Price Dynamics",
     "How does stochastic variation in cattle prices influence the trade-off "
     "between agricultural and forest land use?"),
]

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-wrapper">
    <div class="eyebrow">Working Paper · Brazilian Amazon</div>
    <div class="hero-title">Carbon Prices & Amazon Conservation</div>
    <div class="hero-subtitle">A Robust Land-Allocation Analysis Framework</div>
    <div class="hero-meta">Geospatial Analysis &nbsp;·&nbsp; 1,043 Sites &nbsp;·&nbsp; 1995 – 2017</div>
</div>
""", unsafe_allow_html=True)

col_cta, col_proj = st.columns([3, 3])
with col_cta:
    if st.button("🗺️ Interactive Historical Data Dashboard", width="stretch"):
        st.switch_page("pages/Historical.py")
with col_proj:
    if st.button("🗺️ Interactive Future Projections Dashboard", width="stretch"):
        st.switch_page("pages/Projections.py")

st.link_button("Read the paper here!", "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4414217", type="primary", width="stretch")

# ── Two-column body ───────────────────────────────────────────────────────────
col_left, _, col_right = st.columns([5.5, 0.2, 3.5])

with col_left:
    st.markdown('<span class="section-label">Paper Background</span>', unsafe_allow_html=True)
    st.markdown("""
<p class="body-text">The Brazilian Amazon faces a fundamental tension between two competing
uses of land: cattle ranching generates agricultural income but releases carbon through
deforestation, while forest preservation captures carbon but foregoes that income.</p>
<div class="pull-quote"><p>The productivity driving this trade-off — how much carbon a site
can absorb and how much agricultural value it can generate — are not directly observable
and must be estimated from geographic and census data.</p></div>
<p class="body-text">This introduces uncertainty into the problem, compounded further by
cattle prices that fluctuate over time. The paper develops methods to incorporate both
forms of uncertainty directly into the optimization, allowing the planner to make robust
land-allocation decisions that account for the possibility that estimated productivities
may be wrong.</p>
""", unsafe_allow_html=True)

    st.markdown('<div class="ornamental-divider">✦ ✦ ✦</div>', unsafe_allow_html=True)
    st.markdown('<span class="section-label">Data Sources</span>', unsafe_allow_html=True)

    for icon, label in DATA_SOURCES:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:0.7rem;padding:0.4rem 0;'
            f'border-bottom:1px dashed #c8bfa8;font-size:0.88rem;color:#2a2a1e;'
            f'font-family:\'Source Serif 4\',serif;"><span style="font-size:1.1rem;">'
            f'{icon}</span><span>{label}</span></div>',
            unsafe_allow_html=True,
        )

with col_right:
    st.markdown('<span class="section-label">Dashboard Purpose</span>', unsafe_allow_html=True)
    st.markdown("""
<p class="body-text">The working paper utilizes geospatial data covering <strong>1,043
sites</strong> across the Brazilian Amazon biome, drawing on observations from
<strong>1995, 2008, and 2017</strong> and integrating four key data sources. Each site
contains roughly 40 variables capturing forest carbon density, land allocation, and
calibrated productivity parameters for both cattle farming and carbon absorption.</p>
<p class="body-text">The dashboard serves as an interactive companion to the paper, allowing users to explore
the underlying data, understand the core research questions, and visualize the trade-offs
in the use of Amazonian land faced by policymakers. It provides both a high-level overview of the data
and detailed deep-dives into specific sites, enabling users to engage with the material in a hands-on way.</p>
<p class="body-text">The dashboard is split into two main sections: the Historical Data Dashboard,
which allows users to explore the raw data and understand the baseline conditions across
the Amazon biome; and the Projections Dashboard, which visualizes the authors' model results
on land allocation under different carbon pricing levels.</p>
""", unsafe_allow_html=True)

# ── Live Data Integration (From Homepage.py) ──────────────────────────────────
st.markdown('<div class="ornamental-divider">✦ ✦ ✦</div>', unsafe_allow_html=True)
st.markdown('<span class="section-label">Live Baseline Data</span>', unsafe_allow_html=True)

with st.spinner("Loading geographical and calibration data..."):
    try:
        # Load the data using your custom loader
        map_data = load_amazon_data()

        # Display high-level metrics right below the loading spinner
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Sites Loaded", len(map_data))
        m2.metric("Total Capacity (zbar_2017)", f"{map_data['zbar_2017'].sum() / 1e6:.2f} M ha")
        m3.metric("Avg Deforestation Rate ('08-'17)", f"{map_data['defor_rate_08_17'].mean():.4f}")

        # Expandable dataframe preview
        with st.expander("View Raw Data Preview"):
            st.dataframe(map_data.drop(columns=['geometry']).head(50), width="stretch")

    except Exception as e:
        st.error(f"An error occurred while loading the data: {e}")

# ── Research questions ────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<span class="section-label">Core Research Questions</span>', unsafe_allow_html=True)

q_cols = st.columns(2)
for i, (tag, text) in enumerate(RESEARCH_QUESTIONS):
    with q_cols[i % 2]:
        st.markdown(
            f'<div class="question-block"><div class="question-tag">{tag}</div>'
            f'<div class="question-text">{text}</div></div>',
            unsafe_allow_html=True,
        )

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer-strip">
    Brazilian Amazon Biome &nbsp;·&nbsp; Geospatial Optimization under Uncertainty
    &nbsp;·&nbsp; Data: 1995 · 2008 · 2017
</div>""", unsafe_allow_html=True)
