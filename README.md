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

Default HECTOR path written to the config:

```text
/home/radek/app/hector
```

## Generated project structure

Each initialized project currently contains:

- `config/config.yaml`
- `ori_files/`
- `raw_files/`
- `obs_files/`
- `pre_files/`
- `mom_files/`
- `sea_files/`
- `fil_files/`

The generated `config.yaml` stores general analysis options and paths to HECTOR executables and input files.

Each initialized project is also registered in `project_registry.json`, so future scripts can resolve a project name to its actual location even when projects are stored outside this repository.

If the target project directory already exists, the initializer asks whether it should remove the previous directory and recreate it from scratch.

## Import original files

Copy all files from a source directory into a project's `ori_files/` directory:

```bash
copy-original-files my_project /path/to/source_directory
```

Equivalent direct Python entrypoint:

```bash
python3 scripts/copy_original_files.py my_project /path/to/source_directory
```

Optional arguments:

- `--overwrite` to replace existing files in `ori_files/` without prompting.

Without `--overwrite`, the script asks before replacing each existing file.

## Convert DAT to NEU

Convert `.dat` files from a project's `ori_files/` directory into `.neu` files in
the same `ori_files/` directory:

```bash
convert-dat-to-neu my_project
```

To convert only one file:

```bash
convert-dat-to-neu my_project --filename station.dat
```

Equivalent direct Python entrypoint:

```bash
python3 scripts/convert_dat_to_neu.py my_project
```

Optional arguments:

- `--filename station.dat` to convert a single file from `ori_files/`.
- `--overwrite` to replace existing `.neu` files without prompting.

The generated `.neu` files follow this convention:

- column 1: time as year-fraction
- columns 2-4: North, East, Up in metres
