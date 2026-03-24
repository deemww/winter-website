import io
import zipfile

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
import streamlit as st

from src.utils.projections_loader import run_generation
from src.utils.config import PROJECT_ROOT, DROPBOX_URL
from src.utils import setup_logger

logger = setup_logger(__name__)

# --- Path and URL Setup ---
DATA_DIR = PROJECT_ROOT / "data"

def ensure_amazon_data_exists():
    '''Checks if the data directory has the required files, downloads them if not.'''
    target_file = DATA_DIR / "calibration_1043_sites.csv"

    if not target_file.exists():
        logger.info("Downloading required calibration data from Dropbox...")
        st.info("Downloading required calibration data from Dropbox. This may take a moment...")

        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            response = requests.get(DROPBOX_URL, stream=True, timeout=30)
            response.raise_for_status()  # Automatically raises HTTPError for bad responses (4xx, 5xx)

            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                zip_ref.extractall(DATA_DIR)

            logger.info("[bold green]Data successfully downloaded and extracted![/bold green]")
            st.success("Data successfully downloaded and extracted!")

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error while downloading data: {e}")
            st.error(f"Network error while downloading data from Dropbox. Please check your connection.")
            st.stop()
        except zipfile.BadZipFile:
            logger.error("Downloaded file is not a valid zip archive. The Dropbox link might be broken or expired.")
            st.error("Data extraction failed: The downloaded file was corrupted or invalid.")
            st.stop()
        except OSError as e:
            logger.error(f"File system error during data extraction: {e}")
            st.error("Failed to save data to disk. Check directory permissions.")
            st.stop()

@st.cache_data
def ensure_projection_data_exists():
    '''Checks if the projection output data exists, prompts user to run Pyomo if not.'''
    target_file = PROJECT_ROOT / "output" / "optimization" / "1043_sites" / "pa_44.75" / "pe_6.6" / "Z_trajectory.npy"

    if not target_file.exists():
        logger.info("Running Pyomo optimization model to generate `.npy` projection files...")
        st.info("Running the Pyomo optimization model to generate the required `.npy` files for the projections page. This may take a moment...")

        try:
            run_generation()
            logger.info("[bold green]Projection data successfully generated![/bold green]")
            st.success("Projection data successfully generated!")
        except Exception as e:
            logger.error(f"Pyomo optimization failed during generation: {e}")
            st.error(f"Failed to generate optimization projections. Check your solver configuration. Error: {e}")
            st.stop()

@st.cache_data
def load_amazon_data():
    '''Load and merge Amazon data'''
    # 1. Ensure the data is downloaded before trying to read it
    ensure_amazon_data_exists()
    ensure_projection_data_exists()

    # 2. Team's original loading logic
    try:
        sites = gpd.read_file(DATA_DIR / "grid_1043_sites.geojson")

        # file incorrectly claims EPSG:4326, but coordinates are actually:
        # SIRGAS 2000 / Brazil Polyconic (EPSG:5880)
        sites = sites.set_crs("EPSG:5880", allow_override=True)
        sites = sites.to_crs("EPSG:4326")

        calib = pd.read_csv(DATA_DIR / "calibration_1043_sites.csv")
        amazon_df = sites.merge(calib, on="id", how="left")

        # Data transformations
        amazon_df["ag_pct_1995"] = amazon_df["share_agricultural_use_1995"] * 100
        amazon_df["ag_pct_2008"] = amazon_df["share_agricultural_use_2008"] * 100
        amazon_df["ag_pct_2017"] = amazon_df["share_agricultural_use_2017"] * 100

        amazon_df["theta_gamma_ratio"] = np.where(
            amazon_df["gamma"] > 0,
            amazon_df["theta"] / amazon_df["gamma"],
            np.nan
        )

        amazon_df["defor_rate_08_17"] = (amazon_df["z_2017"] - amazon_df["z_2008"]) / 9

        logger.info(f"Successfully loaded and merged Amazon spatial data with {len(amazon_df)} records.")
        return gpd.GeoDataFrame(amazon_df, geometry="geometry", crs="EPSG:4326")

    except FileNotFoundError as e:
        logger.error(f"Missing expected data file during load: {e.filename}")
        st.error(f"A required data file is missing: {e.filename}. Try clearing your cache and restarting.")
        st.stop()
    except KeyError as e:
        logger.error(f"Missing expected column during data transformations: {e}")
        st.error(f"Data format error: Missing expected column {e}. The source data may have changed.")
        st.stop()
    except Exception as e:
        logger.error(f"Unexpected error loading Amazon data: {e}")
        st.error("An unexpected error occurred while loading the map data.")
        st.stop()