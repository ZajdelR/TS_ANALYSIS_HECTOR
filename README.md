# TS_ANALYSIS_HECTOR

Repository for running time-series analysis workflows with HECTOR.

## Machine config

[`machine_config.yaml`](/home/radek/PYTHON_PROJECTS/TS_ANALYSIS_HECTOR/machine_config.yaml) is the machine-level template used to generate new project configs.

Edit it to match your machine before creating projects, especially:

- `defaults.project_root`
- `defaults.hector_home`
- any common analysis defaults under `analysis`
- `analysis.estimate_seasonal_signals`
- `analysis.estimate_halfseasonal_signals`

`initiate-project` reads this file and uses it as the base for each new `config/config.yaml`. Command-line options such as `--project-root` and `--hector-home` still override the machine config for one-off runs.

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

Repository-wide command help:

```bash
repo-help
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

Default project root used by `initiate-project`:

```text
/data/GNSS/hector-projects/
```

To place a project somewhere else, point to a different base directory:

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
/home/rade/HECTOR_TEMP/
```

## Generated project structure

Each initialized project currently contains:

- `config/config.yaml`
- `config/hector/` with copied example HECTOR `.ctl` files
- `ori_files/`
- `raw_files/`
- `obs_files/`
- `pre_files/`
- `mom_files/`
- `sea_files/`
- `fil_files/`

The generated `config.yaml` stores general analysis options and paths to HECTOR executables and input files.

Each initialized project is also registered in `project_registry.json`, so future scripts can resolve a project name to its actual location even when projects are stored outside this repository.

If the target project directory already exists, the initializer offers three choices:

- remove the whole project directory and recreate it
- keep the existing directories and refresh only `config/config.yaml` plus `config/hector/`
- cancel initialization

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

## Convert NEU to MOM

Convert `.neu` files from a project's `ori_files/` directory into `.mom` files in
`raw_files/`:

```bash
convert-neu-to-mom my_project
```

To convert only one file:

```bash
convert-neu-to-mom my_project --filename station.neu
```

Equivalent direct Python entrypoint:

```bash
python3 scripts/convert_neu_to_mom.py my_project
```

Optional arguments:

- `--filename station.neu` to convert a single file from `ori_files/`.
- `--sampling-period 1.0` to control the `# sampling period` header.
- `--overwrite` to replace existing `.mom` files without prompting.

For each input `.neu` file, the script writes:

- `_0.mom` for East
- `_1.mom` for North
- `_2.mom` for Up

## Analyse and plot

Run a project-aware adaptation of Hector's `analyse_and_plot.py` on the MOM
files in `raw_files/`:

```bash
analyse-and-plot my_project
```

To analyse one station and automatically include its available `_0`, `_1`, `_2`
components:

```bash
analyse-and-plot my_project --station station
```

Equivalent direct Python entrypoint:

```bash
python3 scripts/analyse_and_plot_project.py my_project
```

Optional arguments:

- `--noise-model PLWN` to override `analysis.noise_model` from the project config.
- `--station station` to process one station marker and include all matching component files.
- `--freq 0.0172` to add an extra periodic signal frequency.
- `--fit-seasonal` to force `seasonalsignal yes` for this run.
- `--fit-halfseasonal` to force `halfseasonalsignal yes` for this run.

Runtime note:

- the configured HECTOR binaries must be executable, for example `chmod +x /home/rade/HECTOR_TEMP/*`
- `analyse-and-plot` uses the project-local files in `config/hector/` as the base HECTOR control templates and only overrides run-specific fields such as input/output paths and selected noise model
- if `--fit-seasonal` is absent, the existing `seasonalsignal` value from the project `.ctl` template is preserved
- if `--fit-halfseasonal` is absent, the existing `halfseasonalsignal` value from the project `.ctl` template is preserved
- if either flag is provided, it forces the corresponding setting to `yes` for that run

Outputs:

- cleaned files in `pre_files/`
- analysed MOM files in `mom_files/`
- aggregated `hector_estimatetrend.json` and `hector_removeoutliers.json` in `mom_files/`
- PNG time-series and PSD plots in `fil_files/data_figures/` and `fil_files/psd_figures/`
  : per-component PSD plots include the standard `*_psd.png` view
  : Lomb-Scargle period plots are written separately as `*_lomb_signal_days.png` and `*_lomb_residuals_days.png`
- combined station subplot figures across available `_0/_1/_2` components when they exist
  : `components_data` is arranged as North, East, Up subplots and includes model annotations
  : `components_psd` is also written as a grouped PSD figure for the available components
  : grouped Lomb-Scargle plots are written as `*_components_lomb_signal_days.png` and `*_components_lomb_residuals_days.png`
  : fitted trend, uncertainty, fitted signals, and fitted noise parameters are shown when available
- Markdown station summary reports in `fil_files/reports/`
