from pydantic import BaseModel, Field


class ScoreEstimateRequest(BaseModel):
    vessel_id: str = Field(..., description="Vessel identifier, typically MMSI or IMO.")
    dwell_hours: float = Field(0, ge=0, description="Moored or berthed exposure hours.")
    anchor_hours: float = Field(0, ge=0, description="Anchorage exposure hours.")
    low_speed_hours: float = Field(0, ge=0, description="Low-speed sailing exposure hours.")
    port_proximity_hours: float = Field(
        0, ge=0, description="Exposure hours spent near port or port-service waters."
    )
    port_visits: int = Field(0, ge=0, description="Port or anchorage visit count.")
    maintenance_gap_days: float = Field(
        0, ge=0, description="Estimated days since last hull cleaning or maintenance."
    )
    mean_sst: float | None = Field(
        default=None, description="Mean sea surface temperature during exposure window."
    )
    mean_salinity: float | None = Field(
        default=None, description="Mean sea surface salinity during exposure window."
    )
    mean_chlorophyll_a: float | None = Field(
        default=None, description="Mean chlorophyll-a during exposure window."
    )
    mean_current_u: float | None = Field(
        default=None, description="Mean eastward current component during exposure window."
    )
    mean_current_v: float | None = Field(
        default=None, description="Mean northward current component during exposure window."
    )
    traffic_density_index: float | None = Field(
        default=None, ge=0, le=1, description="Normalized traffic density index."
    )
    anchorage_exposure_index: float | None = Field(
        default=None, ge=0, le=1, description="Normalized anchorage exposure index."
    )


class ComponentScores(BaseModel):
    behavior_score: float
    stay_probability_score: float
    port_anchorage_score: float
    temperature_score: float
    salinity_score: float
    physiology_score: float
    productivity_score: float
    hydrodynamic_score: float
    current_speed: float | None
    environment_score: float
    environment_multiplier: float
    maintenance_score: float
    maintenance_multiplier: float
    persistent_exposure_score: float
    carbon_penalty_multiplier: float


class ScoreEstimateResponse(BaseModel):
    vessel_id: str
    fpi_score: float
    ecp_score: float
    rri_score: float
    recommendation: str
    components: ComponentScores
