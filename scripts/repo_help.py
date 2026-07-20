#!/usr/bin/env python3
"""Repository-level help for the HECTOR workflow."""

from __future__ import annotations

import argparse


HELP_TEXT = """\
TS_ANALYSIS_HECTOR repository help

Purpose
  Run a project-based HECTOR time-series workflow from raw input files to
  converted MOM files, analysis, plots, and summary reports.

Machine-level setup
  1. Edit machine_config.yaml
     Important keys:
       - defaults.project_root
       - defaults.hector_home
  2. Create and activate the environment
       conda env create -f environment.yml
       conda activate ts-analysis-hector
       python -m pip install -e .
  3. Ensure HECTOR binaries are executable
       chmod +x /path/to/hector/*

Main workflow
  1. Create a project
       initiate-project my_project

  2. Copy original files into the project
       copy-original-files my_project /path/to/source_directory

  3. Convert DAT to NEU
       convert-dat-to-neu my_project

  4. Convert NEU to MOM
       convert-neu-to-mom my_project

  5. Analyse and plot
       analyse-and-plot my_project

Project structure
  config/
    config.yaml
    hector/
  ori_files/
  raw_files/
  obs_files/
  pre_files/
  mom_files/
  json_output/
  sea_files/
  fil_files/

Installed commands
  initiate-project
    Create or refresh a project scaffold and config.

  copy-original-files
    Copy source files into ori_files/.

  convert-dat-to-neu
    Convert .dat files in ori_files/ to .neu files in ori_files/.

  convert-neu-to-mom
    Convert .neu files in ori_files/ to component .mom files in raw_files/.

  analyse-and-plot
    Run HECTOR analysis on raw_files/, create analysed MOM files, plots, and reports.

  repo-help
    Show this repository-level workflow help.

HECTOR control files
  - example_hector_config/ contains repository default .ctl files.
  - initiate-project copies those .ctl files into config/hector/ inside the
    project.
  - analyse-and-plot reads the project-local config/hector/ files as templates.
  - For each run it writes temporary .ctl files under
    hector_run_temp/STATION_DATE_TIME and applies run-specific values there.
  - Use analyse-and-plot --keep-temp-config to preserve that temporary run
    directory for inspection after the run.
  - analyse-and-plot does not modify the project-local config/hector/ files.

Common outputs
  pre_files/
    Outlier-cleaned MOM files

  mom_files/
    Analysed MOM files

  json_output/
    Station/project-named Hector JSON summaries
    *_hector_estimatetrend.json
    *_hector_removeoutliers.json

  fil_files/data_figures/
    Per-component and combined time-series plots

  fil_files/psd_figures/
    Lomb-Scargle period plots
    PSD plots only when --make-psd-plots is used

  fil_files/reports/
    Station summary reports

Notes
  - Analysis choices come from the project-local config/hector/ .ctl files.
  - --noise-model is optional and overrides the .ctl noise model for one run.
  - --fit-seasonal/--no-fit-seasonal and
    --fit-halfseasonal/--no-fit-halfseasonal override the matching .ctl values
    for one run.
  - PSD plots are skipped by default because the spectrum/model-spectrum steps
    can be slow. Use --make-psd-plots when you need them.
  - Offset finding is skipped by default. Use --find-offsets to run Hector
    findoffset, write offset-annotated MOM files to obs_files/, and mark
    detected offsets in plots.
  - Default INFO logs show START/DONE timing messages for Hector commands,
    plots, reports, and station/component workflows. Use --log-level WARNING
    for quieter output or --log-level DEBUG for more detail.
  - project_registry.json maps project names to absolute project paths.
"""


def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        description="Show repository-level help and workflow overview."
    )


def main() -> int:
    build_parser().parse_args()
    print(HELP_TEXT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
