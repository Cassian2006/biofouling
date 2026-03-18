import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.science_validation import (
    apply_science_scenario,
    default_ablation_scenarios,
    default_sensitivity_scenarios,
    summarize_scenario_shift,
)
from scripts.build_features import build_vessel_features_with_scoring, load_csv, prepare_ais, prepare_env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build sensitivity and ablation outputs for scientific scoring validation."
    )
    parser.add_argument("--ais", required=True, help="Path to cleaned AIS CSV.")
    parser.add_argument("--env", required=True, help="Path to processed environment CSV.")
    parser.add_argument(
        "--output-dir",
        default="outputs/science_validation",
        help="Directory for scientific validation outputs.",
    )
    return parser.parse_args()


def recommendation_counts(frame: pd.DataFrame) -> dict[str, int]:
    counts = frame["recommendation"].value_counts().to_dict()
    return {
        "Prioritize cleaning assessment": int(counts.get("Prioritize cleaning assessment", 0)),
        "Monitor exposure trend": int(counts.get("Monitor exposure trend", 0)),
        "Low immediate concern": int(counts.get("Low immediate concern", 0)),
    }


def render_sensitivity_chart(sensitivity: pd.DataFrame, output_dir: Path) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(14, 5.8))

    labels = sensitivity.get("scenario_name", sensitivity["scenario_label"])
    axes[0].bar(labels, sensitivity["top20_overlap"], color="#1d4ed8")
    axes[0].set_title("Top-20 stability under sensitivity checks")
    axes[0].set_ylabel("Overlap with current science-v2 ranking")
    axes[0].set_ylim(0, 1.05)
    axes[0].tick_params(axis="x", rotation=35)

    axes[1].bar(labels, sensitivity["recommendation_change_rate"], color="#0f766e")
    axes[1].set_title("Recommendation change rate")
    axes[1].set_ylabel("Changed vessels share")
    axes[1].set_ylim(0, max(0.05, sensitivity["recommendation_change_rate"].max() * 1.2))
    axes[1].tick_params(axis="x", rotation=35)

    figure.tight_layout()
    figure.savefig(output_dir / "sensitivity_stability.png", dpi=180)
    plt.close(figure)


def render_ablation_chart(ablation: pd.DataFrame, output_dir: Path) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(14, 5.8))

    labels = ablation.get("scenario_name", ablation["scenario_label"])
    axes[0].bar(labels, ablation["mean_fpi_shift"], color="#dc2626")
    axes[0].axhline(0.0, color="#6b7280", linestyle="--", linewidth=1)
    axes[0].set_title("Average FPI shift after removing a mechanism")
    axes[0].set_ylabel("Mean FPI delta")
    axes[0].tick_params(axis="x", rotation=35)

    axes[1].bar(labels, ablation["top20_overlap"], color="#7c3aed")
    axes[1].set_title("Top-20 overlap after mechanism ablation")
    axes[1].set_ylabel("Overlap with current science-v2 ranking")
    axes[1].set_ylim(0, 1.05)
    axes[1].tick_params(axis="x", rotation=35)

    figure.tight_layout()
    figure.savefig(output_dir / "ablation_effects.png", dpi=180)
    plt.close(figure)


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ais = prepare_ais(load_csv(Path(args.ais)))
    env = prepare_env(load_csv(Path(args.env)))
    baseline_frame = build_vessel_features_with_scoring(ais, env)
    baseline = pd.DataFrame(
        {
            "mmsi": baseline_frame["mmsi"].astype(str),
            "fpi_score": baseline_frame["fpi_proxy"],
            "ecp_score": baseline_frame["ecp_proxy"],
            "recommendation": baseline_frame["recommendation"],
        }
    )

    sensitivity_rows: list[dict[str, float | str]] = []
    ablation_rows: list[dict[str, float | str]] = []

    baseline_label = "当前科学评分"
    for scenario in default_sensitivity_scenarios()[1:]:
        candidate = apply_science_scenario(baseline_frame, scenario)
        row = summarize_scenario_shift(baseline, candidate, label=scenario.label, kind="sensitivity")
        row["scenario_name"] = scenario.name
        sensitivity_rows.append(row)

    for scenario in default_ablation_scenarios():
        candidate = apply_science_scenario(baseline_frame, scenario)
        row = summarize_scenario_shift(baseline, candidate, label=scenario.label, kind="ablation")
        row["scenario_name"] = scenario.name
        ablation_rows.append(row)

    sensitivity = pd.DataFrame(sensitivity_rows).sort_values("top20_overlap", ascending=False)
    ablation = pd.DataFrame(ablation_rows).sort_values("top20_overlap", ascending=False)

    sensitivity.to_csv(output_dir / "sensitivity_summary.csv", index=False)
    ablation.to_csv(output_dir / "ablation_summary.csv", index=False)

    render_sensitivity_chart(sensitivity, output_dir)
    render_ablation_chart(ablation, output_dir)

    summary = {
        "baseline_label": baseline_label,
        "baseline_recommendation_counts": recommendation_counts(baseline),
        "sensitivity_scenarios": len(sensitivity),
        "ablation_scenarios": len(ablation),
        "most_stable_sensitivity": sensitivity.iloc[0]["scenario_label"] if not sensitivity.empty else None,
        "most_disruptive_ablation": (
            ablation.sort_values("top20_overlap", ascending=True).iloc[0]["scenario_label"]
            if not ablation.empty
            else None
        ),
        "highest_recommendation_change_sensitivity": (
            sensitivity.sort_values("recommendation_change_rate", ascending=False).iloc[0]["scenario_label"]
            if not sensitivity.empty
            else None
        ),
    }
    (output_dir / "science_validation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Science validation outputs written to: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
