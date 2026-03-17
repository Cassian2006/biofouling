import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "science_calibration.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build science calibration config from a processed environment file."
    )
    parser.add_argument(
        "--env",
        default="data/processed/env_20260115_20260130.csv",
        help="Path to processed environment CSV.",
    )
    parser.add_argument(
        "--window-label",
        default="20260115 to 20260130",
        help="Window label for the calibration metadata.",
    )
    parser.add_argument(
        "--default-maintenance-gap-days",
        type=float,
        default=90.0,
        help="Default maintenance-gap prior when no external maintenance records exist.",
    )
    parser.add_argument(
        "--output",
        default=str(CONFIG_PATH),
        help="Path to output JSON config.",
    )
    return parser.parse_args()


def build_calibration(env: pd.DataFrame, window_label: str, default_maintenance_gap_days: float) -> dict[str, object]:
    speed = np.sqrt(env["current_u"].fillna(0) ** 2 + env["current_v"].fillna(0) ** 2)
    return {
        "version": "science_calibration_v1",
        "window_label": window_label,
        "current_speed_quantiles": {
            "p25": round(float(speed.quantile(0.25)), 4),
            "p50": round(float(speed.quantile(0.50)), 4),
            "p75": round(float(speed.quantile(0.75)), 4),
            "p90": round(float(speed.quantile(0.90)), 4),
            "max": round(float(speed.max()), 4),
        },
        "recommendation_thresholds": {
            "fpi_prioritize": 0.25,
            "ecp_prioritize": 0.30,
            "fpi_monitor": 0.08,
            "ecp_monitor": 0.10,
        },
        "maintenance": {
            "default_gap_days": round(float(default_maintenance_gap_days), 1),
            "source": "neutral_default_without_external_maintenance_records",
        },
    }


def main() -> None:
    args = parse_args()
    env = pd.read_csv(args.env)
    env.columns = [column.strip().lower() for column in env.columns]
    calibration = build_calibration(env, args.window_label, args.default_maintenance_gap_days)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(calibration, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Science calibration written to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
