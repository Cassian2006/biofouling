import pandas as pd

from backend.services.scoring import (
    current_speed_quantiles,
    default_maintenance_gap_days,
    recommendation_thresholds,
)
from scripts.build_science_calibration import build_calibration


def test_build_science_calibration_uses_env_current_speed_distribution() -> None:
    env = pd.DataFrame(
        [
            {"current_u": 0.10, "current_v": 0.00},
            {"current_u": 0.20, "current_v": 0.00},
            {"current_u": 0.30, "current_v": 0.00},
            {"current_u": 0.40, "current_v": 0.00},
        ]
    )

    calibration = build_calibration(env, "demo-window", 75.0)

    assert calibration["window_label"] == "demo-window"
    assert calibration["maintenance"]["default_gap_days"] == 75.0
    assert calibration["current_speed_quantiles"]["p25"] == 0.175
    assert calibration["current_speed_quantiles"]["p50"] == 0.25
    assert calibration["current_speed_quantiles"]["p75"] == 0.325
    assert calibration["current_speed_quantiles"]["max"] == 0.4


def test_runtime_science_calibration_loads_from_config() -> None:
    quantiles = current_speed_quantiles()
    thresholds = recommendation_thresholds()

    assert quantiles["p25"] == 0.1745
    assert quantiles["p50"] == 0.249
    assert thresholds["fpi_prioritize"] == 0.25
    assert thresholds["ecp_monitor"] == 0.10
    assert default_maintenance_gap_days() == 90.0
