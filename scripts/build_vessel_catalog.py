import argparse
from pathlib import Path

import pandas as pd


REQUIRED_AIS_COLUMNS = ["mmsi", "timestamp"]
OPTIONAL_AIS_COLUMNS = ["draught", "destination", "nav_status"]
STATIC_NUMERIC_COLUMNS = ["build_year", "length_m", "beam_m", "design_draught_m", "dwt", "grt", "teu"]
STATIC_TEXT_COLUMNS = ["vessel_name", "imo", "ship_type", "flag", "source"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a vessel catalog from AIS-derived profiles and optional static metadata."
    )
    parser.add_argument("--ais", required=True, help="Path to cleaned AIS CSV.")
    parser.add_argument(
        "--static",
        required=False,
        help="Optional path to external vessel static CSV.",
    )
    parser.add_argument(
        "--output",
        default="data/processed/vessel_catalog.csv",
        help="Path to vessel catalog output CSV.",
    )
    return parser.parse_args()


def _load_csv(path: Path) -> pd.DataFrame:
    dataframe = pd.read_csv(path)
    dataframe.columns = [column.strip().lower() for column in dataframe.columns]
    return dataframe


def _mode_or_none(series: pd.Series) -> str | None:
    cleaned = series.dropna().astype(str).str.strip()
    cleaned = cleaned[cleaned.ne("")]
    if cleaned.empty:
        return None
    return cleaned.mode().iloc[0]


def load_static_profiles(path: Path) -> pd.DataFrame:
    dataframe = _load_csv(path)
    if "mmsi" not in dataframe.columns:
        raise ValueError("Static vessel profile file must include `mmsi`.")

    dataframe["mmsi"] = dataframe["mmsi"].astype(str).str.strip()
    for column in STATIC_NUMERIC_COLUMNS:
        if column in dataframe.columns:
            dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce")
    for column in STATIC_TEXT_COLUMNS:
        if column in dataframe.columns:
            dataframe[column] = dataframe[column].astype(str).str.strip()
            dataframe.loc[dataframe[column].eq(""), column] = None
    return dataframe


def build_ais_derived_catalog(ais: pd.DataFrame) -> pd.DataFrame:
    dataframe = ais.copy()
    missing = [column for column in REQUIRED_AIS_COLUMNS if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Missing required AIS columns: {', '.join(missing)}")

    dataframe["mmsi"] = dataframe["mmsi"].astype(str).str.strip()
    dataframe["timestamp"] = pd.to_datetime(dataframe["timestamp"], utc=True, errors="coerce")
    dataframe = dataframe.dropna(subset=["mmsi", "timestamp"])

    if "draught" in dataframe.columns:
        dataframe["draught"] = pd.to_numeric(dataframe["draught"], errors="coerce")

    grouped = []
    for mmsi, frame in dataframe.groupby("mmsi", sort=False):
        grouped.append(
            {
                "mmsi": mmsi,
                "first_seen": frame["timestamp"].min().isoformat(),
                "last_seen": frame["timestamp"].max().isoformat(),
                "observed_draught_m": round(float(frame["draught"].median()), 3)
                if "draught" in frame.columns and frame["draught"].notna().any()
                else None,
                "max_observed_draught_m": round(float(frame["draught"].max()), 3)
                if "draught" in frame.columns and frame["draught"].notna().any()
                else None,
                "dominant_destination": _mode_or_none(frame["destination"])
                if "destination" in frame.columns
                else None,
                "dominant_nav_status": _mode_or_none(frame["nav_status"])
                if "nav_status" in frame.columns
                else None,
                "profile_source": "ais_derived",
                "static_source": None,
            }
        )

    return pd.DataFrame(grouped)


def merge_static_profiles(derived: pd.DataFrame, static_profiles: pd.DataFrame | None) -> pd.DataFrame:
    if static_profiles is None or static_profiles.empty:
        return derived.copy()

    merged = derived.merge(static_profiles, on="mmsi", how="left")
    profile_columns = [column for column in STATIC_TEXT_COLUMNS + STATIC_NUMERIC_COLUMNS if column in merged.columns]
    has_external = merged[profile_columns].notna().any(axis=1) if profile_columns else pd.Series(False, index=merged.index)
    merged["profile_source"] = has_external.map(lambda value: "external_merge" if value else "ais_derived")
    merged["static_source"] = merged.get("source")
    return merged


def save_output(dataframe: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(path, index=False)


def main() -> None:
    args = parse_args()
    ais = _load_csv(Path(args.ais))
    derived = build_ais_derived_catalog(ais)
    static_profiles = load_static_profiles(Path(args.static)) if args.static else None
    catalog = merge_static_profiles(derived, static_profiles)
    save_output(catalog, Path(args.output))

    print(f"Vessel catalog rows: {len(catalog)}")
    print(f"Output written to: {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
