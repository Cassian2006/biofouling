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
    assert payload["window_label"] == "20260115 to 20260130"
    assert payload["vessels_summarized"] == 637
    assert payload["grid_cells"] == 1143
    assert payload["high_risk_cells"] == 1
    assert payload["medium_risk_cells"] == 78


def test_vessel_detail_track_and_trend_endpoints_return_real_payloads() -> None:
    detail_response = client.get("/api/demo/vessels/268240302")
    track_response = client.get("/api/demo/vessels/268240302/track")
    trend_response = client.get("/api/demo/vessels/268240302/trend")
    forecast_response = client.get("/api/demo/vessels/268240302/forecast")
    anomaly_response = client.get("/api/demo/vessels/268240302/anomaly")
    report_response = client.get("/api/demo/reports/vessels/268240302")

    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["rank_fraction"] == "3 / 637"
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

    forecast_payload = forecast_response.json()
    assert forecast_response.status_code == 200
    assert forecast_payload["mmsi"] == "268240302"
    assert forecast_payload["available"] is True
    assert forecast_payload["predicted_fpi"] >= 0
    assert forecast_payload["predicted_risk_label"] in {"low", "medium", "high"}
    assert forecast_payload["raw_predicted_risk_label"] in {"low", "medium", "high"}
    assert forecast_payload["model_name"].startswith("fpi_lstm_")
    assert len(forecast_payload["signals"]) >= 1
    assert len(forecast_payload["history_points"]) == 8

    anomaly_payload = anomaly_response.json()
    assert anomaly_response.status_code == 200
    assert anomaly_payload["mmsi"] == "268240302"
    assert anomaly_payload["anomaly_level"] in {"normal", "suspicious", "highly_abnormal", "observation_insufficient"}
    assert anomaly_payload["anomaly_score"] >= 0
    assert anomaly_payload["anomaly_type"] in {
        "long_dwell_low_speed",
        "warm_productive_water",
        "mixed_anomaly",
        "sparse_observation",
    }
    assert anomaly_payload["anomaly_type_label"]
    assert anomaly_payload["anomaly_type_summary"]
    assert anomaly_payload["anomaly_severity"]
    assert anomaly_payload["dominant_evidence_title"]
    assert anomaly_payload["dominant_evidence_summary"]
    assert anomaly_payload["summary_sentence"]
    assert isinstance(anomaly_payload["driver_details"], list)
    assert len(anomaly_payload["peer_anomalies"]) <= 6

    assert report_response.status_code == 200
    assert report_response.json()["scope"] == "vessel"


def test_vessel_forecast_endpoint_reports_unavailable_when_history_is_insufficient() -> None:
    response = client.get("/api/demo/vessels/209594000/forecast")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mmsi"] == "209594000"
    assert payload["available"] is False
    assert payload["predicted_fpi"] is None
    assert payload["history_points"] == []
    assert "连续历史窗口" in payload["unavailable_reason"]


def test_regional_endpoints_return_expected_distribution() -> None:
    stats_response = client.get("/api/demo/regional-stats")
    cells_response = client.get("/api/demo/risk-cells")
    anomaly_response = client.get("/api/demo/anomalies")

    stats_payload = stats_response.json()
    cells_payload = cells_response.json()
    anomaly_payload = anomaly_response.json()

    assert stats_response.status_code == 200
    assert stats_payload["window_label"] == "20260115 to 20260130"
    assert stats_payload["total_cells"] == 1143
    assert stats_payload["risk_level_counts"] == {"high": 1, "medium": 78, "low": 1064}
    assert len(stats_payload["reference_sites"]) == 8
    assert stats_payload["reference_sites"][0]["site_type"] in {"port", "anchorage"}

    assert cells_response.status_code == 200
    assert len(cells_payload) == 1143
    assert cells_payload[0]["grid_lat"] == 1.275
    assert cells_payload[0]["grid_lon"] == 103.775
    assert cells_payload[0]["rri_score"] == 0.712
    assert cells_payload[0]["traffic_score"] == 1.0
    assert cells_payload[0]["nearest_reference_name"] is not None

    assert anomaly_response.status_code == 200
    assert anomaly_payload["vessel_count"] == 637
    assert anomaly_payload["anomaly_level_counts"] == {
        "highly_abnormal": 16,
        "suspicious": 70,
        "normal": 400,
        "observation_insufficient": 151,
    }
    assert set(anomaly_payload["anomaly_type_counts"].keys()) == {
        "long_dwell_low_speed",
        "warm_productive_water",
        "mixed_anomaly",
        "sparse_observation",
    }
    assert anomaly_payload["top_anomalies"][0]["mmsi"] == "563215100"
    assert anomaly_payload["top_anomalies"][0]["summary_sentence"]
    assert anomaly_payload["top_anomalies"][0]["anomaly_type_label"]
    assert anomaly_payload["top_anomalies"][0]["anomaly_severity"]
    assert anomaly_payload["top_anomalies"][0]["dominant_evidence"]
    assert all(item["anomaly_level"] != "observation_insufficient" for item in anomaly_payload["top_anomalies"])


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
