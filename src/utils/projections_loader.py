'''This module contains the code to load the model and its projections.
Through this module, we can create visualizations of deforestation projections under different scenarios.
'''

import math
import time
from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import pyomo.environ as pyo
import streamlit as st
from pyomo.environ import (
    ConcreteModel,
    Constraint,
    NonNegativeReals,
    Objective,
    Param,
    RangeSet,
    Var,
    maximize,
)
from pyomo.opt import SolverFactory

from src.utils.config import PROJECT_ROOT
from src.utils import setup_logger

logger = setup_logger(__name__)

## Parameter setting

dt=1
time_horizon=200
price_emissions=6.6
price_cattle=41.11
alpha=0.045007414
delta=0.02
kappa=2.094215255
zeta_u=1.66e-4 * 1e9
zeta_v=1.00e-4 * 1e9
solver="gurobi"

# --- Setup Paths ---
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output" / "optimization"

@dataclass
class PlannerSolution:
    '''Data class to hold the results of the optimization.'''
    Z: np.ndarray
    X: np.ndarray
    U: np.ndarray
    V: np.ndarray

# --- 1. Data Loading Functions ---

def load_productivity_params(num_sites: int = 1043):
    '''Load theta and gamma parameters for the given number of sites.'''
    file_path = DATA_DIR / f"productivity_params_{num_sites}.csv"
    try:
        productivity_params = pd.read_csv(file_path)
        theta = productivity_params["theta_fit"].to_numpy()[:,].flatten()
        gamma = productivity_params["gamma_fit"].to_numpy()[:,].flatten()
        return theta, gamma
    except FileNotFoundError:
        logger.error(f"Productivity params not found at {file_path}. Run calibration first.")
        raise
    except KeyError as e:
        logger.error(f"Missing column in productivity params: {e}")
        raise

def load_site_data(num_sites: int = 1043, year: int = 2017, norm_fac: float = 1e9):
    '''Load calibration data for a specific year.'''
    file_path = DATA_DIR / f"calibration_{num_sites}_sites.csv"
    try:
        df = pd.read_csv(file_path)
        z = df[f"z_{year}"].to_numpy() / norm_fac
        zbar = df[f"zbar_{year}"].to_numpy() / norm_fac
        forest_area = df[f"area_forest_{year}"].to_numpy() / norm_fac
        return zbar, z, forest_area
    except FileNotFoundError:
        logger.error(f"Calibration data not found at {file_path}.")
        raise
    except KeyError as e:
        logger.error(f"Missing required year column in calibration data: {e}")
        raise

# --- 2. Pyomo Optimization Rules ---

def _planner_obj(model):
    '''Defines the objective function for the planner's optimization problem,
    incorporating discounted net benefits from land use decisions over time.'''
    return pyo.quicksum(
        math.exp(-model.delta * (t * model.dt - model.dt)) * (
            -model.pe * pyo.quicksum(
                model.kappa * model.z[t + 1, s]
                - (model.x[t + 1, s] - model.x[t, s]) / model.dt
                for s in model.S
            )
            + model.pa[t] * pyo.quicksum(model.theta[s] * model.z[t + 1, s] for s in model.S)
            - (model.zeta_u / 2) * (model.w1[t] ** 2)
            - (model.zeta_v / 2) * (model.w2[t] ** 2)
        ) * model.dt
        for t in model.T if t < max(model.T)
    )

def _zdot_const(model, t, s):
    '''Defines the land allocation dynamics constraint, ensuring that the change
    in agricultural area (z) over time is consistent with land use decisions.'''
    if t < max(model.T):
        return (model.z[t + 1, s] - model.z[t, s]) / model.dt == (model.u[t, s] - model.v[t, s])
    return Constraint.Skip

def _xdot_const(model, t, s):
    '''Defines the dynamics constraint for the livestock population (x), ensuring
    that the change over time is consistent with land use decisions.'''
    if t < max(model.T):
        return (model.x[t + 1, s] - model.x[t, s]) / model.dt == (
            -model.gamma[s] * model.u[t, s]
            - model.alpha * model.x[t, s]
            + model.alpha * model.gamma[s] * (model.zbar[s] - model.z[t, s])
        )
    return Constraint.Skip

