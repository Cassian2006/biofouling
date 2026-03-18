from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from backend.services.scoring import recommendation_thresholds


COMPONENT_COLUMNS = {
    "temperature": "temperature_score",
    "salinity": "salinity_score",
    "productivity": "productivity_score",
    "hydrodynamic": "hydrodynamic_score",
}


@dataclass(frozen=True)
class ScienceScenario:
    name: str
    label: str
    env_weights: dict[str, float]
    env_base: float = 0.85
    env_span: float = 0.30
    maintenance_base: float = 0.90
    maintenance_span: float = 0.20
    carbon_alpha: float = 0.18
    carbon_beta: float = 0.12


def normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("Scenario weights must sum to a positive value.")
    return {key: value / total for key, value in weights.items()}


def scenario_env_modifier(frame: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    normalized = normalize_weights(weights)
    modifier = pd.Series(0.0, index=frame.index, dtype=float)
    for component, weight in normalized.items():
        column = COMPONENT_COLUMNS[component]
        modifier = modifier + frame[column].fillna(0.0) * weight
    return modifier.clip(lower=0.0, upper=1.0).round(4)


def scenario_recommendation(fpi_score: float, ecp_score: float) -> str:
    thresholds = recommendation_thresholds()
    if (
        fpi_score >= thresholds["fpi_prioritize"]
        or ecp_score >= thresholds["ecp_prioritize"]
    ):
        return "Prioritize cleaning assessment"
    if fpi_score >= thresholds["fpi_monitor"] or ecp_score >= thresholds["ecp_monitor"]:
        return "Monitor exposure trend"
    return "Low immediate concern"


def apply_science_scenario(frame: pd.DataFrame, scenario: ScienceScenario) -> pd.DataFrame:
    required_columns = {
        "mmsi",
        "behavior_score",
        "maintenance_score",
        "persistent_exposure_score",
        *COMPONENT_COLUMNS.values(),
    }
    missing = required_columns.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns for science validation: {sorted(missing)}")

    scored = frame.copy()
    scored["scenario_name"] = scenario.name
    scored["scenario_label"] = scenario.label
    scored["environment_modifier"] = scenario_env_modifier(scored, scenario.env_weights)
    scored["environment_multiplier"] = (
        scenario.env_base + scenario.env_span * scored["environment_modifier"]
    ).round(4)
    scored["maintenance_multiplier"] = (
        scenario.maintenance_base + scenario.maintenance_span * scored["maintenance_score"].fillna(0.0)
    ).round(4)
    scored["fpi_score"] = (
        scored["behavior_score"].fillna(0.0)
        * scored["environment_multiplier"]
        * scored["maintenance_multiplier"]
    ).clip(lower=0.0, upper=1.5).round(4)
    scored["carbon_penalty_multiplier"] = (
        1.0
        + scenario.carbon_alpha * scored["maintenance_score"].fillna(0.0)
        + scenario.carbon_beta * scored["persistent_exposure_score"].fillna(0.0)
    ).round(4)
    scored["ecp_score"] = (
        scored["fpi_score"] * scored["carbon_penalty_multiplier"]
    ).clip(lower=0.0, upper=1.5).round(4)
    scored["recommendation"] = [
        scenario_recommendation(fpi, ecp)
        for fpi, ecp in zip(scored["fpi_score"], scored["ecp_score"], strict=False)
    ]
    return scored


def top_k_overlap(
    baseline: pd.DataFrame,
    candidate: pd.DataFrame,
    *,
    score_column: str = "fpi_score",
    k: int = 20,
) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    baseline_top = set(
        baseline.sort_values(score_column, ascending=False)["mmsi"].astype(str).head(k)
    )
    candidate_top = set(
        candidate.sort_values(score_column, ascending=False)["mmsi"].astype(str).head(k)
    )
    if not baseline_top and not candidate_top:
        return 1.0
    return round(len(baseline_top.intersection(candidate_top)) / float(k), 4)


def summarize_scenario_shift(
    baseline: pd.DataFrame,
    candidate: pd.DataFrame,
    *,
    label: str,
    kind: str,
) -> dict[str, float | str]:
    merged = baseline[["mmsi", "fpi_score", "ecp_score", "recommendation"]].merge(
        candidate[["mmsi", "fpi_score", "ecp_score", "recommendation"]],
        on="mmsi",
        suffixes=("_baseline", "_candidate"),
    )
    recommendation_changed = (
        merged["recommendation_baseline"] != merged["recommendation_candidate"]
    ).mean()
    return {
        "scenario_label": label,
        "scenario_kind": kind,
        "mean_fpi_shift": round(
            float((merged["fpi_score_candidate"] - merged["fpi_score_baseline"]).mean()), 4
        ),
        "mean_ecp_shift": round(
            float((merged["ecp_score_candidate"] - merged["ecp_score_baseline"]).mean()), 4
        ),
        "top20_overlap": top_k_overlap(baseline, candidate, k=20),
        "top50_overlap": top_k_overlap(baseline, candidate, k=50),
        "recommendation_change_rate": round(float(recommendation_changed), 4),
        "prioritize_count": int(
            (candidate["recommendation"] == "Prioritize cleaning assessment").sum()
        ),
        "monitor_count": int(
            (candidate["recommendation"] == "Monitor exposure trend").sum()
        ),
        "low_concern_count": int(
            (candidate["recommendation"] == "Low immediate concern").sum()
        ),
    }


def default_sensitivity_scenarios() -> list[ScienceScenario]:
    return [
        ScienceScenario(
            name="baseline",
            label="当前科学评分",
            env_weights={
                "temperature": 0.40,
                "salinity": 0.20,
                "productivity": 0.25,
                "hydrodynamic": 0.15,
            },
        ),
        ScienceScenario(
            name="temp_up",
            label="温度权重上调",
            env_weights={
                "temperature": 0.45,
                "salinity": 0.15,
                "productivity": 0.25,
                "hydrodynamic": 0.15,
            },
        ),
        ScienceScenario(
            name="productivity_up",
            label="叶绿素权重上调",
            env_weights={
                "temperature": 0.35,
                "salinity": 0.20,
                "productivity": 0.30,
                "hydrodynamic": 0.15,
            },
        ),
        ScienceScenario(
            name="env_narrow",
            label="环境修正收窄",
            env_weights={
                "temperature": 0.40,
                "salinity": 0.20,
                "productivity": 0.25,
                "hydrodynamic": 0.15,
            },
            env_base=0.90,
            env_span=0.20,
        ),
        ScienceScenario(
            name="env_wide",
            label="环境修正放宽",
            env_weights={
                "temperature": 0.40,
                "salinity": 0.20,
                "productivity": 0.25,
                "hydrodynamic": 0.15,
            },
            env_base=0.80,
            env_span=0.40,
        ),
        ScienceScenario(
            name="maintenance_soft",
            label="维护修正减弱",
            env_weights={
                "temperature": 0.40,
                "salinity": 0.20,
                "productivity": 0.25,
                "hydrodynamic": 0.15,
            },
            maintenance_base=0.95,
            maintenance_span=0.10,
        ),
        ScienceScenario(
            name="maintenance_strong",
            label="维护修正加强",
            env_weights={
                "temperature": 0.40,
                "salinity": 0.20,
                "productivity": 0.25,
                "hydrodynamic": 0.15,
            },
            maintenance_base=0.85,
            maintenance_span=0.30,
        ),
    ]


def default_ablation_scenarios() -> list[ScienceScenario]:
    return [
        ScienceScenario(
            name="no_temperature",
            label="去除温度分量",
            env_weights={"salinity": 0.20, "productivity": 0.25, "hydrodynamic": 0.15},
        ),
        ScienceScenario(
            name="no_salinity",
            label="去除盐度分量",
            env_weights={"temperature": 0.40, "productivity": 0.25, "hydrodynamic": 0.15},
        ),
        ScienceScenario(
            name="no_productivity",
            label="去除叶绿素分量",
            env_weights={"temperature": 0.40, "salinity": 0.20, "hydrodynamic": 0.15},
        ),
        ScienceScenario(
            name="no_hydrodynamic",
            label="去除水动力分量",
            env_weights={"temperature": 0.40, "salinity": 0.20, "productivity": 0.25},
        ),
    ]
