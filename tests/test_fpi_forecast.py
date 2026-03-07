import pandas as pd

from scripts.fpi_forecast import (
    build_supervised_sequences,
    build_window_feature_frame,
    sequence_feature_columns,
)


def test_build_window_feature_frame_aggregates_vessel_windows() -> None:
    ais = pd.DataFrame(
        {
            "mmsi": ["111000111"] * 6,
            "timestamp": [
                "2026-01-15T00:00:00Z",
                "2026-01-15T03:00:00Z",
                "2026-01-15T06:00:00Z",
                "2026-01-15T09:00:00Z",
                "2026-01-15T12:00:00Z",
                "2026-01-15T15:00:00Z",
            ],
            "latitude": [1.20, 1.21, 1.22, 1.23, 1.24, 1.25],
            "longitude": [103.80, 103.81, 103.82, 103.83, 103.84, 103.85],
            "is_low_speed": [True, True, False, True, True, True],
            "sog": [1.0, 1.2, 8.0, 1.4, 0.8, 0.9],
        }
    )
    env = pd.DataFrame(
        {
            "timestamp": ["2026-01-15T00:00:00Z"] * 2,
            "latitude": [1.20, 1.24],
            "longitude": [103.80, 103.84],
            "sst": [28.5, 27.9],
            "chlorophyll_a": [0.6, 0.2],
            "salinity": [31.2, 31.0],
            "current_u": [-0.3, -0.1],
            "current_v": [0.1, -0.2],
        }
    )

    windows = build_window_feature_frame(ais, env, window_hours=6, min_pings=2)

    assert len(windows) == 3
    assert windows["ping_count"].tolist() == [2, 2, 2]
    assert windows["risk_label"].tolist() == ["high", "medium", "high"]
    assert round(float(windows.iloc[0]["mean_sst"]), 1) == 28.5


def test_build_supervised_sequences_returns_flattened_training_rows() -> None:
    windows = pd.DataFrame(
        {
            "mmsi": ["111000111"] * 5,
            "window_start": pd.date_range("2026-01-15T00:00:00Z", periods=5, freq="6h"),
            "window_end": pd.date_range("2026-01-15T06:00:00Z", periods=5, freq="6h"),
            "window_hours": [6] * 5,
            "ping_count": [8, 9, 10, 11, 12],
            "coverage_ratio": [1.0, 1.0, 0.8, 1.0, 1.0],
            "mean_sog": [1.0, 1.2, 4.5, 5.0, 0.8],
            "max_sog": [1.5, 1.6, 6.0, 6.5, 1.2],
            "low_speed_ratio": [1.0, 0.9, 0.4, 0.3, 1.0],
            "mean_sst": [28.4, 28.1, 27.8, 27.6, 28.3],
            "mean_chlorophyll_a": [0.5, 0.45, 0.3, 0.25, 0.55],
            "mean_salinity": [31.1, 31.0, 30.9, 31.2, 31.1],
            "mean_current_u": [-0.3, -0.2, -0.1, -0.2, -0.3],
            "mean_current_v": [0.1, 0.0, -0.1, -0.2, 0.1],
            "fpi_proxy": [1.0, 0.935, 0.54, 0.495, 1.0],
            "risk_label": ["high", "high", "medium", "medium", "high"],
        }
    )

    dataset = build_supervised_sequences(windows, history_windows=3, horizon_windows=1)

    assert len(dataset) == 2
    assert dataset.iloc[0]["target_risk_label"] == "medium"
    assert float(dataset.iloc[0]["t00_ping_count"]) == 8.0
    assert float(dataset.iloc[0]["t02_fpi_proxy"]) == 0.54
    assert len(sequence_feature_columns(dataset)) == 33
