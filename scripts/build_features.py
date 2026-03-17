import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.schemas.scoring import ScoreEstimateRequest
from backend.services.scoring import default_maintenance_gap_days, estimate_scores


AIS_REQUIRED_COLUMNS = ["mmsi", "timestamp", "latitude", "longitude", "is_low_speed"]
ENV_REQUIRED_COLUMNS = ["timestamp", "latitude", "longitude", "sst"]
OPTIONAL_ENV_COLUMNS = ["chlorophyll_a", "salinity", "current_u", "current_v"]
REFERENCE_PORTS_PATH = PROJECT_ROOT / "data" / "reference" / "singapore_reference_sites.csv"
PORT_PROXIMITY_KM = 10.0
MAX_SEGMENT_HOURS = 6.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build vessel-level features from AIS and environment data."
    )
    parser.add_argument("--ais", required=True, help="Path to cleaned AIS CSV.")
    parser.add_argument("--env", required=False, help="Path to processed environment CSV.")
    parser.add_argument(
        "--output",
        default="data/processed/vessel_features.csv",
        help="Path to feature CSV output.",
    )
    parser.add_argument(
        "--maintenance-overrides",
        required=False,
        help="Optional CSV with mmsi,maintenance_gap_days overrides.",
    )
    parser.add_argument(
        "--maintenance-gap-days-default",
        type=float,
        default=None,
        help="Default maintenance gap days when no override exists. Falls back to science calibration config.",
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
    ais["mmsi"] = ais["mmsi"].astype(str)
    ais["timestamp"] = pd.to_datetime(ais["timestamp"], utc=True, errors="coerce")
    ais["latitude"] = pd.to_numeric(ais["latitude"], errors="coerce")
    ais["longitude"] = pd.to_numeric(ais["longitude"], errors="coerce")
    ais["is_low_speed"] = ais["is_low_speed"].astype(str).str.lower().eq("true")
    if "nav_status" in ais.columns:
        ais["nav_status"] = pd.to_numeric(ais["nav_status"], errors="coerce")
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
    for column in OPTIONAL_ENV_COLUMNS:
        if column in env.columns:
            env[column] = pd.to_numeric(env[column], errors="coerce")
    env = env.dropna(subset=["timestamp", "latitude", "longitude", "sst"])
    env["date"] = env["timestamp"].dt.floor("D")
    return env


def load_reference_ports() -> pd.DataFrame:
    if not REFERENCE_PORTS_PATH.exists():
        return pd.DataFrame(columns=["latitude", "longitude"])
    reference = load_csv(REFERENCE_PORTS_PATH)
    reference = reference.loc[reference["site_type"] == "port"].copy()
    reference["latitude"] = pd.to_numeric(reference["latitude"], errors="coerce")
    reference["longitude"] = pd.to_numeric(reference["longitude"], errors="coerce")
    return reference.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)


