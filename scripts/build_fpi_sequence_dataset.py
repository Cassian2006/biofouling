import argparse
from pathlib import Path

try:
    from scripts.fpi_forecast import (
        build_supervised_sequences,
        build_window_feature_frame,
        load_prepared_inputs,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from fpi_forecast import (  # type: ignore
        build_supervised_sequences,
        build_window_feature_frame,
        load_prepared_inputs,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a supervised sequence dataset for FPI forecasting."
    )
    parser.add_argument("--ais", required=True, help="Path to cleaned AIS CSV.")
    parser.add_argument("--env", help="Path to processed environment CSV.")
    parser.add_argument(
        "--window-hours",
        type=int,
        default=6,
        help="Window size in hours for sequence aggregation.",
    )
    parser.add_argument(
        "--history-windows",
        type=int,
        default=8,
        help="Number of historical windows used as model input.",
    )
    parser.add_argument(
        "--horizon-windows",
        type=int,
        default=1,
        help="How many windows ahead to forecast.",
    )
    parser.add_argument(
        "--min-pings",
        type=int,
        default=4,
        help="Minimum AIS pings required in a window.",
    )
    parser.add_argument(
        "--output",
        default="data/processed/fpi_sequence_dataset.csv",
        help="Path to output sequence dataset CSV.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ais, env = load_prepared_inputs(Path(args.ais), Path(args.env) if args.env else None)
    windows = build_window_feature_frame(
        ais,
        env,
        window_hours=args.window_hours,
        min_pings=args.min_pings,
    )
    dataset = build_supervised_sequences(
        windows,
        history_windows=args.history_windows,
        horizon_windows=args.horizon_windows,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(output_path, index=False)

    print(f"Window rows: {len(windows)}")
    print(f"Sequence rows: {len(dataset)}")
    print(f"Output written to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
