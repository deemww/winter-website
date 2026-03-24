import sys
import time
import pickle
import numpy as np
import pandas as pd
import geopandas as gpd
from scipy.sparse import csr_matrix
from cmdstanpy import CmdStanModel

from src.utils.config import PROJECT_ROOT, STAN_CODE
from src.utils import setup_logger

logger = setup_logger(__name__)

# --- Path Setup ---
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
STAN_DIR = PROJECT_ROOT / "stan_models"
stan_file = STAN_DIR / "baseline.stan"

# Ensure directories exist
try:
    STAN_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "tables").mkdir(parents=True, exist_ok=True)
except OSError as e:
    logger.error(f"Failed to create necessary directories: {e}")
    sys.exit(1)

# --- 1. Data Loading Functions ---

def load_gamma_calib(num_sites: int, type: str = "reg") -> dict:
    '''Load gamma calibration data for either regression or fit type. Returns a dictionary of relevant variables.'''
    try:
        if type == "fit":
            gdf: gpd.GeoDataFrame = gpd.read_file(DATA_DIR / f"gamma_fit_{num_sites}.geojson")
            X: np.ndarray = gdf.iloc[:, :6].to_numpy()
            return {
                "X_gamma_fit": X,
                "m_gamma_fit": gdf["id_group"].astype(int).values,
            }
        else:
            gdf: gpd.GeoDataFrame = gpd.read_file(DATA_DIR / "gamma_reg.geojson")
            X: np.ndarray = gdf.iloc[:, :6].to_numpy()
            return {
                "N_gamma": X.shape[0],
                "M_gamma": gdf["id_group"].unique().size,
                "K_gamma": X.shape[1],
                "y_gamma": gdf["log_co2e_ha_2017"].values,
                "X_gamma": X,
                "m_gamma": gdf["id_group"].astype(int).values,
            }
    except FileNotFoundError as e:
        logger.error(f"Missing gamma calibration file: {e.filename}. Did you run the data prep scripts?")
        sys.exit(1)
    except KeyError as e:
        logger.error(f"Missing expected column in gamma data: {e}. Check your GeoJSON structure.")
        sys.exit(1)

def load_theta_calib(num_sites: int, type: str = "reg"):
    '''Load theta calibration data for either regression or fit type. Returns a dictionary of relevant variables.'''
    try:
        if type == "fit":
            gdf: gpd.GeoDataFrame = gpd.read_file(DATA_DIR / f"theta_fit_{num_sites}.geojson")
            G: np.ndarray = gdf.pivot(index="id", columns="muni_id", values="muni_site_area").fillna(0).to_numpy()
            G = G / G.sum(axis=1, keepdims=True)

            gdf = gdf.sort_values("muni_id").drop_duplicates(subset="muni_id", keep="first")
            X: np.ndarray = gdf.iloc[:, :8].to_numpy()

            G_sparse = csr_matrix(G)
            return {
                "C_theta_fit": X.shape[0],
                "X_theta_fit": X,
                "m_theta_fit": gdf["group_id"].astype(int).values,
                "G_nnz_theta": len(G_sparse.data),
                "G_w_theta": G_sparse.data,
                "G_v_theta": G_sparse.indices + 1,
                "G_u_theta": G_sparse.indptr + 1,
                "pa_2017": 44.9736197781184,
            }
        else:
            gdf: gpd.GeoDataFrame = gpd.read_file(DATA_DIR / "theta_reg.geojson")
            X: np.ndarray = gdf.iloc[:, :8].to_numpy()
            W: np.ndarray = gdf["weights"].values
            W = np.sqrt(W / np.std(W))

            return {
                "N_theta": X.shape[0],
                "M_theta": gdf["group_id"].unique().size,
                "K_theta": X.shape[1],
                "y_theta": gdf["log_slaughter"].values,
                "X_theta": X,
                "m_theta": gdf["group_id"].astype(int).values,
                "W_theta": W,
            }
    except FileNotFoundError as e:
        logger.error(f"Missing theta calibration file: {e.filename}. Did you run the data prep scripts?")
        sys.exit(1)
    except KeyError as e:
        logger.error(f"Missing expected column in theta data: {e}. Check your GeoJSON structure.")
        sys.exit(1)

