# TS_ANALYSIS_HECTOR

Repository for running time-series analysis workflows with HECTOR.

## Repository layout

- `scripts/` contains executable helper scripts.
- `projects/` contains generated analysis projects and outputs.
- `example_python/` contains upstream or exploratory Python examples.

## Installation

Create the Conda environment from the repository file:

```bash
conda env create -f environment.yml
conda activate ts-analysis-hector
```

If you later update `environment.yml`, refresh the environment with:

```bash
conda env update -f environment.yml --prune
```

Current core dependencies:

- `python 3.12`
- `numpy`
- `scipy`
- `matplotlib`

`requirements.txt` is kept as a simple pip fallback, but the primary setup for this repository is Conda.

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
