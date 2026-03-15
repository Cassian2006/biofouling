from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_scientific_statement_covers_requested_boundaries() -> None:
    text = read_text("docs/scientific_statement.md")

    assert "行为主导、环境修正、维护轻修正" in text
    assert "正式碳核算" in text
    assert "区域综合风险图层" in text
    assert "LSTM" in text
    assert "异常检测" in text
    assert "哪些对象能预测" in text
    assert "启发式近似" in text
    assert "这部分我们做了吗" in text


def test_parameter_sources_classifies_mechanism_and_heuristic_parts() -> None:
    text = read_text("docs/parameter_sources.md")

    assert "机制/文献方向支撑" in text
    assert "工程启发式" in text
    assert "平台内部校准" in text
    assert "BehaviorExposure × EnvAdj × MaintenanceAdj" in text
    assert "ECP = FPI × CarbonPenaltyModifier" in text


def test_scientific_review_preserves_scope_boundaries() -> None:
    text = read_text("docs/scientific_review.md")

    assert "可解释的相对风险排序平台" in text
    assert "不应被表述为" in text
    assert "真实污损地图" in text
    assert "正式碳核算" in text
