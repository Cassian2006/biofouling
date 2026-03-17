from backend.schemas.scoring import ScoreEstimateRequest
from backend.services.scoring import (
    behavior_score,
    compute_ecp,
    compute_fpi,
    compute_rri,
    current_speed,
    estimate_scores,
    hydrodynamic_attachment_score,
    maintenance_multiplier,
    productivity_pressure,
    recommend_action,
    salinity_suitability,
    sst_suitability,
)


def build_payload() -> ScoreEstimateRequest:
    return ScoreEstimateRequest(
        vessel_id="demo-vessel",
        dwell_hours=48,
        anchor_hours=36,
        low_speed_hours=60,
        port_visits=4,
        maintenance_gap_days=120,
        mean_sst=28.5,
        mean_salinity=32.0,
        mean_chlorophyll_a=0.8,
        mean_current_u=0.24,
        mean_current_v=-0.11,
        traffic_density_index=0.7,
        anchorage_exposure_index=0.6,
    )


def test_environment_response_functions_follow_piecewise_shapes() -> None:
    assert sst_suitability(16.0) < sst_suitability(24.0) < sst_suitability(28.0)
    assert sst_suitability(28.0) >= sst_suitability(32.0) > sst_suitability(36.0)

    assert salinity_suitability(18.0) < salinity_suitability(26.0) < salinity_suitability(32.0)
    assert salinity_suitability(32.0) >= salinity_suitability(36.0) > salinity_suitability(40.0)

    assert productivity_pressure(0.2) < productivity_pressure(1.0) < productivity_pressure(4.0)
    assert productivity_pressure(8.0) == productivity_pressure(12.0)


def test_hydrodynamic_score_uses_current_speed_not_direction_components() -> None:
    score, speed = hydrodynamic_attachment_score(0.24, -0.11)

    assert current_speed(0.24, -0.11) == 0.264
    assert speed == 0.264
    assert 0 <= score <= 1


def test_component_scores_are_bounded_and_consistent() -> None:
    payload = build_payload()
    fpi, components = compute_fpi(payload)
    ecp = compute_ecp(payload, fpi, components)
    rri = compute_rri(payload, components)

    assert 0 <= behavior_score(payload) <= 1
    assert 0 <= components.behavior_score <= 1
    assert 0 <= components.temperature_score <= 1
    assert 0 <= components.salinity_score <= 1
    assert 0 <= components.productivity_score <= 1
    assert 0 <= components.hydrodynamic_score <= 1
    assert 0 <= components.environment_score <= 1
    assert 0.85 <= components.environment_multiplier <= 1.15
    assert 0 <= components.maintenance_score <= 1
    assert 0.9 <= components.maintenance_multiplier <= 1.1
    assert 0 <= components.stay_probability_score <= 1
    assert 0 <= components.port_anchorage_score <= 1
    assert 0 <= components.persistent_exposure_score <= 1
    assert 1.0 <= components.carbon_penalty_multiplier <= 1.3
    assert 0 <= fpi <= 1
    assert 0 <= ecp <= 1.5
    assert 0 <= rri <= 1


def test_estimate_scores_returns_expected_scientific_baseline_case() -> None:
    payload = build_payload()
    result = estimate_scores(payload)

    assert result.vessel_id == "demo-vessel"
    assert result.fpi_score == 0.5211
    assert result.ecp_score == 0.6086
    assert result.rri_score == 0.6254
    assert result.components.temperature_score == 0.9375
    assert result.components.salinity_score == 0.9357
    assert result.components.productivity_score == 0.24
    assert result.components.hydrodynamic_score == 0.701
    assert result.components.environment_score == 0.7273
    assert result.components.environment_multiplier == 1.0682
    assert result.components.maintenance_multiplier == 1.0333
    assert result.components.carbon_penalty_multiplier == 1.168
    assert result.recommendation == "Prioritize cleaning assessment"


def test_recommend_action_thresholds_cover_three_bands() -> None:
    assert recommend_action(0.75, 0.2) == "Prioritize cleaning assessment"
    assert recommend_action(0.1, 0.9) == "Prioritize cleaning assessment"
    assert recommend_action(0.2, 0.13) == "Monitor exposure trend"
    assert recommend_action(0.07, 0.2) == "Monitor exposure trend"
    assert recommend_action(0.05, 0.08) == "Low immediate concern"


def test_environment_can_enhance_behavior_and_maintenance_remains_in_fpi() -> None:
    payload = build_payload()
    fpi, components = compute_fpi(payload)

    assert components.environment_multiplier > 1.0
    assert maintenance_multiplier(payload) > 1.0
    assert fpi > behavior_score(payload)
