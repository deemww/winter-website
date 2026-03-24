# 2026-winter-bfi

## Project Background

The Becker Friedman Institute for Economics (BFI) serves as a hub for cutting-edge analysis and research across the entire University of Chicago economics community. Inspired by Nobel Laureates Gary Becker and Milton Friedman, BFI works to turn evidence-based research into real-world impact by translating rigorous analysis into accessible formats for key decision-makers around the world.

This project extends the BFI working paper "Carbon Prices, Forest Conservation, and Reforestation in the Brazilian Amazon" (Assunção, Hansen, Munson, Scheinkman, 2023). We have developed an interactive Streamlit dashboard that enables users to explore historical deforestation patterns, economic drivers, and future optimization projections across 1,043 sites in the Brazilian Amazon.

By pre-computing complex quadratic programming scenarios via Gurobi and Pyomo, the dashboard visualizes how agricultural productivity (θ) and forest carbon density (γ) create varying economic incentives for land use change under different carbon pricing policies.

## Project Goals
- **Expand the BFI Working Paper:** Translate rigorous econometric and spatial data into a web-based interactive visualization platform.
- **Simulate Policy Impacts:** Enable journalists, researchers, and policymakers to explore how different carbon prices (pe) and agricultural prices (pa) affect reforestation incentives over a 50-year horizon.
- **Highlight Economic Drivers:** Show the underlying factors determining which forested areas face the greatest pressure for agricultural conversion.
- **Ensure Reproducibility:** Provide a fully containerized, reproducible environment using modern Python tooling (`uv` and Docker) that runs identically on any machine.


## Key Features
- **Interactive Map Visualizations:** MapLibre choropleth maps of 1,043 Amazon sites with toggleable historical and projected data layers.
- **Pre-Computed Projections:** Quick dashboard rendering of 50-year optimization trajectories for agricultural expansion (Z) and carbon stock (X), circumventing the need for commercial solver licenses.
- **Site-Level Deep Dives:** Click any site to view detailed metrics, historical trends, and trajectory comparisons between baseline and active policy scenarios.
- **Economic Context:** Automatic calculation of deforestation pressure levels and percentile rankings based on the θ/γ ratio.

