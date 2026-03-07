import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a first-phase markdown report from vessel features."
    )
    parser.add_argument("--input", required=True, help="Path to vessel feature CSV.")
    parser.add_argument(
        "--output",
        default="outputs/reports/voyage_report.md",
        help="Path to markdown report output.",
    )
    return parser.parse_args()


def build_report(dataframe: pd.DataFrame) -> str:
    lines = [
        "# Voyage Report",
        "",
        "本报告为第一阶段演示版，根据已生成的船舶级特征表输出相对风险摘要。",
        "",
        f"- Vessel count: {len(dataframe)}",
        "",
        "## Vessel Summaries",
        "",
    ]

    for row in dataframe.itertuples(index=False):
        lines.extend(
            [
                f"### MMSI {row.mmsi}",
                f"- Track window: {row.track_start} -> {row.track_end}",
                f"- Ping count: {row.ping_count}",
                f"- Low-speed ratio: {row.low_speed_ratio:.2f}",
                f"- FPI proxy: {row.fpi_proxy:.2f}",
                f"- ECP proxy: {row.ecp_proxy:.2f}",
                f"- Recommendation: {row.recommendation}",
                "",
            ]
        )

    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    dataframe = pd.read_csv(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_report(dataframe), encoding="utf-8")

    print(f"Report written to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
