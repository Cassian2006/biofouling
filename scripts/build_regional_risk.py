import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a first regional risk layer from AIS and environment data."
    )
    parser.add_argument("--ais", required=True, help="Path to cleaned AIS CSV.")
    parser.add_argument("--env", required=True, help="Path to processed environment CSV.")
    parser.add_argument(
        "--output",
        default="outputs/maps/regional_risk.csv",
        help="Path to regional risk CSV output.",
    )
    parser.add_argument(
        "--grid-size",
        type=float,
        default=0.05,
        help="Grid size in degrees for spatial aggregation.",
    )
    return parser.parse_args()


def load_csv(path: Path) -> pd.DataFrame:
    dataframe = pd.read_csv(path)
    dataframe.columns = [column.strip().lower() for column in dataframe.columns]
    return dataframe


def add_grid_columns(dataframe: pd.DataFrame, grid_size: float) -> pd.DataFrame:
    result = dataframe.copy()
    result["grid_lat"] = (result["latitude"] / grid_size).round().mul(grid_size).round(4)
    result["grid_lon"] = (result["longitude"] / grid_size).round().mul(grid_size).round(4)
    return result


def normalize(series: pd.Series) -> pd.Series:
    valid = series.fillna(0)
    min_value = valid.min()
    max_value = valid.max()
    if max_value == min_value:
        return pd.Series(0.0, index=series.index)
    return (valid - min_value) / (max_value - min_value)


def fill_with_median_or_zero(series: pd.Series) -> pd.Series:
    non_null = series.dropna()
    if non_null.empty:
        return series.fillna(0)
    return series.fillna(non_null.median())


def build_risk_layer(ais: pd.DataFrame, env: pd.DataFrame, grid_size: float) -> pd.DataFrame:
    ais = add_grid_columns(ais, grid_size)
    env = add_grid_columns(env, grid_size)

    ais_layer = (
        ais.groupby(["grid_lat", "grid_lon"], as_index=False)
        .agg(
            traffic_points=("mmsi", "size"),
            vessel_count=("mmsi", "nunique"),
            low_speed_ratio=("is_low_speed", "mean"),
        )
        .copy()
    )

    env_layer = (
        env.groupby(["grid_lat", "grid_lon"], as_index=False)
        .agg(
            mean_sst=("sst", "mean"),
            mean_chlorophyll_a=("chlorophyll_a", "mean"),
        )
        .copy()
    )

    layer = ais_layer.merge(env_layer, on=["grid_lat", "grid_lon"], how="left")
    layer["traffic_score"] = normalize(layer["traffic_points"])
    layer["low_speed_score"] = layer["low_speed_ratio"].fillna(0)

    sst_base = fill_with_median_or_zero(layer["mean_sst"])
    chl_base = fill_with_median_or_zero(layer["mean_chlorophyll_a"])
    sst_score = ((sst_base - 24) / 8).clip(0, 1)
    chl_score = normalize(chl_base)
    layer["environment_score"] = (sst_score * 0.55 + chl_score * 0.45).round(4)

    layer["rri_score"] = (
        layer["environment_score"] * 0.4
        + layer["traffic_score"] * 0.35
        + layer["low_speed_score"] * 0.25
    ).round(4)

    layer["risk_level"] = pd.cut(
        layer["rri_score"],
        bins=[-0.001, 0.33, 0.66, 1.0],
        labels=["low", "medium", "high"],
    ).astype(str)

    return layer.sort_values(["rri_score", "traffic_points"], ascending=[False, False]).reset_index(
        drop=True
    )


def main() -> None:
    args = parse_args()
    ais = load_csv(Path(args.ais))
    env = load_csv(Path(args.env))
    layer = build_risk_layer(ais, env, args.grid_size)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    layer.to_csv(output_path, index=False)

    print(f"Grid cells: {len(layer)}")
    print(f"Output written to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
