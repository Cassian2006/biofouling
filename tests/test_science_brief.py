import pandas as pd

from scripts.build_science_brief import (
    classify_priority,
    plain_language_takeaways,
    render_html_report,
)


def test_classify_priority_uses_three_clear_bands() -> None:
    assert classify_priority(0.75) == "优先评估"
    assert classify_priority(0.45) == "持续监测"
    assert classify_priority(0.2) == "当前较低"


def test_plain_language_takeaways_include_score_shift_summary() -> None:
    takeaways = plain_language_takeaways(
        {
            "legacy_fpi_mean": 0.6151,
            "scientific_fpi_mean": 0.1668,
            "legacy_ecp_mean": 0.6209,
            "scientific_ecp_mean": 0.2024,
        }
    )

    assert len(takeaways) == 5
    assert "FPI 平均值从 0.6151 降到 0.1668" in takeaways[3]
    assert "ECP 平均值从 0.6209 降到 0.2024" in takeaways[4]


def test_render_html_report_includes_figure_notes(tmp_path) -> None:
    render_html_report(
        tmp_path,
        {
            "legacy_fpi_mean": 0.6151,
            "scientific_fpi_mean": 0.1668,
            "legacy_ecp_mean": 0.6209,
            "scientific_ecp_mean": 0.2024,
        },
        ["测试要点"],
        {
            "legacy": {"优先评估": 10, "持续监测": 20, "当前较低": 5},
            "scientific": {"优先评估": 4, "持续监测": 18, "当前较低": 13},
        },
        pd.DataFrame(
            [
                {
                    "mmsi": "123456789",
                    "fpi_proxy_legacy": 0.8,
                    "fpi_proxy_scientific": 0.2,
                    "fpi_delta": -0.6,
                    "behavior_score": 0.4,
                    "environment_score": 0.7,
                }
            ]
        ),
    )

    html_text = (tmp_path / "science_upgrade_brief.html").read_text(encoding="utf-8")
    assert "这张图是总览图" in html_text
    assert "这张图看的是整体分布" in html_text
    assert "EnvModifier = 0.40T + 0.20S + 0.25P + 0.15H" in html_text
    assert "FPI = BehaviorExposure × (0.7 + 0.3 × EnvModifier)" in html_text
