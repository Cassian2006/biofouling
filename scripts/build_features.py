import argparse
from pathlib import Path

import numpy as np
import pandas as pd


AIS_REQUIRED_COLUMNS = ["mmsi", "timestamp", "latitude", "longitude", "is_low_speed"]
ENV_REQUIRED_COLUMNS = ["timestamp", "latitude", "longitude", "sst"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build first-phase vessel-level features from AIS and environment data."
    )
    parser.add_argument("--ais", required=True, help="Path to cleaned AIS CSV.")
    parser.add_argument("--env", required=False, help="Path to processed environment CSV.")
    parser.add_argument(
        "--output",
        default="data/processed/vessel_features.csv",
        help="Path to feature CSV output.",
    )
    return parser.parse_args()


def validate_columns(dataframe: pd.DataFrame, required_columns: list[str], label: str) -> None:
    missing = [column for column in required_columns if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Missing required {label} columns: {', '.join(missing)}")


def load_csv(path: Path) -> pd.DataFrame:
    dataframe = pd.read_csv(path)
    dataframe.columns = [column.strip().lower() for column in dataframe.columns]
    return dataframe


def prepare_ais(dataframe: pd.DataFrame) -> pd.DataFrame:
    ais = dataframe.copy()
    validate_columns(ais, AIS_REQUIRED_COLUMNS, "AIS")
    ais["timestamp"] = pd.to_datetime(ais["timestamp"], utc=True, errors="coerce")
    ais["latitude"] = pd.to_numeric(ais["latitude"], errors="coerce")
    ais["longitude"] = pd.to_numeric(ais["longitude"], errors="coerce")
    ais["is_low_speed"] = ais["is_low_speed"].astype(str).str.lower().eq("true")
    ais = ais.dropna(subset=["timestamp", "latitude", "longitude"])
    ais["date"] = ais["timestamp"].dt.floor("D")
    return ais


def prepare_env(dataframe: pd.DataFrame) -> pd.DataFrame:
    env = dataframe.copy()
    validate_columns(env, ENV_REQUIRED_COLUMNS, "environment")
    env["timestamp"] = pd.to_datetime(env["timestamp"], utc=True, errors="coerce")
    env["latitude"] = pd.to_numeric(env["latitude"], errors="coerce")
    env["longitude"] = pd.to_numeric(env["longitude"], errors="coerce")
    env["sst"] = pd.to_numeric(env["sst"], errors="coerce")
    for column in ["salinity", "current_u", "current_v", "chlorophyll_a"]:
        if column in env.columns:
            env[column] = pd.to_numeric(env[column], errors="coerce")
    env = env.dropna(subset=["timestamp", "latitude", "longitude", "sst"])
    env["date"] = env["timestamp"].dt.floor("D")
    return env


def attach_environment(ais: pd.DataFrame, env: pd.DataFrame) -> pd.DataFrame:
    env_indexed = {
        date: frame.reset_index(drop=True)
        for date, frame in env.groupby("date", sort=False)
    }

    matched_frames: list[pd.DataFrame] = []
    for date, ais_day in ais.groupby("date", sort=False):
        env_day = env_indexed.get(date)
        day = ais_day.copy()
        if env_day is None or env_day.empty:
            day["sst"] = np.nan
            day["chlorophyll_a"] = np.nan
            matched_frames.append(day)
            continue

        env_lat = env_day["latitude"].to_numpy()
        env_lon = env_day["longitude"].to_numpy()
        env_sst = env_day["sst"].to_numpy()
        env_chl = (
            env_day["chlorophyll_a"].to_numpy()
            if "chlorophyll_a" in env_day.columns
            else np.full(len(env_day), np.nan)
        )

        matched_sst: list[float] = []
        matched_chl: list[float] = []
        for row in day.itertuples(index=False):
            distance = (env_lat - row.latitude) ** 2 + (env_lon - row.longitude) ** 2
            nearest_index = int(distance.argmin())
            matched_sst.append(float(env_sst[nearest_index]))
            matched_chl.append(float(env_chl[nearest_index]) if len(env_chl) else np.nan)

        day["sst"] = matched_sst
        day["chlorophyll_a"] = matched_chl
        matched_frames.append(day)

    return pd.concat(matched_frames, ignore_index=True)


def build_vessel_features(ais: pd.DataFrame, env: pd.DataFrame | None) -> pd.DataFrame:
    ais_enriched = attach_environment(ais, env) if env is not None and not env.empty else ais.copy()
    features = (
        ais_enriched.groupby("mmsi", as_index=False)
        .agg(
            ping_count=("timestamp", "size"),
            track_start=("timestamp", "min"),
            track_end=("timestamp", "max"),
            mean_latitude=("latitude", "mean"),
            mean_longitude=("longitude", "mean"),
            low_speed_ratio=("is_low_speed", "mean"),
            mean_sst=("sst", "mean"),
            mean_chlorophyll_a=("chlorophyll_a", "mean"),
        )
        .copy()
    )
    features["track_duration_hours"] = (
        (features["track_end"] - features["track_start"]).dt.total_seconds() / 3600
    )
    features["fpi_proxy"] = (
        features["low_speed_ratio"].fillna(0) * 0.6
        + (features["track_duration_hours"].fillna(0) > 6).astype(float) * 0.4
    )

    if env is not None and not env.empty:
        warm_exposure = (features["mean_sst"] >= 28).astype(float)
        bio_exposure = features["mean_chlorophyll_a"].fillna(0).ge(0.5).astype(float)
        features["ecp_proxy"] = (
            features["fpi_proxy"] * (1 + 0.2 * warm_exposure + 0.2 * bio_exposure)
        )
    else:
        features["mean_sst"] = None
        features["mean_chlorophyll_a"] = None
        features["ecp_proxy"] = features["fpi_proxy"]

    features["recommendation"] = features["fpi_proxy"].apply(recommend_action)
    return features


def recommend_action(score: float) -> str:
    if score >= 0.7:
        return "Prioritize cleaning assessment"
    if score >= 0.4:
        return "Monitor exposure trend"
    return "Low immediate concern"


def save_output(dataframe: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(path, index=False)


def main() -> None:
    args = parse_args()
    ais = prepare_ais(load_csv(Path(args.ais)))
    env = prepare_env(load_csv(Path(args.env))) if args.env else None
    features = build_vessel_features(ais, env)
    save_output(features, Path(args.output))

    print(f"Vessels summarized: {len(features)}")
    print(f"Output written to: {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
