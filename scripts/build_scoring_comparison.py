import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_features import build_vessel_features, load_csv, prepare_ais, prepare_env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare legacy proxy scoring with the scientific scoring upgrade."
    )
    parser.add_argument("--ais", required=True, help="Path to cleaned AIS CSV.")
    parser.add_argument("--env", required=True, help="Path to processed environment CSV.")
    parser.add_argument("--legacy-features", required=True, help="Path to frozen legacy feature CSV.")
    parser.add_argument(
        "--output-dir",
        default="outputs/science",
        help="Directory for scientific scoring comparison outputs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ais = prepare_ais(load_csv(Path(args.ais)))
    env = prepare_env(load_csv(Path(args.env)))
    legacy = load_csv(Path(args.legacy_features))
    legacy["mmsi"] = legacy["mmsi"].astype(str)
    scientific = build_vessel_features(ais, env)
    scientific["mmsi"] = scientific["mmsi"].astype(str)

    comparison = legacy[["mmsi", "fpi_proxy", "ecp_proxy"]].merge(
        scientific[
            [
                "mmsi",
                "fpi_proxy",
                "ecp_proxy",
                "environment_score",
                "temperature_score",
                "salinity_score",
                "productivity_score",
                "hydrodynamic_score",
                "behavior_score",
            ]
        ],
        on="mmsi",
        suffixes=("_legacy", "_scientific"),
    )
    comparison["fpi_delta"] = comparison["fpi_proxy_scientific"] - comparison["fpi_proxy_legacy"]
    comparison["ecp_delta"] = comparison["ecp_proxy_scientific"] - comparison["ecp_proxy_legacy"]
    comparison.to_csv(output_dir / "scoring_comparison_20260115_20260130.csv", index=False)

    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

    sns.scatterplot(
        data=comparison,
        x="fpi_proxy_legacy",
        y="fpi_proxy_scientific",
        s=36,
        alpha=0.7,
        ax=axes[0],
        color="#1d4ed8",
    )
    axes[0].plot([0, 1], [0, 1], linestyle="--", color="#9ca3af", linewidth=1)
    axes[0].set_title("Legacy vs Scientific FPI")
    axes[0].set_xlabel("Legacy FPI proxy")
    axes[0].set_ylabel("Scientific FPI")

    delta_summary = pd.DataFrame(
        {
            "metric": ["FPI", "ECP"],
            "mean_delta": [comparison["fpi_delta"].mean(), comparison["ecp_delta"].mean()],
            "median_delta": [comparison["fpi_delta"].median(), comparison["ecp_delta"].median()],
        }
    )
    delta_long = delta_summary.melt(id_vars="metric", var_name="statistic", value_name="value")
    sns.barplot(data=delta_long, x="metric", y="value", hue="statistic", ax=axes[1], palette="crest")
    axes[1].set_title("Average score shift after science upgrade")
    axes[1].set_xlabel("")
    axes[1].set_ylabel("Score delta")

    plt.tight_layout()
    fig.savefig(output_dir / "scoring_v1_vs_v2.png", dpi=180)
    plt.close(fig)

    summary = {
        "legacy_fpi_mean": round(float(comparison["fpi_proxy_legacy"].mean()), 4),
        "scientific_fpi_mean": round(float(comparison["fpi_proxy_scientific"].mean()), 4),
        "legacy_ecp_mean": round(float(comparison["ecp_proxy_legacy"].mean()), 4),
        "scientific_ecp_mean": round(float(comparison["ecp_proxy_scientific"].mean()), 4),
        "mean_fpi_delta": round(float(comparison["fpi_delta"].mean()), 4),
        "mean_ecp_delta": round(float(comparison["ecp_delta"].mean()), 4),
    }
    (output_dir / "scoring_comparison_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Scientific comparison written to: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
