import math
import json
from functools import lru_cache
from pathlib import Path

from backend.schemas.scoring import ComponentScores, ScoreEstimateRequest, ScoreEstimateResponse

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCIENCE_CALIBRATION_PATH = PROJECT_ROOT / "config" / "science_calibration.json"


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


@lru_cache(maxsize=1)
def load_science_calibration() -> dict[str, object]:
    if not SCIENCE_CALIBRATION_PATH.exists():
        return {
            "current_speed_quantiles": {
                "p25": 0.1745,
                "p50": 0.2490,
                "p75": 0.3561,
                "p90": 0.4651,
                "max": 0.6999,
            },
            "recommendation_thresholds": {
                "fpi_prioritize": 0.25,
                "ecp_prioritize": 0.30,
                "fpi_monitor": 0.08,
                "ecp_monitor": 0.10,
            },
            "maintenance": {
                "default_gap_days": 90.0,
            },
        }
    return json.loads(SCIENCE_CALIBRATION_PATH.read_text(encoding="utf-8"))


def current_speed_quantiles() -> dict[str, float]:
    values = load_science_calibration().get("current_speed_quantiles", {})
    if not isinstance(values, dict):
        raise ValueError("Invalid current_speed_quantiles in science calibration config")
    return {
        "p25": float(values["p25"]),
        "p50": float(values["p50"]),
        "p75": float(values["p75"]),
        "p90": float(values["p90"]),
        "max": float(values["max"]),
    }


def recommendation_thresholds() -> dict[str, float]:
    values = load_science_calibration().get("recommendation_thresholds", {})
    if not isinstance(values, dict):
        raise ValueError("Invalid recommendation_thresholds in science calibration config")
    return {
        "fpi_prioritize": float(values["fpi_prioritize"]),
        "ecp_prioritize": float(values["ecp_prioritize"]),
        "fpi_monitor": float(values["fpi_monitor"]),
        "ecp_monitor": float(values["ecp_monitor"]),
    }


def default_maintenance_gap_days() -> float:
    values = load_science_calibration().get("maintenance", {})
    if not isinstance(values, dict):
        return 90.0
    return float(values.get("default_gap_days", 90.0))


def normalize_hours(hours: float, full_scale: float) -> float:
    return clamp(hours / full_scale)


def piecewise_linear(value: float, breakpoints: list[tuple[float, float]]) -> float:
    if not breakpoints:
        raise ValueError("Breakpoints must not be empty")
    if value <= breakpoints[0][0]:
        return breakpoints[0][1]
    for index in range(1, len(breakpoints)):
        x0, y0 = breakpoints[index - 1]
        x1, y1 = breakpoints[index]
        if value <= x1:
            if x1 == x0:
                return y1
            ratio = (value - x0) / (x1 - x0)
            return y0 + ratio * (y1 - y0)
    return breakpoints[-1][1]


def sst_suitability(mean_sst: float | None) -> float:
    if mean_sst is None:
        return 0.0
    breakpoints = [
        (0.0, 0.05),
        (18.0, 0.10),
        (25.0, 0.85),
        (31.0, 1.00),
        (33.0, 0.85),
        (36.0, 0.55),
        (40.0, 0.25),
    ]
    return round(clamp(piecewise_linear(mean_sst, breakpoints)), 4)


def salinity_suitability(mean_salinity: float | None) -> float:
    if mean_salinity is None:
        return 0.0
    breakpoints = [
        (0.0, 0.05),
        (20.0, 0.05),
        (28.0, 0.85),
        (35.0, 1.00),
        (38.0, 0.80),
        (42.0, 0.40),
    ]
    return round(clamp(piecewise_linear(mean_salinity, breakpoints)), 4)


def productivity_pressure(mean_chlorophyll_a: float | None) -> float:
    if mean_chlorophyll_a is None:
        return 0.0
    breakpoints = [
        (0.0, 0.05),
        (0.5, 0.15),
        (2.0, 0.60),
        (8.0, 1.00),
        (12.0, 1.00),
    ]
    return round(clamp(piecewise_linear(mean_chlorophyll_a, breakpoints)), 4)


def current_speed(mean_current_u: float | None, mean_current_v: float | None) -> float | None:
    if mean_current_u is None or mean_current_v is None:
        return None
    return round(math.sqrt(mean_current_u**2 + mean_current_v**2), 4)


def hydrodynamic_attachment_score(mean_current_u: float | None, mean_current_v: float | None) -> tuple[float, float | None]:
    speed = current_speed(mean_current_u, mean_current_v)
    if speed is None:
        return 0.0, None
    quantiles = current_speed_quantiles()
    breakpoints = [
        (0.0, 1.00),
        (quantiles["p25"], 1.00),
        (quantiles["p50"], 0.75),
        (quantiles["p75"], 0.40),
        (quantiles["p90"], 0.18),
        (quantiles["max"], 0.05),
    ]
    score = clamp(piecewise_linear(speed, breakpoints))
    return round(score, 4), speed


def maintenance_score(payload: ScoreEstimateRequest) -> float:
    return round(clamp(payload.maintenance_gap_days / 180), 4)


def maintenance_multiplier(payload: ScoreEstimateRequest) -> float:
    return round(0.9 + 0.2 * maintenance_score(payload), 4)