## Getting Started
#### Prerequisites:
Install and run [Docker](https://docs.docker.com/get-docker/), a clean, lightweight containerization app.

#### 1. Clone the Repository
```bash
git clone https://github.com/dsi-clinic/2026-winter-bfi.git
cd 2026-winter-bfi
```

#### 2. Set Up Data Directory

Ensure your data files are in the correct location:
```
2026-winter-bfi/
├── data/
│   ├── grid_1043_sites.geojson
│   ├── calibration_1043_sites.csv
│   ├── theta_fit_1043.geojson
│   └── gamma_fit_1043.geojson
├── output/
│   └── optimization/
│       └── 1043_sites/
│           └── pa_44.75/
│               ├── pe_6.6
│               ├── pe_16.6
│               ├── pe_21.6
│               ├── pe_26.6
│               └── pe_31.6
```

#### 4. Run the Dashboard with Make
_Make_ automates the building process, allowing you to build, run, and clean the Docker files with one command.

To build and run the app:
```bash
Make build-run
```

To build only:
```bash
Make build
```

To run only:
```bash
Make run
```

To stop and remove the running container:
```bash
Make clean
```

To completely remove the image to free up space:
```bash
Make deep-clean
```

The dashboard will be accessible at **http://localhost:8501** in your browser.

#### 5. Closing and cleaning the App

Press `Ctrl + C` in your terminal will terminate the Streamlit server.

Run
```bash
Make clean
```
to remove the container for housekeeping.

## Project Structure
```
2026-winter-bfi/
├── data/                                   # Data storage
│   ├── grid_1043_sites.geojson           # Site boundary polygons (EPSG:5880)
│   ├── calibration_1043_sites.csv        # Historical land use and economic parameters
│   ├── theta_fit_1043.geojson            # Agricultural productivity (optional)
│   └── gamma_fit_1043.geojson            # Forest carbon density (optional)
├── app.py                                 # Main Streamlit application
├── data_loader.py                         # Data loading and preprocessing
├── requirements.txt                       # Python dependencies
└── README.md                              # This file
```

## Data

### Dataset Overview

**Primary Files:**
- `grid_1043_sites.geojson`: Site boundaries across Brazilian Amazon
- `calibration_1043_sites.csv`: Comprehensive historical and economic data

**Coverage:**
- **1,043 sites** across the Brazilian Amazon biome
- **Time Period**: 1995, 2008, 2017 (three snapshots)
- **Variables**: 40+ socioeconomic and environmental indicators

### Key Variables

**Land Use (hectares):**
- `z_1995`, `z_2008`, `z_2017` — Agricultural area
- `area_forest_1995`, `area_forest_2008`, `area_forest_2017` — Forest area
- `zbar_2017` — Total available land in Amazon biome

**Carbon Stocks (Mg CO₂e):**
- `x_1995`, `x_2008`, `x_2017` — Carbon stored in forests

**Economic Parameters (Calibrated):**
- `theta` — Agricultural productivity
- `gamma` — Forest carbon density (Mg CO₂e/ha)

**Derived Metrics (Calculated by Dashboard):**
- `ag_pct_1995`, `ag_pct_2008`, `ag_pct_2017` — Agricultural area as % of site
- `theta_gamma_ratio` — Productivity/carbon tradeoff (scaled ×1000)
- `defor_rate_08_17` — Deforestation rate (hectares/year)

### Data Dictionary

See the [original research paper](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4414217) for complete variable definitions and methodology.

## Data Access & Privacy

All data handling follows the Data Science Clinic guidelines. Data sources:
- **Primary Source**: [lphansen.github.io/Amazon](https://lphansen.github.io/Amazon)
- **Calibration Data**: Dropbox folder provided by research team
- **Original Paper**: Assunção, Hansen, Munson, Scheinkman (2023)

## Technical Details

### Coordinate Reference System (CRS)

**Important**: The `grid_1043_sites.geojson` file has **incorrect CRS metadata**. The file claims to be in EPSG:4326 (WGS84 lat/lon), but coordinates are actually in **EPSG:5880 (SIRGAS 2000 / Brazil Polyconic)**.

The `data_loader.py` script automatically corrects this:
```python
sites = gpd.read_file("data/grid_1043_sites.geojson")
sites = sites.set_crs('EPSG:5880', allow_override=True)  # Override incorrect metadata
sites = sites.to_crs('EPSG:4326')  # Convert to web mapping standard
```

### Data Processing Pipeline
```
1. Load GeoJSON (fix CRS: EPSG:5880 → EPSG:4326)
2. Load calibration CSV
3. Merge on site 'id'
4. Calculate derived metrics (ag percentages, θ/γ ratio, deforestation rates)
5. Cache with Streamlit @st.cache_data
6. Serve to interactive dashboard
```

## Troubleshooting

### Map Shows No Colors

**Issue**: Streamlit cache is holding old data after code changes.

**Solution**:
```bash
# In terminal while app is running, press 'C' then 'Enter' to clear cache
# Or restart the app with Ctrl+C then:
streamlit run app.py --server.runOnSave true
```

### Coordinate System Errors

**Issue**: `ValueError: Cannot transform naive geometries` or coordinates in millions.

**Solution**: Ensure `data_loader.py` is setting CRS correctly:
```python
sites = sites.set_crs('EPSG:5880', allow_override=True)
```

### Missing Dependencies

**Issue**: `ModuleNotFoundError` for geopandas, plotly, etc.

**Solution**:
```bash
pip install streamlit geopandas plotly pandas numpy shapely pyproj
```

### Slow Performance

**Issue**: App takes a long time to load or respond.

**Solution**:
- Ensure `@st.cache_data` decorator is on `load_amazon_data()` function
- Check that you're not recalculating centroids on every interaction
- Consider reducing number of sites displayed (filter by region)

## References

### Key Documents

- **BFI Working Paper**: [Carbon Prices, Forest Conservation and Reforestation in the Brazilian Amazon](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4414217)
- **Online Notebook**: [lphansen.github.io/Amazon](https://lphansen.github.io/Amazon/solution/det.html)
- **Data Source**: Dropbox calibration folder (access via project team)

### External Resources

- [Streamlit Documentation](https://docs.streamlit.io)
- [GeoPandas Guide](https://geopandas.org/en/stable/)
- [Plotly Python](https://plotly.com/python/)

### Supplementary Data Sources

- [MapBiomas Brazil](https://mapbiomas.org/) — Historical land use data
- [SEEG Brazil](https://seeg.eco.br/) — Greenhouse gas emissions data
- SIRGAS 2000 Coordinate Reference System

## Project Team

**Data Science Clinic** - University of Chicago
Collaboration with the Becker Friedman Institute for Economics

**Student Contributors:**
- Isabella Trainor
- Cynthia Zeng
- Ryan Lee
- Nandi Xu

**TA:**
- Jack Luo

**Mentor:**
- Arna Woemmel

**External BFI Mentors:**
- Abigail Hiller
- Eric Hernandez


---

**Last Updated**: March 10, 2026
