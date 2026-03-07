from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str


class VoyageReportRequest(BaseModel):
    vessel_id: str
    start_time: str
    end_time: str


class VoyageReportSummary(BaseModel):
    vessel_id: str
    fpi_score: float
    ecp_score: float
    recommendation: str

