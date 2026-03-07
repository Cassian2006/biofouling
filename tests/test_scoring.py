from backend.schemas.scoring import ScoreEstimateRequest
from backend.services.scoring import (
    behavior_score,
    compute_ecp,
    compute_fpi,
    compute_rri,
    estimate_scores,
    recommend_action,
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
        mean_chlorophyll_a=0.8,
        traffic_density_index=0.7,
        anchorage_exposure_index=0.6,
    )


def test_component_scores_are_bounded_and_consistent() -> None:
    payload = build_payload()
    fpi, components = compute_fpi(payload)
    ecp = compute_ecp(payload, fpi)
    rri = compute_rri(payload, components)

    assert 0 <= behavior_score(payload) <= 1
    assert 0 <= components.behavior_score <= 1
    assert 0 <= components.environment_score <= 1
    assert 0 <= components.maintenance_score <= 1
    assert 0 <= fpi <= 1
    assert 0 <= ecp <= 1.5
    assert 0 <= rri <= 1


def test_estimate_scores_returns_high_priority_for_high_exposure_case() -> None:
    payload = build_payload()
    result = estimate_scores(payload)

    assert result.vessel_id == "demo-vessel"
    assert result.fpi_score == 0.5473
    assert result.ecp_score == 0.7115
    assert result.rri_score == 0.5895
    assert result.recommendation == "Monitor exposure trend"


def test_recommend_action_thresholds_cover_three_bands() -> None:
    assert recommend_action(0.75, 0.4) == "Prioritize cleaning assessment"
    assert recommend_action(0.3, 0.9) == "Prioritize cleaning assessment"
    assert recommend_action(0.45, 0.4) == "Monitor exposure trend"
    assert recommend_action(0.2, 0.6) == "Monitor exposure trend"
    assert recommend_action(0.1, 0.2) == "Low immediate concern"
