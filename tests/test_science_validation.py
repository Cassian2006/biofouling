import pandas as pd

from backend.services.science_validation import (
    ScienceScenario,
    apply_science_scenario,
    scenario_env_modifier,
    summarize_scenario_shift,
    top_k_overlap,
)


def sample_feature_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "mmsi": "1001",
                "behavior_score": 0.70,
                "maintenance_score": 0.40,
                "persistent_exposure_score": 0.50,
                "temperature_score": 0.90,
                "salinity_score": 0.80,
                "productivity_score": 0.60,
                "hydrodynamic_score": 0.70,
            },
            {
                "mmsi": "1002",
                "behavior_score": 0.50,
                "maintenance_score": 0.20,
                "persistent_exposure_score": 0.20,
                "temperature_score": 0.40,
                "salinity_score": 0.60,
                "productivity_score": 0.30,
                "hydrodynamic_score": 0.90,
            },
            {
                "mmsi": "1003",
                "behavior_score": 0.30,
                "maintenance_score": 0.10,
                "persistent_exposure_score": 0.10,
                "temperature_score": 0.20,
                "salinity_score": 0.30,
                "productivity_score": 0.20,
                "hydrodynamic_score": 0.40,
            },
        ]
    )


def test_scenario_env_modifier_normalizes_weights() -> None:
    frame = sample_feature_frame()
    modifier = scenario_env_modifier(
        frame,
        {
            "temperature": 4.0,
            "salinity": 2.0,
            "productivity": 2.5,
            "hydrodynamic": 1.5,
        },
    )
    assert modifier.round(4).tolist() == [0.775, 0.49, 0.25]


def test_apply_science_scenario_produces_scores_and_labels() -> None:
    frame = sample_feature_frame()
    scenario = ScienceScenario(
        name="baseline",
        label="Current science-v2",
        env_weights={
            "temperature": 0.40,
            "salinity": 0.20,
            "productivity": 0.25,
            "hydrodynamic": 0.15,
        },
    )
    scored = apply_science_scenario(frame, scenario)
    assert list(scored["scenario_name"].unique()) == ["baseline"]
    assert scored.loc[0, "fpi_score"] > scored.loc[1, "fpi_score"] > scored.loc[2, "fpi_score"]
    assert set(scored["recommendation"]).issubset(
        {
            "Prioritize cleaning assessment",
            "Monitor exposure trend",
            "Low immediate concern",
        }
    )


def test_top_k_overlap_and_shift_summary() -> None:
    baseline = pd.DataFrame(
        {
            "mmsi": ["a", "b", "c", "d"],
            "fpi_score": [0.9, 0.8, 0.4, 0.1],
            "ecp_score": [1.0, 0.85, 0.42, 0.12],
            "recommendation": [
                "Prioritize cleaning assessment",
                "Prioritize cleaning assessment",
                "Monitor exposure trend",
                "Low immediate concern",
            ],
        }
    )
    candidate = pd.DataFrame(
        {
            "mmsi": ["a", "c", "b", "d"],
            "fpi_score": [0.88, 0.72, 0.70, 0.08],
            "ecp_score": [0.96, 0.74, 0.73, 0.10],
            "recommendation": [
                "Prioritize cleaning assessment",
                "Prioritize cleaning assessment",
                "Prioritize cleaning assessment",
                "Monitor exposure trend",
            ],
        }
    )
    assert top_k_overlap(baseline, candidate, k=2) == 0.5
    summary = summarize_scenario_shift(baseline, candidate, label="candidate", kind="test")
    assert summary["scenario_label"] == "candidate"
    assert summary["scenario_kind"] == "test"
    assert summary["top20_overlap"] == 0.2
    assert summary["recommendation_change_rate"] == 0.5