def _w1_const(model, t):
    '''Defines the auxiliary variable w1 as the sum of all u[t, s] across sites, representing total land conversion.'''
    if t < max(model.T):
        return model.w1[t] == pyo.quicksum(model.u[t, s] for s in model.S)
    return Constraint.Skip

def _w2_const(model, t):
    '''Defines the auxiliary variable w2 as the sum of all v[t, s] across sites, representing total land abandonment.'''
    if t < max(model.T):
        return model.w2[t] == pyo.quicksum(model.v[t, s] for s in model.S)
    return Constraint.Skip

def _np_to_dict(x):
    '''Helper function to convert a numpy array into a dictionary format suitable for Pyomo parameters.'''
    return dict(enumerate(x.flatten(), 1))

# --- 3. Core Solver ---

def solve_planner_problem(
    x0, z0, zbar, gamma, theta, dt=dt, time_horizon=time_horizon,
    price_emissions=price_emissions, price_cattle=price_cattle, alpha=alpha,
    delta=delta, kappa=kappa, zeta_u=zeta_u, zeta_v=zeta_v,
    solver=solver
):
    '''Constructs and solves the dynamic land allocation model.'''
    model = ConcreteModel()
    model.T = RangeSet(time_horizon + 1)
    model.S = RangeSet(gamma.size)

    # Parameters
    model.x0 = Param(model.S, initialize=_np_to_dict(x0))
    model.z0 = Param(model.S, initialize=_np_to_dict(z0))
    model.zbar = Param(model.S, initialize=_np_to_dict(zbar))
    model.gamma = Param(model.S, initialize=_np_to_dict(gamma))
    model.theta = Param(model.S, initialize=_np_to_dict(theta))
    model.delta = Param(initialize=delta)
    model.pe = Param(initialize=price_emissions)
    model.pa = Param(model.T, initialize={t + 1: price_cattle for t in range(time_horizon)} if isinstance(price_cattle, float) else {t + 1: price_cattle[t] for t in range(time_horizon)})
    model.zeta_u = Param(initialize=zeta_u)
    model.zeta_v = Param(initialize=zeta_v)
    model.alpha = Param(initialize=alpha)
    model.kappa = Param(initialize=kappa)
    model.dt = Param(initialize=dt)

    # Variables
    model.x = Var(model.T, model.S)
    model.z = Var(model.T, model.S, within=NonNegativeReals)
    model.u = Var(model.T, model.S, within=NonNegativeReals)
    model.v = Var(model.T, model.S, within=NonNegativeReals)
    model.w1 = Var(model.T)
    model.w2 = Var(model.T)

    # Constraints & Objective
    model.zdot_def = Constraint(model.T, model.S, rule=_zdot_const)
    model.xdot_def = Constraint(model.T, model.S, rule=_xdot_const)
    model.w1_def = Constraint(model.T, rule=_w1_const)
    model.w2_def = Constraint(model.T, rule=_w2_const)
    model.obj = Objective(rule=_planner_obj, sense=maximize)

    # Solve
    try:
        opt = SolverFactory(solver, solver_io="python")
        logger.info(f"Solving optimization problem with [bold]{solver}[/bold]...")
        start_time = time.time()

        results = opt.solve(model, tee=False)

        # Check if the solver actually found an optimal solution
        if (results.solver.status != pyo.SolverStatus.ok) or (results.solver.termination_condition != pyo.TerminationCondition.optimal):
            logger.warning(f"Solver issue detected. Status: {results.solver.status}, Termination: {results.solver.termination_condition}")

        logger.info(f"[bold green]Done![/bold green] Time elapsed: [bold]{time.time()-start_time:.2f}[/bold] seconds.")

        Z = np.array([[model.z[t, r].value for r in model.S] for t in model.T])
        X = np.array([[model.x[t, r].value for r in model.S] for t in model.T])
        U = np.array([[model.u[t, r].value for r in model.S] for t in model.T])
        V = np.array([[model.v[t, r].value for r in model.S] for t in model.T])

        return PlannerSolution(Z, X, U, V)

    except Exception as e:
        logger.error(f"Failed to solve the model using {solver}. Ensure the solver is installed and licensed. Error: {e}")
        raise RuntimeError(f"Optimization failed: {e}")

