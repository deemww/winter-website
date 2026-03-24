'''Metric calculation functions for the Amazon Deforestation app.
'''

import pandas as pd


def calculate_site_metrics(site_data: pd.Series,
                           amazon_df: pd.DataFrame) -> dict:
    '''Calculate key metrics and percentiles for a selected site.'''
    defor_rate = (site_data["z_2017"] - site_data["z_1995"]) / 22
    carbon_lost = site_data["x_1995"] - site_data["x_2017"]
    pct_deforested = (
        (site_data["z_2017"] - site_data["z_1995"])
        / site_data["zbar_2017"] * 100
    )

    theta_percentile = (
        (amazon_df["theta"] < site_data["theta"]).sum() / len(amazon_df) * 100
    )
    gamma_percentile = (
        (amazon_df["gamma"] < site_data["gamma"]).sum() / len(amazon_df) * 100
    )
    ratio_percentile = (
        (amazon_df["theta_gamma_ratio"] < site_data["theta_gamma_ratio"]).sum()
        / len(amazon_df) * 100
    )

    return {
        "defor_rate": defor_rate,
        "carbon_lost": carbon_lost,
        "pct_deforested": pct_deforested,
        "theta_percentile": theta_percentile,
        "gamma_percentile": gamma_percentile,
        "ratio_percentile": ratio_percentile,
    }


def get_pressure_level(ratio_percentile: float,
                       site_data: pd.Series,
                       metrics: dict) -> dict:
    '''Determine deforestation pressure level and description for a site.'''
    theta_percentile = metrics["theta_percentile"]
    gamma_percentile = metrics["gamma_percentile"]

    if ratio_percentile > 75:
        return {
            "level": "**Very High**",
            "description": (
                f"This site faces **very high deforestation pressure** "
                f"(top 25% of all sites). With high agricultural productivity "
                f"(θ = {site_data['theta']:.2f}, \
                    {theta_percentile:.0f}th percentile) "
                f"relative to its carbon storage (γ = {site_data['gamma']:.0f},\
                      "
                f"{gamma_percentile:.0f}th percentile), \
                    there's a strong economic "
                f"incentive to convert forest to agriculture."
            ),
            "box_type": "error",
        }
    elif ratio_percentile > 50:
        return {
            "level": "**Moderate**",
            "description": (
                "This site has **moderate deforestation pressure**. "
                "Its θ/γ ratio suggests balanced economics between "
                "agricultural value and carbon preservation."
            ),
            "box_type": "warning",
        }
    else:
        return {
            "level": "**Low**",
            "description": (
                f"This site has **low deforestation pressure** "
                f"(bottom 50% of sites). With relatively low \
                    agricultural productivity "
                f"(θ = {site_data['theta']:.2f}) \
                    compared to high carbon density "
                f"(γ = {site_data['gamma']:.0f}), preserving the forest may be "
                f"economically favorable."
            ),
            "box_type": "success",
        }


def build_comparison_data(site_data: pd.Series,
                          amazon_df: pd.DataFrame,
                          defor_rate: float) -> dict:
    '''Build normalized comparison data between site and Amazon average.'''
    import pandas as pd

    metrics = {
        "Metric": ["Productivity (θ)",
                   "Carbon Density (γ)",
                   "Deforestation Rate\n(ha/yr)",
                   "θ/γ Ratio"],
        "This Site": [
            site_data["theta"],
            site_data["gamma"],
            defor_rate,
            site_data["theta_gamma_ratio"],
        ],
        "Amazon Average": [
            amazon_df["theta"].mean(),
            amazon_df["gamma"].mean(),
            amazon_df["defor_rate_08_17"].mean(),
            amazon_df["theta_gamma_ratio"].mean(),
        ],
    }

    df = pd.DataFrame(metrics)

    for idx, row in df.iterrows():
        max_val = max(row["This Site"], row["Amazon Average"])
        if max_val > 0:
            df.loc[idx, "This Site_norm"] = row["This Site"] / max_val
            df.loc[idx, "Amazon Average_norm"] = row["Amazon Average"] / max_val
        else:
            df.loc[idx, "This Site_norm"] = 0
            df.loc[idx, "Amazon Average_norm"] = 0

    return df