# --- 2. Stan Model Setup ---

def generate_calibration_data(num_sites: int = 1043): # 1043 is the default number of sites in the dataset, but can be adjusted for the 78-site version.
    '''Main function to generate calibration data by sampling from the baseline distribution using CmdStanPy. Saves results to CSV and pickled files.'''
    logger.info(f"Starting calibration build for [bold cyan]{num_sites}[/bold cyan] sites...")

    # 1. Compile Data Dictionary
    data_dict = {"num_sites": num_sites}
    data_dict.update(load_gamma_calib(num_sites, "reg"))
    data_dict.update(load_gamma_calib(num_sites, "fit"))
    data_dict.update(load_theta_calib(num_sites, "reg"))
    data_dict.update(load_theta_calib(num_sites, "fit"))

    # 2. Write and Compile Stan Model
    try:
        with open(stan_file, "w") as f:
            f.write(STAN_CODE)

        logger.info("Compiling Stan Model...")
        sampler = CmdStanModel(stan_file=stan_file, cpp_options={"STAN_THREADS": "true"}, force_compile=True)
    except Exception as e:
        logger.error(f"Failed to write or compile the Stan model. Ensure CmdStan is installed correctly. Error: {e}")
        sys.exit(1)

    # 3. Sampling
    logger.info("Sampling from baseline distribution [italic](this may take a while)[/italic]...")
    start_time = time.time()

    try:
        fit = sampler.sample(
            data=data_dict,
            iter_sampling=1500,
            iter_warmup=500,
            show_progress=True,
            seed=1,
            inits=0.2,
            chains=4,
        )
        logger.info(f"[green]Sampling complete[/green] in [bold]{time.time() - start_time:.2f}[/bold] seconds.")
    except Exception as e:
        logger.error(f"Stan sampling failed. Check your model parameters or data inputs. Error: {e}")
        sys.exit(1)

    # 4. Save Productivity Parameters (Critical for Pyomo)
    try:
        gamma_mean = fit.stan_variable("gamma").mean(axis=0)
        theta_mean = fit.stan_variable("theta").mean(axis=0)
        df_params = pd.DataFrame({"gamma_fit": gamma_mean, "theta_fit": theta_mean})

        params_path = DATA_DIR / f"productivity_params_{num_sites}.csv"
        df_params.to_csv(params_path, index=False)
        logger.info(f"Saved productivity params to: [blue]{params_path}[/blue]")
    except Exception as e:
        logger.error(f"Failed to extract or save productivity parameters: {e}")
        sys.exit(1)

    # 5. Save Pickled Posterior Samples
    out_path = OUTPUT_DIR / "sampling" / "gurobi" / f"{num_sites}sites" / "baseline"

    try:
        out_path.mkdir(parents=True, exist_ok=True)
        pcl_path = out_path / "results.pcl"

        with open(pcl_path, "wb") as outfile:
            pickle.dump({
                "gamma": fit.stan_variable("gamma"),
                "theta": fit.stan_variable("theta")
            }, outfile)
        logger.info(f"Saved posterior distributions to: [blue]{pcl_path}[/blue]")
    except OSError as e:
        logger.error(f"Failed to save pickled posterior samples: {e}")

    # 6. Save Percentile Tables
    def save_percentiles(var_name, data):
        '''Calculate and save 10th, 50th, and 90th percentiles for a given variable. Saves to CSV in output/tables.'''
        try:
            pct = np.percentile(data, [10, 50, 90], axis=0)
            pd.DataFrame({
                "10th_percentile": pct[0],
                "50th_percentile": pct[1],
                "90th_percentile": pct[2],
            }).to_csv(OUTPUT_DIR / "tables" / f"{var_name}_percentiles_{num_sites}.csv", index=False)
        except Exception as e:
            logger.error(f"Failed to save percentiles for {var_name}: {e}")

    save_percentiles("gamma", fit.stan_variable("beta_gamma"))
    save_percentiles("theta", fit.stan_variable("beta_theta"))
    logger.info("Saved percentile tables.")

if __name__ == "__main__":
    generate_calibration_data(num_sites=1043)