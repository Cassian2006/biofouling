from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_tooltip_and_map_components_exist() -> None:
    tooltip = read_text("frontend/src/components/HintTooltip.vue")
    overview_map = read_text("frontend/src/components/RiskOverviewMap.vue")
    vessel_map = read_text("frontend/src/components/VesselTrackMap.vue")
    method_drawer = read_text("frontend/src/components/MethodDrawer.vue")

    assert "hint-tooltip__bubble" in tooltip
    assert "leaflet" in overview_map.lower()
    assert "DISPLAY_SUBDIVISIONS = 1" in overview_map
    assert "leaflet" in vessel_map.lower()
    assert "FPI = 0.5" in method_drawer
    assert "RRI = 0.40" in method_drawer


def test_dashboard_and_vessel_pages_use_new_interaction_patterns() -> None:
    dashboard = read_text("frontend/src/pages/DashboardPage.vue")
    vessel = read_text("frontend/src/pages/VesselDetailPage.vue")
    router = read_text("frontend/src/router.js")
    app_shell = read_text("frontend/src/App.vue")

    assert "RiskOverviewMap" in dashboard
    assert "区域主地图" in dashboard
    assert "已接入的主要模块" not in dashboard

    assert "VesselTrackMap" in vessel
    assert "selector-input" in vessel
    assert "单船关键字段" in vessel

    assert 'redirect: "/"' in router
    assert 'to="/regional-risk"' not in app_shell


def test_app_shell_exposes_method_entry() -> None:
    app_shell = read_text("frontend/src/App.vue")

    assert "核心算法" in app_shell
    assert "MethodDrawer" in app_shell
