import argparse
import csv
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract distinct MMSI values from downloaded region-event JSON files."
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Directory containing region-event JSON files.",
    )
    parser.add_argument(
        "--output",
        default="data/raw/mmsi_seed.csv",
        help="CSV path for extracted MMSI list.",
    )
    return parser.parse_args()


def iter_region_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.json"))


def extract_mmsi_values(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    values: list[str] = []

    if "pages" in payload:
        for page in payload.get("pages", []):
            content = page.get("data", {}).get("content", [])
            for item in content:
                value = item.get("mmsi")
                if value is not None:
                    values.append(str(value))
        return values

    content = payload.get("data", {}).get("content", [])
    for item in content:
        value = item.get("mmsi")
        if value is not None:
            values.append(str(value))
    return values


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_path = Path(args.output)

    values: list[str] = []
    for path in iter_region_files(input_dir):
        values.extend(extract_mmsi_values(path))

    unique_values = sorted(dict.fromkeys(values))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["mmsi"])
        for value in unique_values:
            writer.writerow([value])

    print(f"Region files scanned: {len(iter_region_files(input_dir))}")
    print(f"Unique MMSI extracted: {len(unique_values)}")
    print(f"Output written to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
