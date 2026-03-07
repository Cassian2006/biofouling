import pandas as pd

from scripts.build_features import build_vessel_features, prepare_ais, prepare_env


def test_build_vessel_features_keeps_extended_environment_columns() -> None:
    ais = prepare_ais(
        pd.DataFrame(
            [
                {
                    "mmsi": "123456789",
                    "timestamp": "2026-01-15T01:00:00Z",
                    "latitude": 1.20,
                    "longitude": 103.50,
                    "is_low_speed": True,
                },
                {
                    "mmsi": "123456789",
                    "timestamp": "2026-01-15T02:00:00Z",
                    "latitude": 1.21,
                    "longitude": 103.51,
                    "is_low_speed": False,
                },
            ]
        )
    )
    env = prepare_env(
        pd.DataFrame(
            [
                {
                    "timestamp": "2026-01-15T00:00:00Z",
                    "latitude": 1.20,
                    "longitude": 103.50,
                    "sst": 28.4,
                    "chlorophyll_a": 0.18,
                    "salinity": 33.1,
                    "current_u": 0.24,
                    "current_v": -0.11,
                }
            ]
        )
    )

    features = build_vessel_features(ais, env)

    assert len(features) == 1
    assert features.loc[0, "mean_sst"] == 28.4
    assert features.loc[0, "mean_chlorophyll_a"] == 0.18
    assert features.loc[0, "mean_salinity"] == 33.1
    assert features.loc[0, "mean_current_u"] == 0.24
    assert features.loc[0, "mean_current_v"] == -0.11
