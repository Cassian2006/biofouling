from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scripts.build_features import (
        OPTIONAL_ENV_COLUMNS,
        attach_environment,
        load_csv,
        prepare_ais,
        prepare_env,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from build_features import (  # type: ignore
        OPTIONAL_ENV_COLUMNS,
        attach_environment,
        load_csv,
        prepare_ais,
        prepare_env,
    )


WINDOW_BASE_FEATURES = [
    "ping_count",
    "coverage_ratio",
    "mean_sog",
    "max_sog",
    "low_speed_ratio",
    "mean_sst",
    "mean_chlorophyll_a",
    "mean_salinity",
    "mean_current_u",
    "mean_current_v",
]


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def load_prepared_inputs(ais_path: Path, env_path: Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    ais = prepare_ais(load_csv(ais_path))
    env = prepare_env(load_csv(env_path)) if env_path else None
    return ais, env


def assign_risk_label(score: float) -> str:
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


def build_window_feature_frame(
    ais: pd.DataFrame,
    env: pd.DataFrame | None = None,
    *,
    window_hours: int = 6,
    min_pings: int = 4,
) -> pd.DataFrame:
    ais_prepared = prepare_ais(ais.copy())
    env_prepared = prepare_env(env.copy()) if env is not None and not env.empty else None
    ais_enriched = (
        attach_environment(ais_prepared, env_prepared)
        if env_prepared is not None and not env_prepared.empty
        else ais_prepared.copy()
    )

    if "sog" in ais_enriched.columns:
        ais_enriched["sog"] = pd.to_numeric(ais_enriched["sog"], errors="coerce")
    else:
        ais_enriched["sog"] = np.nan

    for column in OPTIONAL_ENV_COLUMNS + ["sst"]:
        if column not in ais_enriched.columns:
            ais_enriched[column] = np.nan

    ais_enriched["window_start"] = ais_enriched["timestamp"].dt.floor(f"{window_hours}h")

    window_features = (
        ais_enriched.groupby(["mmsi", "window_start"], as_index=False)
        .agg(
            ping_count=("timestamp", "size"),
            observed_start=("timestamp", "min"),
            observed_end=("timestamp", "max"),
            mean_sog=("sog", "mean"),
            max_sog=("sog", "max"),
            low_speed_ratio=("is_low_speed", "mean"),
            mean_latitude=("latitude", "mean"),
            mean_longitude=("longitude", "mean"),
            mean_sst=("sst", "mean"),
            mean_chlorophyll_a=("chlorophyll_a", "mean"),
            mean_salinity=("salinity", "mean"),
            mean_current_u=("current_u", "mean"),
            mean_current_v=("current_v", "mean"),
        )
        .copy()
    )

    window_features["window_end"] = window_features["window_start"] + pd.to_timedelta(
        window_hours, unit="h"
    )
    window_features["observed_hours"] = (
        window_features["observed_end"] - window_features["observed_start"]
    ).dt.total_seconds() / 3600
    window_features["coverage_ratio"] = (
        window_features["observed_hours"].fillna(0).apply(lambda value: clamp(value / window_hours))
    )
    window_features["fpi_proxy"] = (
        window_features["low_speed_ratio"].fillna(0) * 0.65
        + window_features["coverage_ratio"] * 0.35
    ).round(4)
    window_features["risk_label"] = window_features["fpi_proxy"].apply(assign_risk_label)
    window_features["window_hours"] = window_hours

    window_features = window_features.loc[window_features["ping_count"] >= min_pings].copy()
    window_features = window_features.sort_values(["mmsi", "window_start"]).reset_index(drop=True)
    return window_features


def build_supervised_sequences(
    window_features: pd.DataFrame,
    *,
    history_windows: int = 8,
    horizon_windows: int = 1,
    feature_columns: list[str] | None = None,
) -> pd.DataFrame:
    if window_features.empty:
        return pd.DataFrame()

    feature_columns = feature_columns or WINDOW_BASE_FEATURES + ["fpi_proxy"]
    data = window_features.sort_values(["mmsi", "window_start"]).reset_index(drop=True)
    window_hours = int(data["window_hours"].iloc[0])
    expected_delta = pd.to_timedelta(window_hours, unit="h")

    records: list[dict[str, object]] = []
    for mmsi, vessel_frame in data.groupby("mmsi", sort=False):
        vessel_frame = vessel_frame.reset_index(drop=True)
        required_windows = history_windows + horizon_windows
        if len(vessel_frame) < required_windows:
            continue

        for start_index in range(len(vessel_frame) - required_windows + 1):
            history_frame = vessel_frame.iloc[start_index : start_index + history_windows]
            target_row = vessel_frame.iloc[start_index + history_windows + horizon_windows - 1]
            contiguous_frame = vessel_frame.iloc[
                start_index : start_index + history_windows + horizon_windows
            ]

            diffs = contiguous_frame["window_start"].diff().dropna()
            if not diffs.eq(expected_delta).all():
                continue

            record: dict[str, object] = {
                "sequence_id": f"{mmsi}_{history_frame.iloc[0]['window_start'].isoformat()}",
                "mmsi": str(mmsi),
                "history_start": history_frame.iloc[0]["window_start"].isoformat(),
                "history_end": history_frame.iloc[-1]["window_end"].isoformat(),
                "target_window_start": target_row["window_start"].isoformat(),
                "target_window_end": target_row["window_end"].isoformat(),
                "history_windows": history_windows,
                "horizon_windows": horizon_windows,
                "window_hours": window_hours,
                "target_fpi_proxy": float(target_row["fpi_proxy"]),
                "target_risk_label": str(target_row["risk_label"]),
            }
            for step_index, (_, row) in enumerate(history_frame.iterrows()):
                for column in feature_columns:
                    value = row.get(column, np.nan)
                    record[f"t{step_index:02d}_{column}"] = (
                        float(value) if pd.notna(value) else np.nan
                    )
            records.append(record)

    return pd.DataFrame.from_records(records)


def build_latest_inference_sequences(
    window_features: pd.DataFrame,
    *,
    history_windows: int = 8,
    feature_columns: list[str] | None = None,
) -> pd.DataFrame:
    if window_features.empty:
        return pd.DataFrame()

    feature_columns = feature_columns or WINDOW_BASE_FEATURES + ["fpi_proxy"]
    data = window_features.sort_values(["mmsi", "window_start"]).reset_index(drop=True)
    window_hours = int(data["window_hours"].iloc[0])
    expected_delta = pd.to_timedelta(window_hours, unit="h")

    records: list[dict[str, object]] = []
    for mmsi, vessel_frame in data.groupby("mmsi", sort=False):
        vessel_frame = vessel_frame.reset_index(drop=True)
        if len(vessel_frame) < history_windows:
            continue

        for end_index in range(len(vessel_frame), history_windows - 1, -1):
            history_frame = vessel_frame.iloc[end_index - history_windows : end_index]
            diffs = history_frame["window_start"].diff().dropna()
            if not diffs.eq(expected_delta).all():
                continue

            forecast_start = history_frame.iloc[-1]["window_end"]
            forecast_end = forecast_start + pd.to_timedelta(window_hours, unit="h")
            record: dict[str, object] = {
                "sequence_id": f"{mmsi}_{history_frame.iloc[0]['window_start'].isoformat()}_forecast",
                "mmsi": str(mmsi),
                "history_start": history_frame.iloc[0]["window_start"].isoformat(),
                "history_end": history_frame.iloc[-1]["window_end"].isoformat(),
                "forecast_window_start": forecast_start.isoformat(),
                "forecast_window_end": forecast_end.isoformat(),
                "history_windows": history_windows,
                "window_hours": window_hours,
            }
            for step_index, (_, row) in enumerate(history_frame.iterrows()):
                for column in feature_columns:
                    value = row.get(column, np.nan)
                    record[f"t{step_index:02d}_{column}"] = (
                        float(value) if pd.notna(value) else np.nan
                    )
            records.append(record)
            break

    return pd.DataFrame.from_records(records)


def sequence_feature_columns(dataset: pd.DataFrame) -> list[str]:
    return [
        column
        for column in dataset.columns
        if len(column) > 3 and column.startswith("t") and column[1:3].isdigit()
    ]
