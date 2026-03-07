from pydantic import BaseModel, Field


class ScoreEstimateRequest(BaseModel):
    vessel_id: str = Field(..., description="Vessel identifier, typically MMSI or IMO.")
    dwell_hours: float = Field(0, ge=0, description="Moored or berthed exposure hours.")
    anchor_hours: float = Field(0, ge=0, description="Anchorage exposure hours.")
    low_speed_hours: float = Field(0, ge=0, description="Low-speed sailing exposure hours.")
    port_visits: int = Field(0, ge=0, description="Port or anchorage visit count.")
    maintenance_gap_days: float = Field(
        0, ge=0, description="Estimated days since last hull cleaning or maintenance."
    )
    mean_sst: float | None = Field(
        default=None, description="Mean sea surface temperature during exposure window."
    )
    mean_chlorophyll_a: float | None = Field(
        default=None, description="Mean chlorophyll-a during exposure window."
    )
    traffic_density_index: float | None = Field(
        default=None, ge=0, le=1, description="Normalized traffic density index."
    )
    anchorage_exposure_index: float | None = Field(
        default=None, ge=0, le=1, description="Normalized anchorage exposure index."
    )


class ComponentScores(BaseModel):
    behavior_score: float
    environment_score: float
    maintenance_score: float


class ScoreEstimateResponse(BaseModel):
    vessel_id: str
    fpi_score: float
    ecp_score: float
    rri_score: float
    recommendation: str
    components: ComponentScores

