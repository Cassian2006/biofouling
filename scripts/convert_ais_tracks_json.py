import argparse
import json
from pathlib import Path

import pandas as pd


FIELD_MAP = {
    "mmsi": "mmsi",
    "postime": "timestamp",
    "lon": "longitude",
    "lat": "latitude",
    "status": "nav_status",
    "eta": "eta",
    "dest": "destination",
    "draught": "draught",
    "cog": "cog",
    "hdg": "heading",
    "sog": "sog",
    "rot": "rot",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert sliced AIS track JSON files into a flat CSV table."
    )
    parser.add_argument("--input-dir", required=True, help="Root directory containing track JSON files.")
    parser.add_argument(
        "--output",
        default="data/raw/ais_tracks_flat.csv",
        help="Path to flattened AIS CSV output.",
    )
    return parser.parse_args()


def iter_track_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.json"))


def load_track_records(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("data", [])
    normalized: list[dict] = []
    for record in records:
        row = {target: record.get(source) for source, target in FIELD_MAP.items()}
        row["source_file"] = path.name
        row["source_mmsi_dir"] = path.parent.name
        normalized.append(row)
    return normalized


def build_dataframe(files: list[Path]) -> pd.DataFrame:
    rows: list[dict] = []
    for path in files:
        rows.extend(load_track_records(path))

    dataframe = pd.DataFrame(rows)
    if dataframe.empty:
        return dataframe

    dataframe["timestamp"] = pd.to_datetime(dataframe["timestamp"], utc=True, errors="coerce")
    dataframe["latitude"] = pd.to_numeric(dataframe["latitude"], errors="coerce")
    dataframe["longitude"] = pd.to_numeric(dataframe["longitude"], errors="coerce")
    for column in ["sog", "cog", "heading", "draught", "rot"]:
        if column in dataframe.columns:
            dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce")

    dataframe = dataframe.dropna(subset=["mmsi", "timestamp", "latitude", "longitude"])
    dataframe = dataframe.drop_duplicates(subset=["mmsi", "timestamp", "latitude", "longitude"])
    dataframe = dataframe.sort_values(["mmsi", "timestamp"]).reset_index(drop=True)
    return dataframe


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_path = Path(args.output)

    files = iter_track_files(input_dir)
    dataframe = build_dataframe(files)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(output_path, index=False)

    print(f"Track files scanned: {len(files)}")
    print(f"Flattened rows: {len(dataframe)}")
    print(f"Output written to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
