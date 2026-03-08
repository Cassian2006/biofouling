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
    assert "交通疏密" in method_drawer
    assert "低速停留" in method_drawer
    assert "水域情况" in method_drawer
    assert "训练样本使用最近 8 个连续窗口作为输入" in method_drawer
    assert "当前前端使用的校准阈值为 0.53 / 0.69" in method_drawer


def test_dashboard_and_vessel_pages_use_new_interaction_patterns() -> None:
    dashboard = read_text("frontend/src/pages/DashboardPage.vue")
    vessel = read_text("frontend/src/pages/VesselDetailPage.vue")
    router = read_text("frontend/src/router.js")
    app_shell = read_text("frontend/src/App.vue")

    assert "RiskOverviewMap" in dashboard
    assert "区域主地图" in dashboard
    assert "已接入的主要模块" not in dashboard
    assert "交通疏密" in dashboard
    assert "低速停留" in dashboard
    assert "水域情况" in dashboard
    assert "异常暴露筛查" in dashboard
    assert "异常船舶榜单" in dashboard
    assert "最高优先级船舶" in dashboard
    assert "需复核" in dashboard
    assert "长时低速型" in dashboard
    assert "观测稀疏型" in dashboard

    assert "VesselTrackMap" in vessel
    assert "selector-input" in vessel
    assert "简要结论" in vessel
    assert "历史-当前-预测链路" in vessel
    assert "定位全轨迹" in read_text("frontend/src/components/VesselTrackMap.vue")

    assert 'redirect: "/"' in router
    assert 'to="/regional-risk"' not in app_shell


def test_app_shell_exposes_method_entry() -> None:
    app_shell = read_text("frontend/src/App.vue")

    assert "核心算法" in app_shell
    assert "MethodDrawer" in app_shell
