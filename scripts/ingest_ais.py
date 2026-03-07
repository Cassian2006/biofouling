import argparse
from pathlib import Path

import pandas as pd


DEFAULT_BBOX = {
    "west": 102.90,
    "south": 0.80,
    "east": 104.90,
    "north": 1.85,
}

REQUIRED_COLUMNS = ["mmsi", "timestamp", "latitude", "longitude"]
OPTIONAL_NUMERIC_COLUMNS = ["sog", "cog", "heading"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean AIS trajectory data for the Singapore study area."
    )
    parser.add_argument("--input", required=True, help="Path to raw AIS CSV file.")
    parser.add_argument(
        "--output",
        default="data/processed/ais_cleaned.csv",
        help="Path to cleaned AIS CSV output.",
    )
    return parser.parse_args()


def load_ais_csv(path: Path) -> pd.DataFrame:
    dataframe = pd.read_csv(path)
    dataframe.columns = [column.strip().lower() for column in dataframe.columns]
    return dataframe


def validate_columns(dataframe: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in dataframe.columns]
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(f"Missing required AIS columns: {missing_text}")


def clean_ais(dataframe: pd.DataFrame) -> pd.DataFrame:
    cleaned = dataframe.copy()
    cleaned = cleaned.dropna(subset=REQUIRED_COLUMNS)
    cleaned["timestamp"] = pd.to_datetime(cleaned["timestamp"], utc=True, errors="coerce")
    cleaned["latitude"] = pd.to_numeric(cleaned["latitude"], errors="coerce")
    cleaned["longitude"] = pd.to_numeric(cleaned["longitude"], errors="coerce")

    for column in OPTIONAL_NUMERIC_COLUMNS:
        if column in cleaned.columns:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    cleaned = cleaned.dropna(subset=["timestamp", "latitude", "longitude"])
    cleaned = cleaned[
        cleaned["longitude"].between(DEFAULT_BBOX["west"], DEFAULT_BBOX["east"])
        & cleaned["latitude"].between(DEFAULT_BBOX["south"], DEFAULT_BBOX["north"])
    ]
    cleaned = cleaned.drop_duplicates(subset=["mmsi", "timestamp", "latitude", "longitude"])
    cleaned = cleaned.sort_values(by=["mmsi", "timestamp"]).reset_index(drop=True)

    if "sog" in cleaned.columns:
        cleaned["is_low_speed"] = cleaned["sog"].fillna(0).between(0, 3)
    else:
        cleaned["is_low_speed"] = False

    cleaned["study_area"] = "singapore_strait_v1"
    return cleaned


def save_output(dataframe: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(path, index=False)


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    dataframe = load_ais_csv(input_path)
    validate_columns(dataframe)
    cleaned = clean_ais(dataframe)
    save_output(cleaned, output_path)

    print(f"Input rows: {len(dataframe)}")
    print(f"Cleaned rows: {len(cleaned)}")
    print(f"Output written to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
