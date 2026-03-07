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
    track_duration_hours: float | None
    fpi_proxy: float | None
    ecp_proxy: float | None
    recommendation: str


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


class ReportPreviewResponse(BaseModel):
    window_label: str
    scope: str
    title: str
    markdown: str
    lines: list[str]
