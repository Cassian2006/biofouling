import argparse
from pathlib import Path

import numpy as np
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
        "--salinity-netcdf",
        help="Path to Copernicus salinity NetCDF file.",
    )
    parser.add_argument(
        "--currents-netcdf",
        help="Path to Copernicus currents NetCDF file with uo/vo variables.",
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


def dataset_to_frame(path: Path, variable_mapping: dict[str, str]) -> pd.DataFrame:
    dataset = xr.open_dataset(path)
    dataframe = dataset[list(variable_mapping)].to_dataframe().reset_index()
    dataframe = dataframe.rename(columns=variable_mapping)
    dataframe = dataframe.rename(columns={"time": "timestamp"})
    if "depth" in dataframe.columns:
        dataframe = dataframe.drop(columns=["depth"])
    dataframe["timestamp"] = pd.to_datetime(dataframe["timestamp"], utc=True, errors="coerce")
    return dataframe


def attach_variables_by_nearest_grid(
    base: pd.DataFrame,
    auxiliary: pd.DataFrame,
    value_columns: list[str],
) -> pd.DataFrame:
    result = base.copy()
    auxiliary_indexed = {
        timestamp: frame.reset_index(drop=True)
        for timestamp, frame in auxiliary.groupby("timestamp", sort=False)
    }

    for column in value_columns:
        result[column] = np.nan

    matched_frames: list[pd.DataFrame] = []
    for timestamp, base_frame in result.groupby("timestamp", sort=False):
        aux_frame = auxiliary_indexed.get(timestamp)
        day = base_frame.copy()

        if aux_frame is None or aux_frame.empty:
            matched_frames.append(day)
            continue

        aux_frame = aux_frame.dropna(subset=value_columns, how="all").reset_index(drop=True)
        if aux_frame.empty:
            matched_frames.append(day)
            continue

        aux_lat = aux_frame["latitude"].to_numpy()
        aux_lon = aux_frame["longitude"].to_numpy()
        aux_values = {
            column: aux_frame[column].to_numpy()
            for column in value_columns
        }

        matched = {column: [] for column in value_columns}
        for row in day.itertuples(index=False):
            distance = (aux_lat - row.latitude) ** 2 + (aux_lon - row.longitude) ** 2
            nearest_index = int(distance.argmin())
            for column in value_columns:
                matched[column].append(float(aux_values[column][nearest_index]))

        for column in value_columns:
            day[column] = matched[column]

        matched_frames.append(day)

    return pd.concat(matched_frames, ignore_index=True)


def load_env_netcdf(
    thetao_path: Path | None,
    chl_path: Path | None,
    salinity_path: Path | None = None,
    currents_path: Path | None = None,
) -> pd.DataFrame:
    if not thetao_path:
        raise ValueError("Thetao NetCDF is required as the base grid for environment processing.")

    base = dataset_to_frame(thetao_path, {"thetao": "sst"})
    if base.empty:
        raise ValueError("At least one NetCDF path must be provided.")

    if chl_path:
        chl = dataset_to_frame(chl_path, {"chl": "chlorophyll_a"})
        base = attach_variables_by_nearest_grid(base, chl, ["chlorophyll_a"])

    if salinity_path:
        salinity = dataset_to_frame(salinity_path, {"so": "salinity"})
        base = attach_variables_by_nearest_grid(base, salinity, ["salinity"])

    if currents_path:
        currents = dataset_to_frame(currents_path, {"uo": "current_u", "vo": "current_v"})
        base = attach_variables_by_nearest_grid(base, currents, ["current_u", "current_v"])

    return base


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
            Path(args.salinity_netcdf) if args.salinity_netcdf else None,
            Path(args.currents_netcdf) if args.currents_netcdf else None,
        )

    validate_columns(dataframe)
    cleaned = clean_env(dataframe)
    save_output(cleaned, output_path)

    print(f"Input rows: {len(dataframe)}")
    print(f"Processed rows: {len(cleaned)}")
    print(f"Output written to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