# --- 4. Execution Block (Run Pre-computations) ---

def generate_all_projections(num_sites=1043, base_pe=price_emissions, pa=price_cattle, solver=solver):
    '''Runs the solver across a grid of parameter values and saves the results.'''
    # 1. Load Data
    zbar_2017, z_2017, forest_area_2017 = load_site_data(num_sites, year=2017)
    theta_vals, gamma_vals = load_productivity_params(num_sites)
    x0_vals = gamma_vals * forest_area_2017

    # 2. Define Scenario Sweep
    b_values = [0, 10, 15, 20, 25]
    pe_values = [base_pe + b for b in b_values]

    for pe in pe_values:
        logger.info(f"[bold magenta]--- Running scenario: PE = {pe} ---[/bold magenta]")
        try:
            results = solve_planner_problem(
                time_horizon=200,
                theta=theta_vals,
                gamma=gamma_vals,
                x0=x0_vals,
                zbar=zbar_2017,
                z0=z_2017,
                price_emissions=pe,
                price_cattle=pa,
                solver=solver,
            )

            # Determine output path
            out_path = OUTPUT_DIR / f"{num_sites}_sites" / f"pa_{pa}" / f"pe_{pe}"
            out_path.mkdir(parents=True, exist_ok=True)

            # Save results
            np.save(out_path / "Z_trajectory.npy", results.Z)
            np.save(out_path / "X_trajectory.npy", results.X)
            np.save(out_path / "U_trajectory.npy", results.U)
            np.save(out_path / "V_trajectory.npy", results.V)
            logger.info(f"Saved results to [blue]{out_path}[/blue]")

        except Exception as e:
            logger.error(f"Failed to generate or save projections for PE = {pe}. Skipping to next scenario. Error: {e}")
            continue # Allows the loop to try the next scenario instead of crashing entirely

@st.cache_data
def load_scenario_projections(pa: float, pe: float, num_sites: int = 1043):
    '''Loads pre-computed Pyomo trajectories from .npy files.'''
    scenario_path = OUTPUT_DIR / f"{num_sites}_sites" / f"pa_{pa}" / f"pe_{pe}"

    if not scenario_path.exists():
        return None

    try:
        return {
            "Z": np.load(scenario_path / "Z_trajectory.npy"),
            "X": np.load(scenario_path / "X_trajectory.npy"),
            "U": np.load(scenario_path / "U_trajectory.npy"),
            "V": np.load(scenario_path / "V_trajectory.npy")
        }
    except FileNotFoundError as e:
        logger.error(f"Incomplete projection data at {scenario_path}. Error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading numpy arrays: {e}")
        return None

def get_choropleth_data(year: int, pe: float = price_emissions, pa: float = price_cattle):
    '''
    Extracts site-specific data for a single year and formats it for mapping.
    '''
    scenario_path = OUTPUT_DIR / f"1043_sites" / f"pa_{pa}" / f"pe_{pe}"

    if not scenario_path.exists():
        raise FileNotFoundError(f"Could not find data for Pe={pe} at {scenario_path}")

    try:
        Z_matrix = np.load(scenario_path / "Z_trajectory.npy")
        X_matrix = np.load(scenario_path / "X_trajectory.npy")
        U_matrix = np.load(scenario_path / "U_trajectory.npy")
        V_matrix = np.load(scenario_path / "V_trajectory.npy")

        z_year = Z_matrix[year, :]
        x_year = X_matrix[year, :]
        u_year = U_matrix[year, :]
        v_year = V_matrix[year, :]

        map_df = pd.DataFrame({
            "site_index": range(1, 1044),
            "agricultural_area_Z": z_year,
            "carbon_stock_X": x_year,
            "deforestation_rate_U": u_year,
            "abandonment_rate_V": v_year
        })
        return map_df
    except Exception as e:
        logger.error(f"Failed to extract choropleth data for year {year}: {e}")
        raise

