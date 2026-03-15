import pandas as pd

from scripts.build_features import build_vessel_features, prepare_ais, prepare_env


def test_build_vessel_features_outputs_scientific_and_legacy_scores() -> None:
    ais = prepare_ais(
        pd.DataFrame(
            [
                {
                    "mmsi": "123456789",
                    "timestamp": "2026-01-15T01:00:00Z",
                    "latitude": 1.20,
                    "longitude": 103.50,
                    "is_low_speed": True,
                    "nav_status": 1,
                },
                {
                    "mmsi": "123456789",
                    "timestamp": "2026-01-15T02:00:00Z",
                    "latitude": 1.21,
                    "longitude": 103.51,
                    "is_low_speed": False,
                    "nav_status": 5,
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
    assert features.loc[0, "anchor_hours"] == 1.0
    assert features.loc[0, "dwell_hours"] == 1.0
    assert features.loc[0, "low_speed_hours"] == 1.0
    assert features.loc[0, "fpi_proxy_legacy"] == 0.3
    assert features.loc[0, "ecp_proxy_legacy"] == 0.36
    assert features.loc[0, "temperature_score"] > 0
    assert features.loc[0, "salinity_score"] > 0
    assert features.loc[0, "hydrodynamic_score"] > 0
    assert features.loc[0, "fpi_proxy"] >= 0
    assert features.loc[0, "ecp_proxy"] >= 0