def load_maintenance_overrides(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame(columns=["mmsi", "maintenance_gap_days"])
    overrides = load_csv(path)
    if "mmsi" not in overrides.columns or "maintenance_gap_days" not in overrides.columns:
        raise ValueError("Maintenance overrides must include 'mmsi' and 'maintenance_gap_days'")
    overrides["mmsi"] = overrides["mmsi"].astype(str)
    overrides["maintenance_gap_days"] = pd.to_numeric(
        overrides["maintenance_gap_days"], errors="coerce"
    )
    return overrides.dropna(subset=["maintenance_gap_days"])[["mmsi", "maintenance_gap_days"]]


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
            for column in OPTIONAL_ENV_COLUMNS:
                day[column] = np.nan
            matched_frames.append(day)
            continue

        env_lat = env_day["latitude"].to_numpy()
        env_lon = env_day["longitude"].to_numpy()
        env_sst = env_day["sst"].to_numpy()
        env_optional = {
            column: (
                env_day[column].to_numpy()
                if column in env_day.columns
                else np.full(len(env_day), np.nan)
            )
            for column in OPTIONAL_ENV_COLUMNS
        }

        matched_sst: list[float] = []
        matched_optional = {column: [] for column in OPTIONAL_ENV_COLUMNS}
        for row in day.itertuples(index=False):
            distance = (env_lat - row.latitude) ** 2 + (env_lon - row.longitude) ** 2
            nearest_index = int(distance.argmin())
            matched_sst.append(float(env_sst[nearest_index]))
            for column in OPTIONAL_ENV_COLUMNS:
                values = env_optional[column]
                matched_optional[column].append(
                    float(values[nearest_index]) if len(values) else np.nan
                )

        day["sst"] = matched_sst
        for column in OPTIONAL_ENV_COLUMNS:
            day[column] = matched_optional[column]
        matched_frames.append(day)

    return pd.concat(matched_frames, ignore_index=True)


def add_segment_hours(ais: pd.DataFrame) -> pd.DataFrame:
    enriched = ais.sort_values(["mmsi", "timestamp"]).copy()
    next_timestamp = enriched.groupby("mmsi")["timestamp"].shift(-1)
    delta_hours = (next_timestamp - enriched["timestamp"]).dt.total_seconds() / 3600
    median_hours = (
        delta_hours.groupby(enriched["mmsi"])
        .transform(lambda values: values.dropna().clip(lower=0, upper=MAX_SEGMENT_HOURS).median())
        .fillna(0.0)
    )
    enriched["segment_hours"] = delta_hours.fillna(median_hours).clip(lower=0.0, upper=MAX_SEGMENT_HOURS)
    return enriched


def mark_port_proximity(ais: pd.DataFrame, ports: pd.DataFrame) -> pd.DataFrame:
    marked = ais.copy()
    if ports.empty:
        marked["is_near_port"] = False
        return marked

    earth_radius_km = 6371.0
    lat = np.radians(marked["latitude"].to_numpy())
    lon = np.radians(marked["longitude"].to_numpy())
    min_distance = np.full(len(marked), np.inf)

    for row in ports.itertuples(index=False):
        port_lat = np.radians(float(row.latitude))
        port_lon = np.radians(float(row.longitude))
        delta_lat = lat - port_lat
        delta_lon = lon - port_lon
        hav = (
            np.sin(delta_lat / 2.0) ** 2
            + np.cos(lat) * np.cos(port_lat) * np.sin(delta_lon / 2.0) ** 2
        )
        distance = 2.0 * earth_radius_km * np.arctan2(np.sqrt(hav), np.sqrt(1.0 - hav))
        min_distance = np.minimum(min_distance, distance)

    marked["is_near_port"] = min_distance <= PORT_PROXIMITY_KM
    return marked


def legacy_fpi_proxy(features: pd.DataFrame) -> pd.Series:
    return (
        features["low_speed_ratio"].fillna(0) * 0.6
        + (features["track_duration_hours"].fillna(0) > 6).astype(float) * 0.4
    )


def legacy_ecp_proxy(features: pd.DataFrame) -> pd.Series:
    warm_exposure = (features["mean_sst"] >= 28).astype(float)
    bio_exposure = features["mean_chlorophyll_a"].fillna(0).ge(0.5).astype(float)
    return features["fpi_proxy_legacy"] * (1 + 0.2 * warm_exposure + 0.2 * bio_exposure)


def estimate_port_visits(vessel_points: pd.DataFrame) -> int:
    near_port = vessel_points["is_near_port"].fillna(False).astype(bool)
    entries = near_port & ~near_port.shift(fill_value=False)
    return int(entries.sum())


def summarize_behavior_exposure(ais_enriched: pd.DataFrame) -> pd.DataFrame:
    grouped_rows: list[dict[str, object]] = []
    for mmsi, vessel_points in ais_enriched.groupby("mmsi", sort=False):
        vessel_points = vessel_points.sort_values("timestamp").copy()
        nav_status = pd.to_numeric(vessel_points.get("nav_status"), errors="coerce")
        anchor_mask = nav_status.eq(1) if nav_status is not None else pd.Series(False, index=vessel_points.index)
        moored_mask = nav_status.eq(5) if nav_status is not None else pd.Series(False, index=vessel_points.index)

        grouped_rows.append(
            {
                "mmsi": mmsi,
                "ping_count": int(len(vessel_points)),
                "track_start": vessel_points["timestamp"].min(),
                "track_end": vessel_points["timestamp"].max(),
                "mean_latitude": vessel_points["latitude"].mean(),
                "mean_longitude": vessel_points["longitude"].mean(),
                "low_speed_ratio": vessel_points["is_low_speed"].mean(),
                "mean_sst": vessel_points["sst"].mean(),
                "mean_chlorophyll_a": vessel_points["chlorophyll_a"].mean(),
                "mean_salinity": vessel_points["salinity"].mean(),
                "mean_current_u": vessel_points["current_u"].mean(),
                "mean_current_v": vessel_points["current_v"].mean(),
                "mean_current_speed": np.sqrt(
                    vessel_points["current_u"].fillna(0) ** 2 + vessel_points["current_v"].fillna(0) ** 2
                ).mean(),
                "current_speed_std": np.sqrt(
                    vessel_points["current_u"].fillna(0) ** 2 + vessel_points["current_v"].fillna(0) ** 2
                ).std(),
                "low_speed_hours": vessel_points.loc[vessel_points["is_low_speed"], "segment_hours"].sum(),
                "anchor_hours": vessel_points.loc[anchor_mask, "segment_hours"].sum(),
                "dwell_hours": vessel_points.loc[moored_mask, "segment_hours"].sum(),
                "port_proximity_hours": vessel_points.loc[vessel_points["is_near_port"], "segment_hours"].sum(),
                "port_visits": estimate_port_visits(vessel_points),
            }
        )

    features = pd.DataFrame(grouped_rows)
    features["track_duration_hours"] = (
        (features["track_end"] - features["track_start"]).dt.total_seconds() / 3600
    )
    return features


def apply_scientific_scores(
    features: pd.DataFrame,
    maintenance_overrides: pd.DataFrame | None = None,
    maintenance_gap_days_default: float | None = None,
) -> pd.DataFrame:
    scored = features.copy()
    scored["fpi_proxy_legacy"] = legacy_fpi_proxy(scored).round(4)
    scored["ecp_proxy_legacy"] = legacy_ecp_proxy(scored).round(4)
    default_gap = (
        float(maintenance_gap_days_default)
        if maintenance_gap_days_default is not None
        else default_maintenance_gap_days()
    )

    if maintenance_overrides is not None and not maintenance_overrides.empty:
        scored = scored.merge(maintenance_overrides, on="mmsi", how="left")
    else:
        scored["maintenance_gap_days"] = np.nan

    scored["maintenance_gap_days_used"] = scored["maintenance_gap_days"].fillna(default_gap)
    scored["maintenance_gap_source"] = np.where(
        scored["maintenance_gap_days"].notna(),
        "override",
        "calibrated_default",
    )

    results: list[dict[str, float | str | None]] = []
    for row in scored.itertuples(index=False):
        payload = ScoreEstimateRequest(
            vessel_id=str(row.mmsi),
            dwell_hours=float(row.dwell_hours or 0.0),
            anchor_hours=float(row.anchor_hours or 0.0),
            low_speed_hours=float(row.low_speed_hours or 0.0),
            port_proximity_hours=float(row.port_proximity_hours or 0.0),
            port_visits=int(row.port_visits or 0),
            maintenance_gap_days=float(row.maintenance_gap_days_used or default_gap),
            mean_sst=float(row.mean_sst) if pd.notna(row.mean_sst) else None,
            mean_salinity=float(row.mean_salinity) if pd.notna(row.mean_salinity) else None,
            mean_chlorophyll_a=float(row.mean_chlorophyll_a) if pd.notna(row.mean_chlorophyll_a) else None,
            mean_current_u=float(row.mean_current_u) if pd.notna(row.mean_current_u) else None,
            mean_current_v=float(row.mean_current_v) if pd.notna(row.mean_current_v) else None,
        )
        result = estimate_scores(payload)
        results.append(
            {
                "behavior_score": result.components.behavior_score,
                "stay_probability_score": result.components.stay_probability_score,
                "port_anchorage_score": result.components.port_anchorage_score,
                "temperature_score": result.components.temperature_score,
                "salinity_score": result.components.salinity_score,
                "physiology_score": result.components.physiology_score,
                "productivity_score": result.components.productivity_score,
                "hydrodynamic_score": result.components.hydrodynamic_score,
                "environment_score": result.components.environment_score,
                "environment_multiplier": result.components.environment_multiplier,
                "maintenance_score": result.components.maintenance_score,
                "maintenance_multiplier": result.components.maintenance_multiplier,
                "persistent_exposure_score": result.components.persistent_exposure_score,
                "carbon_penalty_multiplier": result.components.carbon_penalty_multiplier,
                "current_speed": result.components.current_speed,
                "fpi_proxy": result.fpi_score,
                "ecp_proxy": result.ecp_score,
                "recommendation": result.recommendation,
            }
        )

    result_frame = pd.DataFrame(results)
    return pd.concat([scored.reset_index(drop=True), result_frame], axis=1)


def build_vessel_features(ais: pd.DataFrame, env: pd.DataFrame | None) -> pd.DataFrame:
    return build_vessel_features_with_scoring(ais, env)


def build_vessel_features_with_scoring(
    ais: pd.DataFrame,
    env: pd.DataFrame | None,
    maintenance_overrides: pd.DataFrame | None = None,
    maintenance_gap_days_default: float | None = None,
) -> pd.DataFrame:
    ais_enriched = attach_environment(ais, env) if env is not None and not env.empty else ais.copy()
    for column in ["sst", *OPTIONAL_ENV_COLUMNS]:
        if column not in ais_enriched.columns:
            ais_enriched[column] = np.nan
    ais_enriched = add_segment_hours(ais_enriched)
    ais_enriched = mark_port_proximity(ais_enriched, load_reference_ports())
    features = summarize_behavior_exposure(ais_enriched)
    return apply_scientific_scores(
        features,
        maintenance_overrides=maintenance_overrides,
        maintenance_gap_days_default=maintenance_gap_days_default,
    )


def save_output(dataframe: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(path, index=False)


def main() -> None:
    args = parse_args()
    ais = prepare_ais(load_csv(Path(args.ais)))
    env = prepare_env(load_csv(Path(args.env))) if args.env else None
    overrides = load_maintenance_overrides(Path(args.maintenance_overrides)) if args.maintenance_overrides else None
    features = build_vessel_features_with_scoring(
        ais,
        env,
        maintenance_overrides=overrides,
        maintenance_gap_days_default=args.maintenance_gap_days_default,
    )
    save_output(features, Path(args.output))

    print(f"Vessels summarized: {len(features)}")
    print(f"Output written to: {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
