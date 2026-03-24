'''app_utilities

Utilities needed for the data preprocessing process, Guided Tour and Freeroam apps.

This package provides helper functions and configurations for data loading, processing, and visualization.
There are a few submodules:
1. Packages involved in the data preprocessing pipeline
    1.1 dataprep_utils: helper functions for data preprocessing parts 1 and 2 (Shapefile processing and Census/BEA data processing)
    1.2 census_bea_pipeline: functions to interact with the Census BEA API and process the data:
        1.2.1 get_census_bea_data: functions to download data from the Census BEA API
        1.2.2 clean_census_bea_data: functions to clean the raw data downloaded from the API
        1.2.3 merge_census_bea_data: functions to merge cleaned data into final datasets
        1.2.4 build_census_bea_resources: function to build resources needed for the final datasets
2. Packages involved in the Guided Tour pages:
    2.1 charts.py: functions to create charts used in the Guided Tour app
    2.2 demographics.py: functions to render demographic comparison visualizations
    2.3 loaders.py: functions to load datasets for the Guided Tour app
3. Package involved in the Freeroam page:
    3.1 map_visualization_helper.py: functions to create MapLibre maps and other visualizations for the Freeroam app
4. config.py: configuration constants and paths used across the package
'''

from __future__ import annotations

import logging
from pathlib import Path

from rich.logging import RichHandler

__all__ = ["__version__", "get_version", "setup_logger"]

__version__ = "0.0.1"


def get_version() -> str:
    '''Return the package version.'''
    return __version__


def setup_logger(name: str | None = None, level: int = logging.INFO) -> logging.Logger:
    '''Configure and return a Rich-enabled logger for the package.

    Use this function when running scripts in isolation.
    Do NOT use this if your main application has already configured logging.
    '''
    logger = logging.getLogger(name or "app_utilities")
    logger.setLevel(level)
    if not logger.handlers:
        handler = RichHandler(
            rich_tracebacks=True, markup=True, show_time=False, show_level=True
        )

        logger.addHandler(handler)
        logger.propagate = False

    return logger


# Ensure importing the package doesn't emit logs unless the app configures logging.
logging.getLogger(__name__).addHandler(logging.NullHandler())


def find_project_root(start: Path | None = None) -> Path:
    '''Walk upward from the given file until we find the project root.

    The root is identified by containing BOTH:
    - pyproject.toml
    - data/ directory
    '''
    start = start or Path(__file__).resolve()

    for parent in [start, *start.parents]:
        if (parent / "pyproject.toml").exists() and (parent / "data").exists():
            return parent

    # Fallback: return directory containing utils
    return Path(__file__).resolve().parent.parent
