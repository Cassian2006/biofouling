from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_export_scientific_statement_script_contains_key_sections() -> None:
    text = read_text("scripts/export_scientific_statement_html.ps1")

    assert "\u79d1\u5b66\u6027\u8bf4\u660e\u6b63\u5f0f\u6750\u6599" in text
    assert "\u884c\u4e3a\u4e3b\u5bfc" in text
    assert "\u6b63\u5f0f\u78b3\u6838\u7b97" in text
    assert "\u533a\u57df\u7efc\u5408\u98ce\u9669\u56fe\u5c42" in text
    assert "scientific_statement.html" in text
