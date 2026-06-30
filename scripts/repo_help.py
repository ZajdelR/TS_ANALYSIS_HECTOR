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
       - analysis.noise_model
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

Common outputs
  pre_files/
    Outlier-cleaned MOM files

  mom_files/
    Analysed MOM files
    hector_estimatetrend.json
    hector_removeoutliers.json

  fil_files/data_figures/
    Per-component and combined time-series plots

  fil_files/psd_figures/
    Per-component and combined PSD plots

  fil_files/reports/
    Station summary reports

Notes
  - analyse-and-plot uses analysis.noise_model from config by default.
  - --noise-model can override the config for one run.
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
