import argparse
import json
import shutil
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export current demo outputs into the Vue frontend public directory."
    )
    parser.add_argument("--features", required=True, help="Path to vessel features CSV.")
    parser.add_argument("--risk", required=True, help="Path to regional risk CSV.")
    parser.add_argument("--demo-dir", required=True, help="Path to generated demo visuals directory.")
    parser.add_argument(
        "--public-dir",
        default="frontend/public/demo",
        help="Path to frontend public demo directory.",
    )
    return parser.parse_args()


def load_csv(path: Path) -> pd.DataFrame:
    dataframe = pd.read_csv(path)
    dataframe.columns = [column.strip().lower() for column in dataframe.columns]
    return dataframe


def maybe_round(value: object, digits: int = 3) -> float | None:
    if pd.isna(value):
        return None
    return round(float(value), digits)


def window_label_from_features_path(path: Path) -> str:
    stem = path.stem.replace("vessel_features_", "")
    parts = stem.split("_")
    if len(parts) >= 2:
        return f"{parts[0]} to {parts[1]}"
    return stem


def serialize_vessels(features: pd.DataFrame) -> list[dict]:
    ordered = features.sort_values(["fpi_proxy", "ping_count"], ascending=[False, False]).copy()
    vessels = []
    for rank, row in enumerate(ordered.itertuples(index=False), start=1):
        vessels.append(
            {
                "rank": rank,
                "mmsi": str(row.mmsi),
                "ping_count": int(row.ping_count),
                "track_start": row.track_start,
                "track_end": row.track_end,
                "mean_latitude": maybe_round(row.mean_latitude, 4),
                "mean_longitude": maybe_round(row.mean_longitude, 4),
                "low_speed_ratio": maybe_round(row.low_speed_ratio),
                "mean_sst": maybe_round(row.mean_sst),
                "mean_chlorophyll_a": maybe_round(row.mean_chlorophyll_a),
                "track_duration_hours": maybe_round(row.track_duration_hours, 2),
                "fpi_proxy": maybe_round(row.fpi_proxy),
                "ecp_proxy": maybe_round(row.ecp_proxy),
                "recommendation": row.recommendation,
            }
        )
    return vessels


def serialize_risk_cells(risk: pd.DataFrame) -> list[dict]:
    ordered = risk.sort_values(["rri_score", "traffic_points"], ascending=[False, False]).copy()
    cells = []
    for rank, row in enumerate(ordered.itertuples(index=False), start=1):
        cells.append(
            {
                "rank": rank,
                "grid_lat": maybe_round(row.grid_lat, 4),
                "grid_lon": maybe_round(row.grid_lon, 4),
                "traffic_points": int(row.traffic_points),
                "vessel_count": int(row.vessel_count),
                "low_speed_ratio": maybe_round(row.low_speed_ratio),
                "mean_sst": maybe_round(row.mean_sst),
                "mean_chlorophyll_a": maybe_round(row.mean_chlorophyll_a),
                "traffic_score": maybe_round(row.traffic_score),
                "low_speed_score": maybe_round(row.low_speed_score),
                "environment_score": maybe_round(row.environment_score),
                "rri_score": maybe_round(row.rri_score),
                "risk_level": row.risk_level,
            }
        )
    return cells


def build_summary(vessels: list[dict], risk_cells: list[dict], window_label: str) -> dict:
    top_vessel = vessels[0]
    top_cell = risk_cells[0]
    high_risk_cells = sum(1 for cell in risk_cells if cell["risk_level"] == "high")
    medium_risk_cells = sum(1 for cell in risk_cells if cell["risk_level"] == "medium")

    recommendation_counts: dict[str, int] = {}
    for vessel in vessels:
        recommendation_counts[vessel["recommendation"]] = recommendation_counts.get(vessel["recommendation"], 0) + 1

    return {
        "window_label": window_label,
        "vessels_summarized": len(vessels),
        "grid_cells": len(risk_cells),
        "high_risk_cells": high_risk_cells,
        "medium_risk_cells": medium_risk_cells,
        "recommendation_counts": recommendation_counts,
        "top_vessel": {
            "mmsi": top_vessel["mmsi"],
            "fpi_proxy": top_vessel["fpi_proxy"],
            "ecp_proxy": top_vessel["ecp_proxy"],
            "recommendation": top_vessel["recommendation"],
        },
        "top_cell": {
            "grid_lat": top_cell["grid_lat"],
            "grid_lon": top_cell["grid_lon"],
            "rri_score": top_cell["rri_score"],
            "risk_level": top_cell["risk_level"],
        },
        "top_vessels": vessels[:6],
        "top_cells": risk_cells[:6],
    }


def main() -> None:
    args = parse_args()
    features = load_csv(Path(args.features))
    risk = load_csv(Path(args.risk))
    demo_dir = Path(args.demo_dir)
    public_dir = Path(args.public_dir)
    public_dir.mkdir(parents=True, exist_ok=True)
    window_label = window_label_from_features_path(Path(args.features))

    vessels = serialize_vessels(features)
    risk_cells = serialize_risk_cells(risk)
    summary = build_summary(vessels, risk_cells, window_label)

    (public_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (public_dir / "vessels.json").write_text(
        json.dumps(vessels, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (public_dir / "risk_cells.json").write_text(
        json.dumps(risk_cells, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    for file_name in [
        "demo_dashboard.html",
        "regional_demo_map.html",
        "recommendation_breakdown.png",
        "top_vessels_fpi.png",
    ]:
        shutil.copy2(demo_dir / file_name, public_dir / file_name)

    print(f"Frontend demo assets exported to: {public_dir.resolve()}")


if __name__ == "__main__":
    main()
