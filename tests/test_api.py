from pathlib import Path

from fastapi.testclient import TestClient

import backend.main as backend_main


client = TestClient(backend_main.app)


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}


def test_demo_summary_endpoint_returns_real_counts() -> None:
    response = client.get("/api/demo/summary")
    payload = response.json()

    assert response.status_code == 200
    assert payload["vessels_summarized"] == 52
    assert payload["grid_cells"] == 642
    assert payload["high_risk_cells"] == 1
    assert payload["medium_risk_cells"] == 31


def test_vessel_detail_track_and_trend_endpoints_return_real_payloads() -> None:
    detail_response = client.get("/api/demo/vessels/268240302")
    track_response = client.get("/api/demo/vessels/268240302/track")
    trend_response = client.get("/api/demo/vessels/268240302/trend")
    report_response = client.get("/api/demo/reports/vessels/268240302")

    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["rank_fraction"] == "1 / 52"
    assert detail_payload["vessel"]["mean_salinity"] is not None
    assert detail_payload["vessel"]["mean_current_u"] is not None
    assert detail_payload["static_profile"]["profile_source"] == "ais_derived"
    assert detail_payload["validation_summary"]["event_count"] == 0
    assert detail_payload["nearest_reference"] is not None
    assert detail_payload["nearest_reference_distance_km"] is not None

    track_payload = track_response.json()
    assert track_response.status_code == 200
    assert track_payload["mmsi"] == "268240302"
    assert track_payload["point_count"] == 1146
    assert track_payload["rendered_point_count"] == 320
    assert track_payload["points"][0]["timestamp"].startswith("2026-01-15T00:00:36")

    trend_payload = trend_response.json()
    assert trend_response.status_code == 200
    assert trend_payload["interval_hours"] == 6
    assert len(trend_payload["windows"]) == 11
    assert trend_payload["max_point_count"] == 119

    assert report_response.status_code == 200
    assert report_response.json()["scope"] == "vessel"


def test_regional_endpoints_return_expected_distribution() -> None:
    stats_response = client.get("/api/demo/regional-stats")
    cells_response = client.get("/api/demo/risk-cells")

    stats_payload = stats_response.json()
    cells_payload = cells_response.json()

    assert stats_response.status_code == 200
    assert stats_payload["total_cells"] == 642
    assert stats_payload["risk_level_counts"] == {"high": 1, "medium": 31, "low": 610}
    assert len(stats_payload["reference_sites"]) == 8
    assert stats_payload["reference_sites"][0]["site_type"] in {"port", "anchorage"}

    assert cells_response.status_code == 200
    assert len(cells_payload) == 642
    assert cells_payload[0]["grid_lat"] == 1.275
    assert cells_payload[0]["grid_lon"] == 103.775
    assert cells_payload[0]["rri_score"] == 0.709
    assert cells_payload[0]["traffic_score"] == 1.0
    assert cells_payload[0]["nearest_reference_name"] is not None


def test_unknown_api_route_returns_404() -> None:
    response = client.get("/api/unknown")

    assert response.status_code == 404


def test_spa_routes_return_index_when_dist_exists(tmp_path, monkeypatch) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    index_file = dist_dir / "index.html"
    index_file.write_text("<html><body>frontend-app</body></html>", encoding="utf-8")

    monkeypatch.setattr(backend_main, "FRONTEND_DIST_DIR", dist_dir)

    root_response = client.get("/")
    route_response = client.get("/regional-risk")

    assert root_response.status_code == 200
    assert "frontend-app" in root_response.text
    assert route_response.status_code == 200
    assert "frontend-app" in route_response.text