def append_projections_to_gdf(gdf, pe=6.6, pa=44.75):
    '''Calculates 50 years of normalized Z projections and appends them to a GeoDataFrame.'''
    num_sites = 1043

    try:
        zbar, _, _ = load_site_data(num_sites=num_sites, year=2017)

        scenario_path = OUTPUT_DIR / f"{num_sites}_sites" / f"pa_{pa}" / f"pe_{pe}"
        Z_matrix = np.load(scenario_path / "Z_trajectory.npy")

        Z_50_years = Z_matrix[:51, :]

        # Protect against division by zero just in case zbar has 0s
        with np.errstate(divide='ignore', invalid='ignore'):
            Z_pct_matrix = np.where(zbar > 0, (Z_50_years / zbar) * 100, 0)

        Z_pct_sites = Z_pct_matrix.T

        column_names = [f"Z_pct_yr{t}" for t in range(51)]
        df_projections = pd.DataFrame(Z_pct_sites, columns=column_names)
        df_projections['id'] = range(1, num_sites + 1)

        updated_gdf = gdf.merge(df_projections, on='id', how='left')
        return updated_gdf

    except FileNotFoundError as e:
        logger.error(f"Required data missing to append projections: {e}")
        raise # Reraise so Streamlit's UI try/except block catches it
    except Exception as e:
        logger.error(f"Unexpected error appending projections to map data: {e}")
        raise

def make_choropleth(gdf: pd.DataFrame, color_col: str, title: str, color_scale: str = "Reds") -> go.Figure:
    '''Generates a MapLibre choropleth map from a Dataframe.'''
    if color_col not in gdf.columns:
        logger.error(f"Column '{color_col}' not found in GeoDataFrame.")
        # Return an empty figure gracefully if the data merge failed upstream
        return go.Figure().update_layout(title="Data Missing for this Scenario")

    try:
        years_from_base = int(color_col.replace("Z_pct_yr", ""))
        display_year = 2017 + years_from_base
    except ValueError:
        display_year = "Selected Year"

    fig = px.choropleth_map(
        gdf,
        geojson=gdf.geometry,
        locations=gdf.index,
        color=color_col,
        color_continuous_scale=color_scale,
        range_color=[0, 100],
        custom_data=["id"],
        map_style="open-street-map",
        zoom=3.5,
        center={"lat": -5.0, "lon": -59.0},
        opacity=0.68
    )

    custom_hover = (
        "<b>Site ID:</b> %{customdata[0]}<br>" +
        "<b>Projected " + str(display_year) + " agricultural land coverage:</b> %{z:.1f}%" +
        "<extra></extra>"
    )

    fig.update_traces(hovertemplate=custom_hover)

    fig.update_layout(
        title=title,
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        height=500,
        coloraxis_colorbar={
            "orientation": "h",
            "yanchor": "top",
            "y": 0.05,
            "xanchor": "center",
            "x": 0.5,
            "len": 0.8,
            "title": "Agricultural Area Coverage (%)",
            "thickness": 10,
        },
    )
    return fig

