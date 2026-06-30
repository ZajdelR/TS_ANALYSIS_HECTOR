#!/usr/bin/env python3
"""Project-aware adaptation of Hector's analyse_and_plot workflow."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import lombscargle

try:
    from scripts.project_config import load_project_config
except ModuleNotFoundError:
    from project_config import load_project_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyse project MOM files with HECTOR and create plots."
    )
    parser.add_argument("project_name", help="Registered project name.")
    parser.add_argument(
        "--noise-model",
        default="",
        help="Optional override for the noise model abbreviation string from config.",
    )
    parser.add_argument(
        "--station",
        default="",
        help="Convert only one station/component stem from raw_files.",
    )
    parser.add_argument(
        "--freq",
        type=float,
        default=0.0,
        help="Extra periodic signal frequency.",
    )
    return parser


def parse_noisemodels(noisemodel_abr: str) -> list[str]:
    abbreviations = ["fGGM", "MT", "GGM", "PL", "FN", "WN", "RW", "AR1", "VA", "VSA"]
    i0 = 0
    i1 = 2
    noisemodels: list[str] = []
    n = len(noisemodel_abr)
    while i1 <= n:
        try:
            index = abbreviations.index(noisemodel_abr[i0:i1])
        except ValueError:
            index = -1
        while index < 0 and i1 <= n and i1 - i0 < 4:
            i1 += 1
            try:
                index = abbreviations.index(noisemodel_abr[i0:i1])
            except ValueError:
                index = -1
        if index < 0:
            raise ValueError(f"Unknown abbreviation: {noisemodel_abr[i0:i1]}")
        token = noisemodel_abr[i0:i1]
        if token in noisemodels:
            raise ValueError(f"{token} repeated")
        noisemodels.append(token)
        i0 = i1
        i1 += 2

    if "GGM" in noisemodels and any(token in noisemodels for token in ("PL", "FN", "RW")):
        raise ValueError("Cannot have GGM and one of PL|FN|RW together")
    return noisemodels


def collect_station_files(raw_dir: Path, station: str) -> list[Path]:
    if station:
        marker = get_station_marker(station)
        grouped_matches = sorted(
            path
            for path in raw_dir.glob(f"{marker}_*.mom")
            if path.is_file() and re.search(r"_\d+$", path.stem)
        )
        if grouped_matches:
            return grouped_matches

        candidate = raw_dir / f"{station}.mom"
        if not candidate.exists():
            raise FileNotFoundError(f"MOM file does not exist: {candidate}")
        return [candidate]

    files = sorted(path for path in raw_dir.glob("*.mom") if path.is_file())
    if not files:
        raise FileNotFoundError(f"No .mom files found in {raw_dir}")
    return files


def get_station_marker(station_name: str) -> str:
    match = re.match(r"(.+)_\d+$", station_name)
    if match:
        return match.group(1)
    return station_name


def get_component_label(station_name: str) -> str:
    match = re.match(r".+_(\d+)$", station_name)
    if not match:
        return station_name
    component = match.group(1)
    labels = {"0": "East", "1": "North", "2": "Up"}
    return labels.get(component, f"Component {component}")


def get_component_index(station_name: str) -> int:
    match = re.match(r".+_(\d+)$", station_name)
    if not match:
        return 99
    return int(match.group(1))


def get_component_sort_key(station_name: str) -> tuple[int, str]:
    component_order = {1: 0, 0: 1, 2: 2}
    component_index = get_component_index(station_name)
    return component_order.get(component_index, 99), station_name


def create_removeoutliers_ctl_file(
    ctl_path: Path,
    station: str,
    raw_dir: Path,
    pre_dir: Path,
    freq: float,
) -> None:
    with ctl_path.open("w", encoding="utf-8") as fp:
        fp.write(f"DataFile            {station}.mom\n")
        fp.write(f"DataDirectory       {raw_dir}\n")
        fp.write("interpolate         no\n")
        fp.write(f"OutputFile          {pre_dir / f'{station}.mom'}\n")
        fp.write("seasonalsignal      yes\n")
        fp.write("halfseasonalsignal  yes\n")
        if freq > 0.0:
            fp.write(f"periodicsignals     {freq:f}\n")
        fp.write("estimateoffsets     yes\n")
        fp.write("estimatepostseismic yes\n")
        fp.write("estimateslowslipevent yes\n")
        fp.write("ScaleFactor         1.0\n")
        fp.write("PhysicalUnit        mm\n")
        fp.write("IQ_factor           3\n")
        fp.write("JSON                yes\n")


def create_estimatetrend_ctl_file(
    ctl_path: Path,
    station: str,
    pre_dir: Path,
    mom_dir: Path,
    noisemodels: list[str],
    freq: float,
) -> None:
    with ctl_path.open("w", encoding="utf-8") as fp:
        fp.write(f"DataFile              {station}.mom\n")
        fp.write(f"DataDirectory         {pre_dir}\n")
        fp.write(f"OutputFile            {mom_dir / f'{station}.mom'}\n")
        fp.write("interpolate           no\n")
        fp.write("PhysicalUnit          mm\n")
        fp.write("ScaleFactor           1.0\n")
        fp.write("JSON                  yes\n")

        names = ""
        need_1mphi = False
        need_varying_phi = False
        for noisemodel in noisemodels:
            if noisemodel == "WN":
                names += " White"
            elif noisemodel in {"GGM", "fGGM"}:
                names += " GGM"
            elif noisemodel == "FN":
                names += " FlickerGGM"
                need_1mphi = True
            elif noisemodel == "RW":
                names += " RandomWalkGGM"
                need_1mphi = True
            elif noisemodel == "PL":
                names += " GGM"
                need_1mphi = True
            elif noisemodel == "MT":
                names += " Matern"
            elif noisemodel == "VA":
                names += " VaryingAnnual"
                need_varying_phi = True
            elif noisemodel == "VSA":
                names += " VaryingSemiAnnual"
                need_varying_phi = True
            elif noisemodel == "AR1":
                names += " ARMA"
                fp.write("AR_p                  1\n")
                fp.write("MA_q                  0\n")

        fp.write(f"NoiseModels           {names.lstrip()}\n")
        if need_1mphi:
            fp.write("GGM_1mphi             6.9e-06\n")
        if need_varying_phi:
            fp.write("phi_varying_fixed     0.9999\n")
        if "fGGM" in noisemodels:
            fp.write("GGM_1mphi             0.02\n")
            fp.write("kappa_fixed           -1.0\n")

        fp.write("seasonalsignal        yes\n")
        fp.write("halfseasonalsignal    yes\n")
        if freq > 0.0:
            fp.write(f"periodicsignals       {freq:f}\n")
        fp.write("estimateoffsets       yes\n")
        fp.write("estimatepostseismic   yes\n")
        fp.write("estimateslowslipevent yes\n")
        fp.write("ScaleFactor           1.0\n")
        fp.write("PhysicalUnit          mm\n")


def create_estimatespectrum_ctl_file(
    ctl_path: Path,
    station: str,
    mom_dir: Path,
    noise_model: str,
) -> None:
    with ctl_path.open("w", encoding="utf-8") as fp:
        fp.write(f"DataFile            {station}.mom\n")
        fp.write(f"DataDirectory       {mom_dir}\n")
        fp.write("interpolate         no\n")
        fp.write(f"NoiseModels         {noise_model}\n")
        fp.write("ScaleFactor         1.0\n")
        fp.write("PhysicalUnit        mm\n")
        fp.write("WindowFunction      Hann\n")


def extract_optional_noise_parameters(ctl_path: Path) -> dict[str, float]:
    values: dict[str, float] = {}
    with ctl_path.open(encoding="utf-8") as fp:
        for line in fp:
            if line.startswith("GGM_1mphi"):
                values["GGM_1mphi"] = float(line.split()[1])
            elif line.startswith("kappa_fixed"):
                values["kappa_fixed"] = float(line.split()[1])
            elif line.startswith("lambda_fixed"):
                values["lambda_fixed"] = float(line.split()[1])
    return values


def create_modelspectrum_ctl_file(
    ctl_path: Path,
    station: str,
    mom_dir: Path,
    results: dict[str, object],
    sampling_period: float,
    number_of_points: int,
    fixed_params: dict[str, float],
) -> None:
    with ctl_path.open("w", encoding="utf-8") as fp:
        fp.write(f"DataFile                {station}.mom\n")
        fp.write(f"DataDirectory           {mom_dir}\n")
        fp.write("ScaleFactor             1.0\n")
        fp.write("PhysicalUnit            mm\n")

        noise_lst = ""
        noises = results["NoiseModel"]
        assert isinstance(noises, dict)
        for noise in noises:
            noise_lst += f" {noise}"

        if "GGM_1mphi" in fixed_params:
            fp.write(f"GGM_1mphi             {fixed_params['GGM_1mphi']:e}\n")
        if "kappa_fixed" in fixed_params:
            fp.write(f"kappa_fixed           {fixed_params['kappa_fixed']:f}\n")
        if "lambda_fixed" in fixed_params:
            fp.write(f"lambda_fixed          {fixed_params['lambda_fixed']:e}\n")

        fp.write(f"NoiseModels            {noise_lst.lstrip()}\n")
        fp.write("AR_p                    1\n")
        fp.write("MA_q                    0\n")
        fp.write("TimeNoiseStart          1000\n")
        fp.write("MonteCarloConfidence    yes\n")
        fp.write("NumberOfSimulations     5000\n")
        fp.write(f"SamplingPeriod          {sampling_period:f}\n")
        fp.write(f"NumberOfPoints          {number_of_points:d}\n")
        fp.write("NumberOfSegments        4\n")
        fp.write("WindowFunction          Hann\n")


def create_modelspectrum_input(
    input_path: Path,
    results: dict[str, object],
    fs: float,
    freq0: str,
    freq1: str,
    fixed_params: dict[str, float],
) -> None:
    noises = results["NoiseModel"]
    assert isinstance(noises, dict)
    sigma = float(results["driving_noise"])
    with input_path.open("w", encoding="utf-8") as fp:
        fp.write(f"{sigma:f}\n{24.0 / fs:f}\n")
        for noise in noises.values():
            assert isinstance(noise, dict)
            fp.write(f"{float(noise['fraction']):f}\n")

        for model, noise in noises.items():
            assert isinstance(noise, dict)
            if model == "GGM":
                if "kappa_fixed" not in fixed_params:
                    fp.write(f"{float(noise['d']):f}\n")
                if "GGM_1mphi" not in fixed_params:
                    fp.write(f"{float(noise['1-phi']):f}\n")
            elif model in {"Powerlaw", "PowerlawApprox"}:
                fp.write(f"{float(noise['d']):f}\n")
            elif model in {"VaryingAnnual", "VaryingSemiAnnual"}:
                fp.write(f"{float(noise['phi']):f}\n")
            elif model == "Matern":
                if "kappa_fixed" not in fixed_params:
                    fp.write(f"{float(noise['d']):f}\n")
                if "lambda_fixed" not in fixed_params:
                    fp.write(f"{float(noise['lambda']):f}\n")
            elif model == "ARMA":
                ar_values = noise["AR"]
                assert isinstance(ar_values, list)
                fp.write(f"{float(ar_values[0]):f}\n")

        fp.write(f"2\n{freq0} {freq1}\n")


def read_sampling_info(mom_path: Path) -> tuple[float, float, float, int]:
    lines = mom_path.read_text(encoding="utf-8").splitlines()
    match = re.search(r"# sampling period (\d+\.?\d*)", lines[0])
    if not match:
        raise ValueError(f"{mom_path} does not have # sampling period")
    sampling_period = float(match.group(1))

    data_lines = [line for line in lines if line and not line.startswith("#")]
    if not data_lines:
        raise ValueError(f"{mom_path} has no data rows")
    mjd0 = float(data_lines[0].split()[0])
    mjd1 = float(data_lines[-1].split()[0])
    number_of_points = int((mjd1 - mjd0) / sampling_period + 1.0e-6)
    return sampling_period, mjd0, mjd1, number_of_points


def read_mom_series(mom_path: Path) -> tuple[list[float], list[float], list[float]]:
    x_values: list[float] = []
    data_values: list[float] = []
    model_values: list[float] = []
    with mom_path.open(encoding="utf-8") as fp:
        for line in fp:
            if not line.strip() or line.startswith("#"):
                continue
            columns = line.split()
            if len(columns) < 3:
                continue
            mjd = float(columns[0])
            x_values.append((mjd - 51544.0) / 365.25 + 2000.0)
            data_values.append(float(columns[1]))
            model_values.append(float(columns[2]))
    return x_values, data_values, model_values


def read_mom_series_with_mjd(mom_path: Path) -> tuple[list[float], list[float], list[float], list[float]]:
    mjd_values: list[float] = []
    x_values: list[float] = []
    data_values: list[float] = []
    model_values: list[float] = []
    with mom_path.open(encoding="utf-8") as fp:
        for line in fp:
            if not line.strip() or line.startswith("#"):
                continue
            columns = line.split()
            if len(columns) < 3:
                continue
            mjd = float(columns[0])
            mjd_values.append(mjd)
            x_values.append((mjd - 51544.0) / 365.25 + 2000.0)
            data_values.append(float(columns[1]))
            model_values.append(float(columns[2]))
    return mjd_values, x_values, data_values, model_values


def read_two_column_file(path: Path) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    with path.open(encoding="utf-8") as fp:
        for line in fp:
            if not line.strip() or line.startswith("#"):
                continue
            columns = line.split()
            if len(columns) < 2:
                continue
            xs.append(float(columns[0]))
            ys.append(float(columns[1]))
    return xs, ys


def read_four_column_file(path: Path) -> tuple[list[float], list[float], list[float]]:
    xs: list[float] = []
    y1: list[float] = []
    y2: list[float] = []
    with path.open(encoding="utf-8") as fp:
        for line in fp:
            if not line.strip() or line.startswith("#"):
                continue
            columns = line.split()
            if len(columns) < 4:
                continue
            xs.append(float(columns[0]))
            y1.append(float(columns[1]))
            y2.append(float(columns[3]))
    return xs, y1, y2


def make_data_plots(station: str, mom_path: Path, figure_dir: Path) -> None:
    years, data_values, model_values = read_mom_series(mom_path)
    residuals = [data - model for data, model in zip(data_values, model_values)]

    figure_dir.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(10, 6))
    plt.plot(years, data_values, ".", markersize=3, label="Data")
    plt.plot(years, model_values, "-", linewidth=1.5, label="Model")
    plt.xlabel("Years")
    plt.ylabel("mm")
    plt.legend()
    plt.tight_layout()
    plt.savefig(figure_dir / f"{station}_data.png", dpi=150)
    plt.close()

    plt.figure(figsize=(10, 4))
    plt.plot(years, residuals, "-", linewidth=1.0)
    plt.xlabel("Years")
    plt.ylabel("Residual (mm)")
    plt.tight_layout()
    plt.savefig(figure_dir / f"{station}_res.png", dpi=150)
    plt.close()


def format_number(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.3f}"
    return str(value)


def extract_signal_lines(estimatetrend_json: dict[str, object]) -> list[str]:
    lines: list[str] = []

    trend = estimatetrend_json.get("trend")
    trend_sigma = estimatetrend_json.get("trend_sigma")
    if isinstance(trend, (int, float)) and isinstance(trend_sigma, (int, float)):
        lines.append(f"trend={trend:.3f} +/- {trend_sigma:.3f}")
    elif isinstance(trend, (int, float)):
        lines.append(f"trend={trend:.3f}")

    preferred_pairs = [
        ("bias", "bias_sigma"),
        ("annual_amplitude", "annual_amplitude_sigma"),
        ("semiannual_amplitude", "semiannual_amplitude_sigma"),
        ("annual_phase", "annual_phase_sigma"),
        ("semiannual_phase", "semiannual_phase_sigma"),
        ("driving_noise", None),
    ]
    seen_keys = {"trend", "trend_sigma"}
    for key, sigma_key in preferred_pairs:
        value = estimatetrend_json.get(key)
        if not isinstance(value, (int, float)):
            continue
        seen_keys.add(key)
        if sigma_key and isinstance(estimatetrend_json.get(sigma_key), (int, float)):
            sigma_value = float(estimatetrend_json[sigma_key])
            lines.append(f"{key}={float(value):.3f} +/- {sigma_value:.3f}")
            seen_keys.add(sigma_key)
        else:
            lines.append(f"{key}={float(value):.3f}")

    harmonic_definitions = [
        ("annual", "365.250"),
        ("halfseasonal", "182.625"),
    ]
    for label, period in harmonic_definitions:
        amp_key = f"amp_{period}"
        pha_key = f"pha_{period}"
        amp_sigma_key = f"{amp_key}_sigma"
        pha_sigma_key = f"{pha_key}_sigma"
        amp_value = estimatetrend_json.get(amp_key)
        pha_value = estimatetrend_json.get(pha_key)
        if isinstance(amp_value, (int, float)):
            if isinstance(estimatetrend_json.get(amp_sigma_key), (int, float)):
                lines.append(
                    f"{label}_amp={float(amp_value):.3f} +/- "
                    f"{float(estimatetrend_json[amp_sigma_key]):.3f}"
                )
            else:
                lines.append(f"{label}_amp={float(amp_value):.3f}")
        if isinstance(pha_value, (int, float)):
            if isinstance(estimatetrend_json.get(pha_sigma_key), (int, float)):
                lines.append(
                    f"{label}_phase={float(pha_value):.3f} +/- "
                    f"{float(estimatetrend_json[pha_sigma_key]):.3f}"
                )
            else:
                lines.append(f"{label}_phase={float(pha_value):.3f}")
        if isinstance(amp_value, (int, float)) or isinstance(pha_value, (int, float)):
            continue

        cos_key = f"cos_{period}"
        sin_key = f"sin_{period}"
        cos_sigma_key = f"{cos_key}_sigma"
        sin_sigma_key = f"{sin_key}_sigma"
        cos_value = estimatetrend_json.get(cos_key)
        sin_value = estimatetrend_json.get(sin_key)
        if not isinstance(cos_value, (int, float)) or not isinstance(sin_value, (int, float)):
            continue

        amplitude = math.sqrt(float(cos_value) ** 2 + float(sin_value) ** 2)
        phase_deg = math.degrees(math.atan2(float(sin_value), float(cos_value)))
        lines.append(f"{label}_amp={amplitude:.3f}")
        lines.append(f"{label}_phase_deg={phase_deg:.3f}")
        lines.append(f"{label}_cos={float(cos_value):.3f}")
        lines.append(f"{label}_sin={float(sin_value):.3f}")

        cos_sigma = estimatetrend_json.get(cos_sigma_key)
        sin_sigma = estimatetrend_json.get(sin_sigma_key)
        if isinstance(cos_sigma, (int, float)):
            lines.append(f"{label}_cos_sigma={float(cos_sigma):.3f}")
        if isinstance(sin_sigma, (int, float)):
            lines.append(f"{label}_sin_sigma={float(sin_sigma):.3f}")

    signal_pattern = re.compile(r"(annual|semi|season|offset|postseismic|slow)", re.IGNORECASE)
    for key, value in estimatetrend_json.items():
        if key in seen_keys or key == "NoiseModel":
            continue
        if signal_pattern.search(key) and isinstance(value, (int, float)):
            lines.append(f"{key}={float(value):.3f}")

    return lines


def extract_noise_lines(estimatetrend_json: dict[str, object]) -> list[str]:
    lines: list[str] = []
    noise_model_fit = estimatetrend_json.get("NoiseModel")
    if not isinstance(noise_model_fit, dict):
        return lines

    for name, params in noise_model_fit.items():
        if not isinstance(params, dict):
            lines.append(f"{name}: {format_report_value(params)}")
            continue
        summary_parts: list[str] = []
        if "fraction" in params:
            summary_parts.append(f"fraction={format_number(params['fraction'])}")
        for key in ("d", "phi", "1-phi", "lambda"):
            if key in params:
                summary_parts.append(f"{key}={format_number(params[key])}")
        if "AR" in params and isinstance(params["AR"], list) and params["AR"]:
            summary_parts.append(f"AR1={format_number(params['AR'][0])}")
        lines.append(f"{name}: " + ", ".join(summary_parts) if summary_parts else f"{name}")
    return lines


def build_model_annotation_lines(estimatetrend_json: dict[str, object]) -> list[str]:
    lines = extract_signal_lines(estimatetrend_json)
    noise_lines = extract_noise_lines(estimatetrend_json)
    if noise_lines:
        lines.extend(noise_lines)
    return lines


def format_model_legend(estimatetrend_json: dict[str, object]) -> str:
    lines = build_model_annotation_lines(estimatetrend_json)
    if not lines:
        return "Model"
    return "Model " + lines[0]


def make_station_component_data_plot(
    marker: str,
    component_results: list[dict[str, object]],
    figure_dir: Path,
) -> None:
    figure_dir.mkdir(parents=True, exist_ok=True)
    ordered_results = sorted(
        component_results,
        key=lambda item: get_component_sort_key(item["station_name"]),
    )
    fig, axes = plt.subplots(len(ordered_results), 1, figsize=(12, 3.8 * len(ordered_results)), sharex=True)
    if len(ordered_results) == 1:
        axes = [axes]

    for axis, result in zip(axes, ordered_results):
        metadata = result["metadata"]
        mom_path = Path(str(metadata["mom_path"]))
        years, data_values, model_values = read_mom_series(mom_path)
        component_label = str(metadata["component_label"])
        axis.plot(years, data_values, ".", markersize=2, label=f"{component_label} data")
        axis.plot(
            years,
            model_values,
            "-",
            linewidth=1.2,
            label=format_model_legend(result["estimatetrend"]),
        )
        axis.set_ylabel("mm")
        axis.set_title(component_label)
        axis.legend(loc="best", fontsize=9)
        annotation_lines = build_model_annotation_lines(result["estimatetrend"])
        if len(annotation_lines) > 1:
            axis.text(
                0.01,
                0.98,
                "\n".join(annotation_lines[1:6]),
                transform=axis.transAxes,
                va="top",
                ha="left",
                fontsize=8,
                bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.7},
            )

    axes[-1].set_xlabel("Years")
    fig.tight_layout()
    fig.savefig(figure_dir / f"{marker}_components_data.png", dpi=150)
    plt.close(fig)
    plt.close()


def make_psd_plot(station: str, work_dir: Path, figure_dir: Path) -> None:
    estimatespectrum_x, estimatespectrum_y = read_two_column_file(work_dir / "estimatespectrum.out")
    modelspectrum_x, modelspectrum_y = read_two_column_file(work_dir / "modelspectrum.out")
    percentiles_x, percentiles_low, percentiles_high = read_four_column_file(
        work_dir / "modelspectrum_percentiles.out"
    )

    seconds_per_year = 31557600.0
    figure_dir.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(6, 6))
    plt.loglog(
        [value * seconds_per_year for value in estimatespectrum_x],
        [value / seconds_per_year for value in estimatespectrum_y],
        ".",
        markersize=4,
        label="Estimate",
    )
    plt.loglog(
        [value * seconds_per_year for value in modelspectrum_x],
        [value / seconds_per_year for value in modelspectrum_y],
        "-",
        linewidth=1.5,
        label="Model",
    )
    plt.loglog(
        [value * seconds_per_year for value in percentiles_x],
        [value / seconds_per_year for value in percentiles_low],
        "--",
        linewidth=1.0,
        label="Percentiles",
    )
    plt.loglog(
        [value * seconds_per_year for value in percentiles_x],
        [value / seconds_per_year for value in percentiles_high],
        "--",
        linewidth=1.0,
    )
    plt.xlabel("Frequency (cpy)")
    plt.ylabel("Power (mm^2/cpy)")
    plt.tight_layout()
    plt.legend()
    plt.savefig(figure_dir / f"{station}_psd.png", dpi=150)
    plt.close()


def make_psd_period_plot(station: str, work_dir: Path, figure_dir: Path) -> None:
    del work_dir
    raise RuntimeError("make_psd_period_plot requires a MOM path; call make_lomb_scargle_period_plot instead.")


def compute_lomb_scargle_periodogram(
    times_days: np.ndarray,
    values_mm: np.ndarray,
    min_period_days: float | None = None,
    max_period_days: float | None = None,
    number_of_samples: int = 600,
) -> tuple[np.ndarray, np.ndarray]:
    if len(times_days) < 5:
        raise ValueError("Not enough samples for Lomb-Scargle plot")

    centered_values = values_mm - np.mean(values_mm)
    times = times_days - times_days.min()

    if min_period_days is None:
        if len(times) > 1:
            min_step = float(np.min(np.diff(np.unique(times_days))))
        else:
            min_step = 1.0
        sampling_period = max(min_step, 1.0)
        min_period_days = max(2.0 * sampling_period, 2.0)
    if max_period_days is None:
        span_days = float(times.max())
        max_period_days = max(min_period_days * 1.5, span_days)

    periods = np.logspace(np.log10(min_period_days), np.log10(max_period_days), number_of_samples)
    angular_frequencies = 2.0 * np.pi / periods
    power = lombscargle(times, centered_values, angular_frequencies, precenter=False, normalize=False)
    amplitudes = 2.0 * np.sqrt(np.maximum(power, 0.0) / len(times))
    return periods, amplitudes


def compute_signal_periodogram(mom_path: Path) -> tuple[np.ndarray, np.ndarray]:
    mjd_values, _years, data_values, _model_values = read_mom_series_with_mjd(mom_path)
    times = np.asarray(mjd_values, dtype=float)
    values = np.asarray(data_values, dtype=float)
    return compute_lomb_scargle_periodogram(times, values)


def compute_residual_periodogram(mom_path: Path) -> tuple[np.ndarray, np.ndarray]:
    mjd_values, _years, data_values, model_values = read_mom_series_with_mjd(mom_path)
    times = np.asarray(mjd_values, dtype=float)
    residuals = np.asarray(data_values, dtype=float) - np.asarray(model_values, dtype=float)
    return compute_lomb_scargle_periodogram(times, residuals)


def make_lomb_scargle_period_plot(
    output_path: Path,
    periods: np.ndarray,
    amplitudes: np.ndarray,
    title: str,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7, 5))
    plt.semilogx(periods, amplitudes, "-", linewidth=1.3, label="Lomb-Scargle")
    plt.xlabel("Period (days)")
    plt.ylabel("Amplitude (mm)")
    plt.title(title)
    plt.tight_layout()
    plt.legend()
    plt.savefig(output_path, dpi=150)
    plt.close()


def make_station_component_psd_plot(
    marker: str,
    component_results: list[dict[str, object]],
    figure_dir: Path,
) -> None:
    seconds_per_year = 31557600.0
    figure_dir.mkdir(parents=True, exist_ok=True)
    ordered_results = sorted(
        component_results,
        key=lambda item: get_component_sort_key(item["station_name"]),
    )
    fig, axes = plt.subplots(len(ordered_results), 1, figsize=(10, 3.8 * len(ordered_results)), sharex=True)
    if len(ordered_results) == 1:
        axes = [axes]

    for axis, result in zip(axes, ordered_results):
        metadata = result["metadata"]
        work_dir = Path(str(metadata["psd_cache_dir"]))
        spectrum_x, spectrum_y = read_two_column_file(work_dir / "estimatespectrum.out")
        model_x, model_y = read_two_column_file(work_dir / "modelspectrum.out")
        percentile_x, percentile_low, percentile_high = read_four_column_file(
            work_dir / "modelspectrum_percentiles.out"
        )
        component_label = str(metadata["component_label"])

        axis.loglog(
            [value * seconds_per_year for value in spectrum_x],
            [value / seconds_per_year for value in spectrum_y],
            ".",
            markersize=3,
            label="Estimate",
        )
        axis.loglog(
            [value * seconds_per_year for value in model_x],
            [value / seconds_per_year for value in model_y],
            "-",
            linewidth=1.2,
            label=format_model_legend(result["estimatetrend"]),
        )
        axis.loglog(
            [value * seconds_per_year for value in percentile_x],
            [value / seconds_per_year for value in percentile_low],
            "--",
            linewidth=1.0,
            label="Percentiles",
        )
        axis.loglog(
            [value * seconds_per_year for value in percentile_x],
            [value / seconds_per_year for value in percentile_high],
            "--",
            linewidth=1.0,
        )
        axis.set_ylabel("Power")
        axis.set_title(component_label)
        axis.legend(loc="best", fontsize=9)
        annotation_lines = build_model_annotation_lines(result["estimatetrend"])
        if len(annotation_lines) > 1:
            axis.text(
                0.01,
                0.98,
                "\n".join(annotation_lines[1:6]),
                transform=axis.transAxes,
                va="top",
                ha="left",
                fontsize=8,
                bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.7},
            )

    axes[-1].set_xlabel("Frequency (cpy)")
    fig.tight_layout()
    fig.savefig(figure_dir / f"{marker}_components_psd.png", dpi=150)
    plt.close(fig)


def make_station_component_lomb_plot(
    marker: str,
    component_results: list[dict[str, object]],
    figure_dir: Path,
    kind: str,
) -> None:
    figure_dir.mkdir(parents=True, exist_ok=True)
    ordered_results = sorted(
        component_results,
        key=lambda item: get_component_sort_key(item["station_name"]),
    )
    fig, axes = plt.subplots(len(ordered_results), 1, figsize=(10, 3.8 * len(ordered_results)), sharex=True)
    if len(ordered_results) == 1:
        axes = [axes]

    for axis, result in zip(axes, ordered_results):
        metadata = result["metadata"]
        source_path = Path(str(metadata["mom_path"]))
        if kind == "signal":
            periods, amplitudes = compute_signal_periodogram(source_path)
            label = "Lomb-Scargle signal"
        else:
            periods, amplitudes = compute_residual_periodogram(source_path)
            label = "Lomb-Scargle residuals"
        component_label = str(metadata["component_label"])

        axis.semilogx(
            periods,
            amplitudes,
            "-",
            linewidth=1.2,
            label=label,
        )
        axis.set_ylabel("Amplitude")
        axis.set_title(component_label)
        axis.legend(loc="best", fontsize=9)
        annotation_lines = build_model_annotation_lines(result["estimatetrend"])
        if len(annotation_lines) > 1:
            axis.text(
                0.01,
                0.98,
                "\n".join(annotation_lines[1:6]),
                transform=axis.transAxes,
                va="top",
                ha="left",
                fontsize=8,
                bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.7},
            )

    axes[-1].set_xlabel("Period (days)")
    fig.tight_layout()
    suffix = "signal" if kind == "signal" else "residuals"
    fig.savefig(figure_dir / f"{marker}_components_lomb_{suffix}_days.png", dpi=150)
    plt.close(fig)


def run_command(command: list[str], cwd: Path, stdout_path: Path | None = None, stdin_path: Path | None = None) -> None:
    stdin_handle = stdin_path.open("r", encoding="utf-8") if stdin_path else None
    stdout_handle = stdout_path.open("w", encoding="utf-8") if stdout_path else subprocess.PIPE
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            stdin=stdin_handle,
            stdout=stdout_handle,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
        )
    finally:
        if stdin_handle:
            stdin_handle.close()
        if stdout_path and hasattr(stdout_handle, "close"):
            stdout_handle.close()

    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(command)}")


def ensure_executable(binary_path: Path) -> None:
    if not binary_path.exists():
        raise FileNotFoundError(f"HECTOR executable does not exist: {binary_path}")
    if not os.access(binary_path, os.X_OK):
        raise RuntimeError(
            f"HECTOR executable is not runnable: {binary_path}. "
            f"Run 'chmod +x {binary_path}' first."
        )


def analyse_station(
    station: str,
    project_dir: Path,
    config: dict[str, dict[str, object]],
    noise_model: str,
    freq: float,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    paths = config["paths"]
    hector_removeoutliers = Path(str(paths["hector_removeoutliers"]))
    hector_estimatetrend = Path(str(paths["hector_estimatetrend"]))
    hector_estimatespectrum = Path(str(paths["hector_estimatespectrum"]))
    hector_modelspectrum = Path(str(Path(str(paths["hector_home"])) / "modelspectrum"))
    for binary_path in (
        hector_removeoutliers,
        hector_estimatetrend,
        hector_estimatespectrum,
        hector_modelspectrum,
    ):
        ensure_executable(binary_path)

    raw_dir = project_dir / str(paths["raw_files_dir"])
    pre_dir = project_dir / str(paths["pre_files_dir"])
    mom_dir = project_dir / str(paths["mom_files_dir"])
    fil_dir = project_dir / str(paths["fil_files_dir"])
    data_figure_dir = fil_dir / "data_figures"
    psd_figure_dir = fil_dir / "psd_figures"

    noisemodels = parse_noisemodels(noise_model)
    input_mom_path = raw_dir / f"{station}.mom"
    if not input_mom_path.exists():
        raise FileNotFoundError(f"Input MOM file does not exist: {input_mom_path}")

    pre_dir.mkdir(parents=True, exist_ok=True)
    mom_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=project_dir, prefix="hector_run_") as temp_dir_name:
        temp_dir = Path(temp_dir_name)

        removeoutliers_ctl = temp_dir / "removeoutliers.ctl"
        create_removeoutliers_ctl_file(removeoutliers_ctl, station, raw_dir, pre_dir, freq)
        run_command(
            [str(hector_removeoutliers)],
            cwd=temp_dir,
            stdout_path=temp_dir / "removeoutliers.out",
        )

        estimatetrend_ctl = temp_dir / "estimatetrend.ctl"
        create_estimatetrend_ctl_file(estimatetrend_ctl, station, pre_dir, mom_dir, noisemodels, freq)
        run_command(
            [str(hector_estimatetrend)],
            cwd=temp_dir,
            stdout_path=temp_dir / "estimatetrend.out",
        )

        estimatetrend_json = json.loads((temp_dir / "estimatetrend.json").read_text(encoding="utf-8"))
        removeoutliers_json = json.loads((temp_dir / "removeoutliers.json").read_text(encoding="utf-8"))

        sampling_period, _mjd0, _mjd1, number_of_points = read_sampling_info(mom_dir / f"{station}.mom")

        estimatespectrum_ctl = temp_dir / "estimatespectrum.ctl"
        create_estimatespectrum_ctl_file(estimatespectrum_ctl, station, mom_dir, noise_model)
        output = subprocess.check_output([str(hector_estimatespectrum), "4"], cwd=temp_dir, text=True)
        estimatespectrum_cols = output.split()
        freq0 = estimatespectrum_cols[-5]
        freq1 = estimatespectrum_cols[-3]

        fixed_params = extract_optional_noise_parameters(estimatetrend_ctl)

        modelspectrum_ctl = temp_dir / "modelspectrum.ctl"
        create_modelspectrum_ctl_file(
            modelspectrum_ctl,
            station,
            mom_dir,
            estimatetrend_json,
            sampling_period,
            number_of_points,
            fixed_params,
        )
        modelspectrum_input = temp_dir / "modelspectrum.txt"
        fs = 1.0 / sampling_period
        create_modelspectrum_input(
            modelspectrum_input,
            estimatetrend_json,
            fs,
            freq0,
            freq1,
            fixed_params,
        )
        run_command(
            [str(hector_modelspectrum)],
            cwd=temp_dir,
            stdin_path=modelspectrum_input,
        )

        make_psd_plot(station, temp_dir, psd_figure_dir)
        make_data_plots(station, mom_dir / f"{station}.mom", data_figure_dir)
        psd_cache_dir = fil_dir / "psd_cache"
        psd_cache_dir.mkdir(parents=True, exist_ok=True)
        station_cache_dir = psd_cache_dir / station
        if station_cache_dir.exists():
            shutil.rmtree(station_cache_dir)
        station_cache_dir.mkdir(parents=True, exist_ok=True)
        for filename in (
            "estimatespectrum.out",
            "modelspectrum.out",
            "modelspectrum_percentiles.out",
        ):
            source = temp_dir / filename
            if source.exists():
                shutil.copy2(source, station_cache_dir / filename)

    metadata = {
        "marker": get_station_marker(station),
        "component_label": get_component_label(station),
        "mom_path": str(mom_dir / f"{station}.mom"),
        "data_plot": str(data_figure_dir / f"{station}_data.png"),
        "residual_plot": str(data_figure_dir / f"{station}_res.png"),
        "psd_plot": str(psd_figure_dir / f"{station}_psd.png"),
        "lomb_signal_plot": str(psd_figure_dir / f"{station}_lomb_signal_days.png"),
        "lomb_residuals_plot": str(psd_figure_dir / f"{station}_lomb_residuals_days.png"),
        "psd_cache_dir": str((fil_dir / "psd_cache" / station)),
    }
    signal_periods, signal_amplitudes = compute_signal_periodogram(mom_dir / f"{station}.mom")
    make_lomb_scargle_period_plot(
        psd_figure_dir / f"{station}_lomb_signal_days.png",
        signal_periods,
        signal_amplitudes,
        f"{station} signal",
    )
    residual_periods, residual_amplitudes = compute_residual_periodogram(mom_dir / f"{station}.mom")
    make_lomb_scargle_period_plot(
        psd_figure_dir / f"{station}_lomb_residuals_days.png",
        residual_periods,
        residual_amplitudes,
        f"{station} residuals",
    )
    return estimatetrend_json, removeoutliers_json, metadata


def format_report_value(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value)


def write_station_summary_report(
    marker: str,
    report_dir: Path,
    noise_model: str,
    freq: float,
    component_results: list[dict[str, object]],
) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{marker}_summary.md"
    lines = [
        f"# Station Summary: {marker}",
        "",
        f"- Noise model: `{noise_model}`",
        f"- Extra frequency: `{freq}`",
        f"- Components analysed: `{len(component_results)}`",
        "",
    ]
    for result in component_results:
        metadata = result["metadata"]
        est_json = result["estimatetrend"]
        rem_json = result["removeoutliers"]
        lines.extend(
            [
                f"## {result['station_name']}",
                "",
                f"- Component: `{metadata['component_label']}`",
                f"- MOM file: `{metadata['mom_path']}`",
                f"- Data plot: `{metadata['data_plot']}`",
                f"- Residual plot: `{metadata['residual_plot']}`",
                f"- PSD plot: `{metadata['psd_plot']}`",
            ]
        )

        trend_keys = ("trend", "trend_sigma", "bias", "driving_noise")
        available_est_keys = [key for key in trend_keys if key in est_json]
        if available_est_keys:
            lines.append("")
            lines.append("Estimated trend metrics:")
            for key in available_est_keys:
                lines.append(f"- `{key}`: `{format_report_value(est_json[key])}`")

        remove_keys = ("N", "outliers", "NumberOfOutliers")
        available_rem_keys = [key for key in remove_keys if key in rem_json]
        if available_rem_keys:
            lines.append("")
            lines.append("Outlier summary:")
            for key in available_rem_keys:
                lines.append(f"- `{key}`: `{format_report_value(rem_json[key])}`")

        if "NoiseModel" in est_json:
            lines.append("")
            lines.append("Noise model fit:")
            for noise_line in extract_noise_lines(est_json):
                lines.append(f"- `{noise_line}`")

        signal_lines = extract_signal_lines(est_json)
        if signal_lines:
            lines.append("")
            lines.append("Fitted signal terms:")
            for signal_line in signal_lines:
                lines.append(f"- `{signal_line}`")

        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")


def analyse_project(
    project_name: str,
    noise_model: str,
    station: str,
    freq: float,
) -> tuple[Path, int]:
    project_dir, config = load_project_config(project_name)
    if not noise_model:
        noise_model_value = config["analysis"].get("noise_model")
        if not isinstance(noise_model_value, str) or not noise_model_value:
            raise ValueError("No noise model provided and analysis.noise_model is missing in config.")
        noise_model = noise_model_value
    raw_dir = project_dir / str(config["paths"]["raw_files_dir"])
    mom_files = collect_station_files(raw_dir, station)

    estimatetrend_results: dict[str, object] = {}
    removeoutliers_results: dict[str, object] = {}
    grouped_results: dict[str, list[dict[str, object]]] = {}
    for mom_file in mom_files:
        station_name = mom_file.stem
        est_json, rem_json, metadata = analyse_station(
            station_name, project_dir, config, noise_model, freq
        )
        estimatetrend_results[station_name] = est_json
        removeoutliers_results[station_name] = rem_json
        marker = str(metadata["marker"])
        grouped_results.setdefault(marker, []).append(
            {
                "station_name": station_name,
                "estimatetrend": est_json,
                "removeoutliers": rem_json,
                "metadata": metadata,
            }
        )

    mom_dir = project_dir / str(config["paths"]["mom_files_dir"])
    fil_dir = project_dir / str(config["paths"]["fil_files_dir"])
    (mom_dir / "hector_estimatetrend.json").write_text(
        json.dumps(estimatetrend_results, indent=2) + "\n",
        encoding="utf-8",
    )
    (mom_dir / "hector_removeoutliers.json").write_text(
        json.dumps(removeoutliers_results, indent=2) + "\n",
        encoding="utf-8",
    )

    data_figure_dir = fil_dir / "data_figures"
    psd_figure_dir = fil_dir / "psd_figures"
    report_dir = fil_dir / "reports"
    for marker, component_results in grouped_results.items():
        sorted_results = sorted(component_results, key=lambda item: item["station_name"])
        if len(sorted_results) > 1:
            make_station_component_data_plot(marker, sorted_results, data_figure_dir)
            if all(Path(str(item["metadata"]["psd_cache_dir"])).exists() for item in sorted_results):
                make_station_component_psd_plot(marker, sorted_results, psd_figure_dir)
                make_station_component_lomb_plot(marker, sorted_results, psd_figure_dir, "signal")
                make_station_component_lomb_plot(marker, sorted_results, psd_figure_dir, "residuals")
        write_station_summary_report(marker, report_dir, noise_model, freq, sorted_results)

    return mom_dir, len(mom_files)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        output_dir, station_count = analyse_project(
            project_name=args.project_name,
            noise_model=args.noise_model,
            station=args.station,
            freq=args.freq,
        )
    except (FileNotFoundError, ValueError, KeyError, RuntimeError) as exc:
        parser.error(str(exc))

    print(f"Analysed {station_count} station file(s); results written under {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
