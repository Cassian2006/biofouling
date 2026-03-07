from pydantic import BaseModel


class VesselRecord(BaseModel):
    rank: int
    mmsi: str
    ping_count: int
    track_start: str
    track_end: str
    mean_latitude: float | None
    mean_longitude: float | None
    low_speed_ratio: float | None
    mean_sst: float | None
    mean_chlorophyll_a: float | None
    mean_salinity: float | None
    mean_current_u: float | None
    mean_current_v: float | None
    track_duration_hours: float | None
    fpi_proxy: float | None
    ecp_proxy: float | None
    recommendation: str


class VesselStaticProfile(BaseModel):
    mmsi: str
    first_seen: str | None
    last_seen: str | None
    vessel_name: str | None
    imo: str | None
    ship_type: str | None
    flag: str | None
    build_year: int | None
    length_m: float | None
    beam_m: float | None
    design_draught_m: float | None
    observed_draught_m: float | None
    max_observed_draught_m: float | None
    dwt: float | None
    grt: float | None
    teu: float | None
    dominant_destination: str | None
    dominant_nav_status: str | None
    profile_source: str
    static_source: str | None


class ValidationSummary(BaseModel):
    mmsi: str
    event_count: int
    source_count: int
    sources: list[str]
    latest_event_type: str | None
    latest_event_start: str | None
    latest_port_name: str | None
    notes_count: int


class ReferenceSiteRecord(BaseModel):
    site_id: str
    name: str
    site_type: str
    zone: str
    latitude: float
    longitude: float
    description: str | None


class RiskCellRecord(BaseModel):
    rank: int
    grid_lat: float | None
    grid_lon: float | None
    traffic_points: int
    vessel_count: int
    low_speed_ratio: float | None
    mean_sst: float | None
    mean_chlorophyll_a: float | None
    traffic_score: float | None
    low_speed_score: float | None
    environment_score: float | None
    rri_score: float | None
    risk_level: str
    nearest_reference_name: str | None
    nearest_reference_type: str | None
    nearest_reference_zone: str | None
    nearest_reference_distance_km: float | None


class TopVesselSummary(BaseModel):
    mmsi: str
    fpi_proxy: float | None
    ecp_proxy: float | None
    recommendation: str


class TopCellSummary(BaseModel):
    grid_lat: float | None
    grid_lon: float | None
    rri_score: float | None
    risk_level: str


class DemoSummaryResponse(BaseModel):
    window_label: str
    vessels_summarized: int
    grid_cells: int
    high_risk_cells: int
    medium_risk_cells: int
    recommendation_counts: dict[str, int]
    top_vessel: TopVesselSummary
    top_cell: TopCellSummary
    top_vessels: list[VesselRecord]
    top_cells: list[RiskCellRecord]


class VesselDetailResponse(BaseModel):
    window_label: str
    vessel: VesselRecord
    cohort_size: int
    rank_fraction: str
    peer_vessels: list[VesselRecord]
    static_profile: VesselStaticProfile | None
    validation_summary: ValidationSummary
    nearest_reference: ReferenceSiteRecord | None
    nearest_reference_distance_km: float | None


class VesselTrackPoint(BaseModel):
    timestamp: str
    latitude: float
    longitude: float
    sog: float | None
    is_low_speed: bool


class VesselTrackResponse(BaseModel):
    window_label: str
    mmsi: str
    point_count: int
    rendered_point_count: int
    low_speed_point_count: int
    track_start: str
    track_end: str
    min_latitude: float
    max_latitude: float
    min_longitude: float
    max_longitude: float
    points: list[VesselTrackPoint]


class VesselTrendPoint(BaseModel):
    window_start: str
    point_count: int
    mean_sog: float | None
    low_speed_ratio: float | None


class VesselTrendResponse(BaseModel):
    window_label: str
    mmsi: str
    interval_hours: int
    windows: list[VesselTrendPoint]
    max_point_count: int
    max_mean_sog: float | None
    max_low_speed_ratio: float | None


class ForecastSignal(BaseModel):
    title: str
    value: str
    assessment: str
    detail: str


class ForecastHistoryPoint(BaseModel):
    window_start: str
    fpi_proxy: float


class VesselForecastResponse(BaseModel):
    available: bool
    unavailable_reason: str | None = None
    window_label: str
    mmsi: str
    history_start: str | None
    history_end: str | None
    forecast_window_start: str | None
    forecast_window_end: str | None
    predicted_fpi: float | None
    predicted_risk_label: str | None
    raw_predicted_risk_label: str | None
    low_threshold: float | None
    high_threshold: float | None
    validation_rmse: float | None
    validation_r2: float | None
    raw_accuracy: float | None
    calibrated_accuracy: float | None
    confidence_band_low: float | None
    confidence_band_high: float | None
    confidence_level: str | None
    model_name: str | None
    history_windows: int | None
    window_hours: int | None
    signals: list[ForecastSignal]
    history_points: list[ForecastHistoryPoint]


class VesselAnomalyRecord(BaseModel):
    rank: int
    mmsi: str
    anomaly_score: float
    anomaly_level: str
    explanations: list[str]


class VesselAnomalyResponse(BaseModel):
    window_label: str
    vessel_count: int
    anomaly_level_counts: dict[str, int]
    top_anomalies: list[VesselAnomalyRecord]


class VesselAnomalyDetailResponse(BaseModel):
    window_label: str
    mmsi: str
    anomaly_score: float
    anomaly_level: str
    percentile_rank: float
    explanations: list[str]
    peer_anomalies: list[VesselAnomalyRecord]


class RegionalStatsResponse(BaseModel):
    window_label: str
    total_cells: int
    risk_level_counts: dict[str, int]
    average_rri: float | None
    average_traffic_score: float | None
    average_low_speed_score: float | None
    average_environment_score: float | None
    top_cell: RiskCellRecord
    top_cells: list[RiskCellRecord]
    reference_sites: list[ReferenceSiteRecord]


class ReportPreviewResponse(BaseModel):
    window_label: str
    scope: str
    title: str
    markdown: str
    lines: list[str]
