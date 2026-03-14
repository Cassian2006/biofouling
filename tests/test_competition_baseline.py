from pathlib import Path

from backend.services.demo_data import get_competition_baseline_manifest, load_demo_payload


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_competition_baseline_manifest_exists_and_points_to_real_artifacts() -> None:
    manifest = get_competition_baseline_manifest()

    assert manifest["version"] == "competition_main_v1"
    assert manifest["status"] == "frozen"
    assert manifest["window_label"] == "20260115 to 20260130"

    resolved_artifacts = manifest["resolved_artifacts"]
    assert "vessel_features" in resolved_artifacts
    assert "regional_risk" in resolved_artifacts
    assert "voyage_report" in resolved_artifacts

    for artifact_path in resolved_artifacts.values():
        assert Path(artifact_path).exists()


def test_demo_payload_uses_frozen_competition_window() -> None:
    payload = load_demo_payload()

    assert payload["window_label"] == "20260115 to 20260130"
    assert payload["summary"].vessels_summarized == 637
    assert payload["summary"].grid_cells == 1143
