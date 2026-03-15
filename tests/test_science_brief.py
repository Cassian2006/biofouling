from scripts.build_science_brief import classify_priority, plain_language_takeaways


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
