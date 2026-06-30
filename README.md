# TS_ANALYSIS_HECTOR

Repository for running time-series analysis workflows with HECTOR.

## Repository layout

- `scripts/` contains executable helper scripts.
- `projects/` can be used for local generated projects and outputs.
- `example_python/` contains upstream or exploratory Python examples.
- `project_registry.json` maps project names to their absolute filesystem paths.

## Installation

Create the Conda environment from the repository file:

```bash
conda env create -f environment.yml
conda activate ts-analysis-hector
python -m pip install -e .
```

If you later update `environment.yml`, refresh the environment with:

```bash
conda env update -f environment.yml --prune
```

If you add or change command aliases, reinstall the local package:

```bash
python -m pip install -e .
```

Current core dependencies:

- `python 3.12`
- `numpy`
- `scipy`
- `matplotlib`

`requirements.txt` is kept as a simple pip fallback, but the primary setup for this repository is Conda.

## Initialize a project

Create a new project scaffold using the installed command alias:

```bash
initiate-project my_project
```

To place a project outside the repository, point to a different base directory:

```bash
initiate-project my_project --project-root /data/hector_ts
```

Equivalent direct Python entrypoints:

```bash
python3 scripts/init_project.py my_project
python3 main.py my_project
```

Optional arguments:

- `--project-root /path/to/projects_base` to choose where the project directory is created.
- `--hector-home /path/to/hector` to override the default HECTOR location.
- `--overwrite-registry` to replace an existing project name mapping in `project_registry.json`.
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

Each initialized project is also registered in `project_registry.json`, so future scripts can resolve a project name to its actual location even when projects are stored outside this repository.