def render_projection_site_deep_dive(site_id, gdf_base, gdf_scen, transfer_amount):
    '''Render the comparative deep dive section for a selected site.'''
    try:
        site_id_converted = site_id + 1
        st.header(f"Site {site_id_converted} Trajectory Analysis")

        row_base = gdf_base[gdf_base['id'] == site_id_converted].squeeze()
        row_scen = gdf_scen[gdf_scen['id'] == site_id_converted].squeeze()

        projection_indices = list(range(51))
        traj_base = [row_base[f"Z_pct_yr{t}"] for t in projection_indices]
        traj_scen = [row_scen[f"Z_pct_yr{t}"] for t in projection_indices]

        calendar_years = list(range(2017, 2068))

        base_final = traj_base[-1]
        scen_final = traj_scen[-1]
        diff = base_final - scen_final

        if diff > 5.0:
            st.success(f"**Significant Impact:** Your choice of a ${transfer_amount:.0f}-per-ton transfer has significantly preserved/reforested this region compared to the baseline.")
        elif diff > 0.5:
            st.info(f"**Slight Impact:** Your ${transfer_amount:.0f}-per-ton transfer slightly reduced agricultural expansion here.")
        elif diff < -0.5:
            st.warning(f"Under a ${transfer_amount:.0f}-per-ton transfer, agricultural area actually increased compared to baseline.")
        else:
            st.write(f"This region's trajectory remains unaffected by the ${transfer_amount:.0f}-per-ton transfer.")

        df_plot = pd.DataFrame({
            "Year": calendar_years + calendar_years,
            "Agricultural Area (%)": traj_base + traj_scen,
            "Scenario": ["Baseline (b=0)"] * 51 + [f"Policy (b={transfer_amount:.0f})"] * 51
        })

        fig = px.line(
            df_plot,
            x="Year",
            y="Agricultural Area (%)",
            color="Scenario",
            color_discrete_map={
                "Baseline (b=0)": "gray",
                f"Policy (b={transfer_amount:.0f})": "#2ca02c"
            }
        )

        fig.update_layout(
            yaxis_range=[0, max(traj_base + traj_scen) + 10],
            margin={"r": 0, "t": 30, "l": 0, "b": 0},
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        st.plotly_chart(fig, use_container_width=True)
    except KeyError as e:
        st.error(f"Error extracting site data. Missing column: {e}")
    except Exception as e:
        st.error(f"An error occurred generating the deep dive plot: {e}")

def generate_aggregate_trajectory_charts(b_values, base_pe, selected_pa, zbar_total, colors):
    '''
    Iterates through the b_values to load projection data and constructs
    the aggregate trajectory line charts for Agricultural Area (Z) and Carbon Stock (X).
    '''
    fig_z = go.Figure()
    fig_x = go.Figure()
    data_missing = False
    calendar_years = list(range(2017, 2068))

    for j, b in enumerate(b_values):
        current_pe = base_pe + b
        trajectories = load_scenario_projections(pa=selected_pa, pe=current_pe)

        if trajectories is not None:
            try:
                Z_matrix = trajectories["Z"][:51, :]
                X_matrix = trajectories["X"][:51, :]

                # Protect against division by zero
                z_agg_per_year = np.sum(Z_matrix, axis=1)
                z_percentage = (z_agg_per_year / zbar_total) * 100 if zbar_total > 0 else np.zeros_like(z_agg_per_year)

                fig_z.add_trace(go.Scatter(
                    x=calendar_years,
                    y=z_percentage,
                    mode='lines',
                    name=f'b=${b}',
                    line=dict(color=colors[j], width=3)
                ))

                x_agg_per_year = np.sum(X_matrix, axis=1)

                fig_x.add_trace(go.Scatter(
                    x=calendar_years,
                    y=x_agg_per_year,
                    mode='lines',
                    name=f'b=${b}',
                    line=dict(color=colors[j], width=3)
                ))
            except Exception as e:
                logger.error(f"Error processing trajectories for b={b}: {e}")
                data_missing = True
        else:
            data_missing = True

    # Formatting Charts
    fig_z.update_layout(
        title="a) Agricultural Land Allocation Trajectory (Z)",
        xaxis_title="Year",
        yaxis_title="Z (%)",
        height=450,
        hovermode="x unified",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    fig_x.update_layout(
        title="b) Forest Carbon Stock Evolution (X)",
        xaxis_title="Year",
        yaxis_title="X (billion tons CO2e)",
        height=450,
        hovermode="x unified",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig_z, fig_x, data_missing

# --- 4. Functions that Run Optimizations ---

def run_generation():
    '''Runs the Pyomo optimization for the specified scenarios and saves the results.'''

    target_sites = [1043]

    logger.info("[bold cyan]=== Starting Amazon Deforestation Pyomo Optimization ===[/bold cyan]")

    for sites in target_sites:
        logger.info(f"[bold cyan]Generating Projections for: {sites} Sites[/bold cyan]")

        try:
            generate_all_projections(
                num_sites=sites,
                base_pe=price_emissions,
                pa=price_cattle,
                solver="gurobi"
            )
            logger.info(f"[bold green]Successfully finished all scenarios for {sites} sites.[/bold green]")

        except Exception as e:
            logger.exception(f"[bold red]Failed to generate projections for {sites} sites. Error: {e}[/bold red]")
            logger.warning(
                "Troubleshooting:\n"
                "1. Ensure you have run build_calibration.py to generate the .csv parameters.\n"
                "2. Verify that your Gurobi solver license is active and accessible."
            )
            # Raise it so the Streamlit UI can catch it and display a user-friendly error
            raise

    logger.info("[bold cyan]=== All optimization runs completed successfully! ===[/bold cyan]")

if __name__ == "__main__":
    run_generation()