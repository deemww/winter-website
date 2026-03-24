# This is a basic docker image for use in the clinic
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Switch to root to update and install tools
USER root

# Added build-essential (for CmdStan) and open-source solvers (GLPK/CBC for Pyomo)
RUN apt-get update && apt-get install -y \
    curl git build-essential \
    libspatialindex-dev \
    libgdal-dev \
    libgeos-dev \
    gdal-bin \
    glpk-utils coinor-cbc \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /project

# Copy source and config for initial install
COPY src ./src
COPY pyproject.toml .
COPY uv.lock .

# Create venv in /opt so it won't be shadowed by volume mounts
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
RUN /usr/local/bin/uv venv $UV_PROJECT_ENVIRONMENT
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH=/project/src

RUN uv sync

# Install and compile CmdStan binaries required by cmdstanpy
RUN python -c "import cmdstanpy; cmdstanpy.install_cmdstan()"

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "Home.py", "--server.port=8501", "--server.address=0.0.0.0"]