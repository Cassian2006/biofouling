from backend.schemas.scoring import ComponentScores, ScoreEstimateRequest, ScoreEstimateResponse


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def normalize_hours(hours: float, full_scale: float) -> float:
    return clamp(hours / full_scale)


def behavior_score(payload: ScoreEstimateRequest) -> float:
    dwell = normalize_hours(payload.dwell_hours, 72)
    anchor = normalize_hours(payload.anchor_hours, 120)
    low_speed = normalize_hours(payload.low_speed_hours, 96)
    port_visits = clamp(payload.port_visits / 12)
    return round(dwell * 0.35 + anchor * 0.30 + low_speed * 0.20 + port_visits * 0.15, 4)


def environment_score(payload: ScoreEstimateRequest) -> float:
    sst = 0.0 if payload.mean_sst is None else clamp((payload.mean_sst - 24) / 8)
    chlorophyll = (
        0.0 if payload.mean_chlorophyll_a is None else clamp(payload.mean_chlorophyll_a / 1.5)
    )
    return round(sst * 0.55 + chlorophyll * 0.45, 4)


def maintenance_score(payload: ScoreEstimateRequest) -> float:
    return round(clamp(payload.maintenance_gap_days / 180), 4)


def compute_fpi(payload: ScoreEstimateRequest) -> tuple[float, ComponentScores]:
    behavior = behavior_score(payload)
    environment = environment_score(payload)
    maintenance = maintenance_score(payload)
    fpi = round(behavior * 0.5 + environment * 0.3 + maintenance * 0.2, 4)
    return fpi, ComponentScores(
        behavior_score=behavior,
        environment_score=environment,
        maintenance_score=maintenance,
    )


def compute_ecp(payload: ScoreEstimateRequest, fpi: float) -> float:
    warm_multiplier = 1.0
    if payload.mean_sst is not None and payload.mean_sst >= 28:
        warm_multiplier += 0.15
    if payload.mean_chlorophyll_a is not None and payload.mean_chlorophyll_a >= 0.5:
        warm_multiplier += 0.10
    if payload.low_speed_hours >= 48:
        warm_multiplier += 0.05
    return round(clamp(fpi * warm_multiplier, 0.0, 1.5), 4)


def compute_rri(payload: ScoreEstimateRequest, components: ComponentScores) -> float:
    traffic = payload.traffic_density_index or 0.0
    anchorage = payload.anchorage_exposure_index or 0.0
    rri = (
        components.environment_score * 0.4
        + traffic * 0.25
        + anchorage * 0.2
        + components.behavior_score * 0.15
    )
    return round(clamp(rri), 4)


def recommend_action(fpi: float, ecp: float) -> str:
    if fpi >= 0.7 or ecp >= 0.85:
        return "Prioritize cleaning assessment"
    if fpi >= 0.4 or ecp >= 0.55:
        return "Monitor exposure trend"
    return "Low immediate concern"


def estimate_scores(payload: ScoreEstimateRequest) -> ScoreEstimateResponse:
    fpi, components = compute_fpi(payload)
    ecp = compute_ecp(payload, fpi)
    rri = compute_rri(payload, components)
    return ScoreEstimateResponse(
        vessel_id=payload.vessel_id,
        fpi_score=fpi,
        ecp_score=ecp,
        rri_score=rri,
        recommendation=recommend_action(fpi, ecp),
        components=components,
    )

