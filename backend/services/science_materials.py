from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from backend.schemas.demo import (
    ScienceMaterialsResponse,
    ScienceStatementSection,
    ScienceValidationSummaryResponse,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = PROJECT_ROOT / "docs"
SCIENCE_VALIDATION_PATH = PROJECT_ROOT / "outputs" / "science_validation" / "science_validation_summary.json"
SCIENTIFIC_STATEMENT_PATH = DOCS_DIR / "scientific_statement.md"


def _clean_line(value: str) -> str:
    return value.strip().lstrip("-").strip()


@lru_cache(maxsize=1)
def load_science_validation_summary() -> ScienceValidationSummaryResponse:
    if not SCIENCE_VALIDATION_PATH.exists():
        return ScienceValidationSummaryResponse(
            baseline_label="当前科学评分",
            baseline_recommendation_counts={},
            sensitivity_scenarios=0,
            ablation_scenarios=0,
            most_stable_sensitivity=None,
            most_disruptive_ablation=None,
            highest_recommendation_change_sensitivity=None,
        )
    payload = json.loads(SCIENCE_VALIDATION_PATH.read_text(encoding="utf-8"))
    return ScienceValidationSummaryResponse(**payload)


def _parse_scientific_statement() -> tuple[str, str, list[ScienceStatementSection]]:
    if not SCIENTIFIC_STATEMENT_PATH.exists():
        return "科学性说明", "", []

    title = "科学性说明"
    intro_lines: list[str] = []
    sections: list[ScienceStatementSection] = []
    current_title: str | None = None
    current_paragraphs: list[str] = []
    seen_first_section = False

    for raw_line in SCIENTIFIC_STATEMENT_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# "):
            title = _clean_line(line[2:])
            continue
        if line.startswith("## "):
            if current_title:
                sections.append(
                    ScienceStatementSection(title=current_title, paragraphs=current_paragraphs)
                )
            current_title = _clean_line(line[3:])
            current_paragraphs = []
            seen_first_section = True
            continue
        if line.startswith("### "):
            normalized = _clean_line(line[4:])
            if current_title is None:
                current_title = normalized
                current_paragraphs = []
            else:
                current_paragraphs.append(normalized)
            continue
        if line.startswith("```"):
            continue
        cleaned = _clean_line(line)
        if not seen_first_section:
            intro_lines.append(cleaned)
        elif current_title:
            current_paragraphs.append(cleaned)

    if current_title:
        sections.append(ScienceStatementSection(title=current_title, paragraphs=current_paragraphs))
    return title, " ".join(intro_lines), sections


def get_science_materials() -> ScienceMaterialsResponse:
    title, intro, sections = _parse_scientific_statement()
    if not intro:
        intro = (
            "本文用于统一说明 FPI、ECP、RRI、LSTM 与异常检测的科学边界，"
            "并解释当前平台哪些部分已有机制支撑，哪些部分仍属于工程近似。"
        )
    return ScienceMaterialsResponse(
        title=title,
        intro=intro,
        sections=sections,
        validation_summary=load_science_validation_summary(),
        maintenance_note=(
            "维护项当前仍以“显式默认值 + 可选外部覆盖”的方式参与评分。若没有真实维护记录，"
            "系统会使用校准配置中的默认维护间隔，并在单船详情中明确标注来源。"
        ),
    )
