from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_info_disclosure_component_exists() -> None:
    content = read_text("frontend/src/components/InfoDisclosure.vue")

    assert "<details" in content
    assert "展开说明" in content


def test_core_pages_use_collapsible_explanations() -> None:
    dashboard = read_text("frontend/src/pages/DashboardPage.vue")
    vessel = read_text("frontend/src/pages/VesselDetailPage.vue")
    regional = read_text("frontend/src/pages/RegionalRiskPage.vue")

    assert "InfoDisclosure" in dashboard
    assert "页面说明" in dashboard

    assert "InfoDisclosure" in vessel
    assert "轨迹判读说明" in vessel
    assert "趋势判读说明" in vessel

    assert "InfoDisclosure" in regional
    assert "图层判读说明" in regional
    assert "地图说明" in regional
