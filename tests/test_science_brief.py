import pandas as pd

from scripts.build_science_brief import (
    classify_priority,
    plain_language_takeaways,
    render_html_report,
    render_scientific_statement_html,
)


def test_classify_priority_uses_three_clear_bands() -> None:
    assert classify_priority(0.75) == "优先评估"
    assert classify_priority(0.12) == "持续监测"
    assert classify_priority(0.05) == "当前较低"


def test_plain_language_takeaways_include_score_shift_summary() -> None:
    takeaways = plain_language_takeaways(
        {
            "legacy_fpi_mean": 0.6151,
            "scientific_fpi_mean": 0.1668,
            "legacy_ecp_mean": 0.6209,
            "scientific_ecp_mean": 0.2024,
        }
    )

    assert len(takeaways) == 6
    assert "FPI 平均值从 0.6151 变为 0.1668" in takeaways[4]
    assert "ECP 平均值从 0.6209 变为 0.2024" in takeaways[5]


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
                    "ecp_proxy_legacy": 0.82,
                    "ecp_proxy_scientific": 0.24,
                    "temperature_score": 0.6,
                    "salinity_score": 0.5,
                    "productivity_score": 0.7,
                    "hydrodynamic_score": 0.4,
                }
            ]
        ),
    )

    html_text = (tmp_path / "science_upgrade_brief.html").read_text(encoding="utf-8")
    assert "这张图是总览图" in html_text
    assert "这张图看的是整体分布" in html_text
    assert "EnvModifier = 0.40T + 0.20S + 0.25P + 0.15H" in html_text
    assert "FPI = BehaviorExposure × EnvAdj × MaintenanceAdj" in html_text


def test_render_scientific_statement_html_exports_formal_material(tmp_path) -> None:
    statement = tmp_path / "scientific_statement.md"
    statement.write_text(
        "# 科学性说明\n\n## FPI\n\n- 行为主导\n- 环境修正\n- 维护轻修正\n\n## ECP\n\n不是正式碳核算。\n",
        encoding="utf-8",
    )

    render_scientific_statement_html(tmp_path, statement)

    html_text = (tmp_path / "scientific_statement.html").read_text(encoding="utf-8")
    assert "科学性说明正式材料" in html_text
    assert "行为主导" in html_text
    assert "不是正式碳核算" in html_text
