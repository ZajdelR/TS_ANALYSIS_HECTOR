# TS_ANALYSIS_HECTOR

Repository for running time-series analysis workflows with HECTOR.

## Repository layout

- `scripts/` contains executable helper scripts.
- `projects/` contains generated analysis projects and outputs.
- `example_python/` contains upstream or exploratory Python examples.

## Installation

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Current dependencies:

- `numpy`
- `scipy`
- `matplotlib`

## Initialize a project

Create a new project scaffold under `projects/`:

```bash
python3 scripts/init_project.py my_project
```

You can also use the top-level entrypoint:

```bash
python3 main.py my_project
```

Optional arguments:

- `--hector-home /path/to/hector` to override the default HECTOR location.
- `--overwrite-config` to regenerate an existing `config/config.yaml`.

Default HECTOR path written to the config:

```text
/home/radek/app/hector
```

## Generated project structure

Each initialized project currently contains:

- `config/config.yaml`
- `data/raw/`
- `data/processed/`
- `metadata/`
- `outputs/figures/`
- `outputs/hector/`
- `logs/`

The generated `config.yaml` stores general analysis options and paths to HECTOR executables and input files.
