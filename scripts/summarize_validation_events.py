import argparse
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = ["validation_id", "mmsi", "event_type", "event_start", "source"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize external validation events at vessel level."
    )
    parser.add_argument("--input", required=True, help="Path to validation events CSV.")
    parser.add_argument(
        "--output",
        default="data/processed/validation_summary.csv",
        help="Path to validation summary CSV output.",
    )
    return parser.parse_args()


def load_validation_events(path: Path) -> pd.DataFrame:
    dataframe = pd.read_csv(path)
    dataframe.columns = [column.strip().lower() for column in dataframe.columns]
    missing = [column for column in REQUIRED_COLUMNS if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Missing required validation columns: {', '.join(missing)}")

    dataframe["mmsi"] = dataframe["mmsi"].astype(str).str.strip()
    dataframe["event_start"] = pd.to_datetime(dataframe["event_start"], utc=True, errors="coerce")
    if "event_end" in dataframe.columns:
        dataframe["event_end"] = pd.to_datetime(dataframe["event_end"], utc=True, errors="coerce")
    return dataframe.dropna(subset=["mmsi", "event_start"])


def summarize_validation_events(dataframe: pd.DataFrame) -> pd.DataFrame:
    summaries = []
    for mmsi, frame in dataframe.sort_values("event_start").groupby("mmsi", sort=False):
        latest = frame.iloc[-1]
        sources = sorted({str(value).strip() for value in frame["source"].dropna() if str(value).strip()})
        notes_count = int(frame["notes"].fillna("").astype(str).str.strip().ne("").sum()) if "notes" in frame.columns else 0
        summaries.append(
            {
                "mmsi": mmsi,
                "event_count": int(len(frame)),
                "source_count": int(len(sources)),
                "sources": " | ".join(sources),
                "latest_event_type": str(latest["event_type"]),
                "latest_event_start": latest["event_start"].isoformat(),
                "latest_port_name": str(latest["port_name"]) if "port_name" in frame.columns and pd.notna(latest["port_name"]) else None,
                "notes_count": notes_count,
            }
        )
    return pd.DataFrame(summaries)


def save_output(dataframe: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(path, index=False)


def main() -> None:
    args = parse_args()
    events = load_validation_events(Path(args.input))
    summary = summarize_validation_events(events)
    save_output(summary, Path(args.output))

    print(f"Validation summary rows: {len(summary)}")
    print(f"Output written to: {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
