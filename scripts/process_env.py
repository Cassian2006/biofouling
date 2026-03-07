import argparse
from pathlib import Path

import pandas as pd
import xarray as xr


DEFAULT_BBOX = {
    "west": 102.90,
    "south": 0.80,
    "east": 104.90,
    "north": 1.85,
}

REQUIRED_COLUMNS = ["timestamp", "latitude", "longitude", "sst"]
OPTIONAL_NUMERIC_COLUMNS = ["salinity", "current_u", "current_v", "chlorophyll_a"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean environmental exposure data for the study area."
    )
    parser.add_argument("--input", help="Path to raw environment CSV file.")
    parser.add_argument(
        "--thetao-netcdf",
        help="Path to Copernicus thetao NetCDF file.",
    )
    parser.add_argument(
        "--chl-netcdf",
        help="Path to Copernicus chlorophyll NetCDF file.",
    )
    parser.add_argument(
        "--output",
        default="data/processed/env_processed.csv",
        help="Path to processed environment CSV output.",
    )
    return parser.parse_args()


def load_env_csv(path: Path) -> pd.DataFrame:
    dataframe = pd.read_csv(path)
    dataframe.columns = [column.strip().lower() for column in dataframe.columns]
    return dataframe


def load_env_netcdf(thetao_path: Path | None, chl_path: Path | None) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    if thetao_path:
        ds = xr.open_dataset(thetao_path)
        df = ds[["thetao"]].to_dataframe().reset_index()
        df = df.rename(columns={"thetao": "sst"})
        frames.append(df)

    if chl_path:
        ds = xr.open_dataset(chl_path)
        df = ds[["chl"]].to_dataframe().reset_index()
        df = df.rename(columns={"chl": "chlorophyll_a"})
        frames.append(df)

    if not frames:
        raise ValueError("At least one NetCDF path must be provided.")

    merged = frames[0]
    for frame in frames[1:]:
        merged = merged.merge(
            frame,
            on=[column for column in ["time", "depth", "latitude", "longitude"] if column in frame.columns],
            how="outer",
        )

    merged = merged.rename(columns={"time": "timestamp"})
    if "depth" in merged.columns:
        merged = merged.drop(columns=["depth"])
    return merged


def validate_columns(dataframe: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Missing required environment columns: {', '.join(missing)}")


def clean_env(dataframe: pd.DataFrame) -> pd.DataFrame:
    cleaned = dataframe.copy()
    cleaned = cleaned.dropna(subset=REQUIRED_COLUMNS)
    cleaned["timestamp"] = pd.to_datetime(cleaned["timestamp"], utc=True, errors="coerce")
    cleaned["latitude"] = pd.to_numeric(cleaned["latitude"], errors="coerce")
    cleaned["longitude"] = pd.to_numeric(cleaned["longitude"], errors="coerce")
    cleaned["sst"] = pd.to_numeric(cleaned["sst"], errors="coerce")

    for column in OPTIONAL_NUMERIC_COLUMNS:
        if column in cleaned.columns:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    cleaned = cleaned.dropna(subset=["timestamp", "latitude", "longitude", "sst"])
    cleaned = cleaned[
        cleaned["longitude"].between(DEFAULT_BBOX["west"], DEFAULT_BBOX["east"])
        & cleaned["latitude"].between(DEFAULT_BBOX["south"], DEFAULT_BBOX["north"])
    ]
    cleaned = cleaned.drop_duplicates(subset=["timestamp", "latitude", "longitude"])
    cleaned = cleaned.sort_values(by=["timestamp", "latitude", "longitude"]).reset_index(
        drop=True
    )
    cleaned["study_area"] = "singapore_strait_v1"
    return cleaned


def save_output(dataframe: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(path, index=False)


def main() -> None:
    args = parse_args()
    output_path = Path(args.output)

    if args.input:
        dataframe = load_env_csv(Path(args.input))
    else:
        dataframe = load_env_netcdf(
            Path(args.thetao_netcdf) if args.thetao_netcdf else None,
            Path(args.chl_netcdf) if args.chl_netcdf else None,
        )

    validate_columns(dataframe)
    cleaned = clean_env(dataframe)
    save_output(cleaned, output_path)

    print(f"Input rows: {len(dataframe)}")
    print(f"Processed rows: {len(cleaned)}")
    print(f"Output written to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