def behavior_score(payload: ScoreEstimateRequest) -> float:
    low_speed = normalize_hours(payload.low_speed_hours, 96)
    anchor = normalize_hours(payload.anchor_hours, 120)
    dwell = normalize_hours(payload.dwell_hours, 72)
    port_proximity = normalize_hours(payload.port_proximity_hours, 72)
    port_visits = clamp(payload.port_visits / 12)
    port_exposure = max(port_proximity, port_visits * 0.6)
    return round(low_speed * 0.35 + anchor * 0.30 + dwell * 0.20 + port_exposure * 0.15, 4)


def stay_probability_score(payload: ScoreEstimateRequest) -> float:
    low_speed = normalize_hours(payload.low_speed_hours, 96)
    stationary = normalize_hours(payload.anchor_hours + payload.dwell_hours, 144)
    return round(low_speed * 0.55 + stationary * 0.45, 4)


def port_anchorage_score(payload: ScoreEstimateRequest) -> float:
    port_proximity = normalize_hours(payload.port_proximity_hours, 96)
    anchorage = normalize_hours(payload.anchor_hours, 120)
    anchorage_index = payload.anchorage_exposure_index or 0.0
    return round(clamp(port_proximity * 0.45 + anchorage * 0.25 + anchorage_index * 0.30), 4)


def persistent_exposure_score(payload: ScoreEstimateRequest) -> float:
    low_speed = normalize_hours(payload.low_speed_hours, 120)
    stationary = normalize_hours(payload.anchor_hours + payload.dwell_hours, 168)
    port_proximity = normalize_hours(payload.port_proximity_hours, 120)
    return round(clamp(low_speed * 0.45 + stationary * 0.35 + port_proximity * 0.20), 4)


def environment_components(payload: ScoreEstimateRequest) -> dict[str, float | None]:
    temperature = sst_suitability(payload.mean_sst)
    salinity = salinity_suitability(payload.mean_salinity)
    physiology = round(clamp(temperature * 0.65 + salinity * 0.35), 4)
    productivity = productivity_pressure(payload.mean_chlorophyll_a)
    hydrodynamic, speed = hydrodynamic_attachment_score(payload.mean_current_u, payload.mean_current_v)
    environment = round(
        clamp(temperature * 0.40 + salinity * 0.20 + productivity * 0.25 + hydrodynamic * 0.15),
        4,
    )
    multiplier = round(0.85 + 0.30 * environment, 4)
    return {
        "temperature": temperature,
        "salinity": salinity,
        "physiology": physiology,
        "productivity": productivity,
        "hydrodynamic": hydrodynamic,
        "current_speed": speed,
        "environment": environment,
        "multiplier": multiplier,
    }


def compute_fpi(payload: ScoreEstimateRequest) -> tuple[float, ComponentScores]:
    behavior = behavior_score(payload)
    stay_probability = stay_probability_score(payload)
    port_anchorage = port_anchorage_score(payload)
    environment = environment_components(payload)
    maintenance = maintenance_score(payload)
    maintenance_adj = maintenance_multiplier(payload)
    persistent_exposure = persistent_exposure_score(payload)
    carbon_penalty = round(1.0 + 0.18 * maintenance + 0.12 * persistent_exposure, 4)
    fpi = round(clamp(behavior * environment["multiplier"] * maintenance_adj), 4)
    return fpi, ComponentScores(
        behavior_score=behavior,
        stay_probability_score=stay_probability,
        port_anchorage_score=port_anchorage,
        temperature_score=environment["temperature"],  # type: ignore[arg-type]
        salinity_score=environment["salinity"],  # type: ignore[arg-type]
        physiology_score=environment["physiology"],  # type: ignore[arg-type]
        productivity_score=environment["productivity"],  # type: ignore[arg-type]
        hydrodynamic_score=environment["hydrodynamic"],  # type: ignore[arg-type]
        current_speed=environment["current_speed"],  # type: ignore[arg-type]
        environment_score=environment["environment"],  # type: ignore[arg-type]
        environment_multiplier=environment["multiplier"],  # type: ignore[arg-type]
        maintenance_score=maintenance,
        maintenance_multiplier=maintenance_adj,
        persistent_exposure_score=persistent_exposure,
        carbon_penalty_multiplier=carbon_penalty,
    )


def compute_ecp(payload: ScoreEstimateRequest, fpi: float, components: ComponentScores) -> float:
    return round(clamp(fpi * components.carbon_penalty_multiplier, 0.0, 1.5), 4)


def compute_rri(payload: ScoreEstimateRequest, components: ComponentScores) -> float:
    traffic = payload.traffic_density_index or 0.0
    rri = (
        components.environment_score * 0.4
        + traffic * 0.25
        + components.stay_probability_score * 0.2
        + components.port_anchorage_score * 0.15
    )
    return round(clamp(rri), 4)


def recommend_action(fpi: float, ecp: float) -> str:
    thresholds = recommendation_thresholds()
    if fpi >= thresholds["fpi_prioritize"] or ecp >= thresholds["ecp_prioritize"]:
        return "Prioritize cleaning assessment"
    if fpi >= thresholds["fpi_monitor"] or ecp >= thresholds["ecp_monitor"]:
        return "Monitor exposure trend"
    return "Low immediate concern"


def estimate_scores(payload: ScoreEstimateRequest) -> ScoreEstimateResponse:
    fpi, components = compute_fpi(payload)
    ecp = compute_ecp(payload, fpi, components)
    rri = compute_rri(payload, components)
    return ScoreEstimateResponse(
        vessel_id=payload.vessel_id,
        fpi_score=fpi,
        ecp_score=ecp,
        rri_score=rri,
        recommendation=recommend_action(fpi, ecp),
        components=components,
    )
