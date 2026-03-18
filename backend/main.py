import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.schemas.demo import (
    DemoSummaryResponse,
    RegionalStatsResponse,
    ReportPreviewResponse,
    RiskCellRecord,
    ScienceMaterialsResponse,
    VesselAnomalyDetailResponse,
    VesselAnomalyResponse,
    VesselDetailResponse,
    VesselForecastResponse,
    VesselRecord,
    VesselTrendResponse,
    VesselTrackResponse,
)
from backend.schemas.report import HealthResponse
from backend.schemas.scoring import ScoreEstimateRequest, ScoreEstimateResponse
from backend.services.demo_data import (
    get_demo_risk_cells,
    get_demo_summary,
    get_demo_vessels,
    get_overview_report_preview,
    get_regional_stats,
    get_vessel_detail,
    get_vessel_report_preview,
    get_vessel_trend,
    get_vessel_track,
)
from backend.services.anomaly_data import get_demo_anomaly_summary, get_vessel_anomaly_detail
from backend.services.forecast_data import get_vessel_forecast
from backend.services.science_materials import get_science_materials
from backend.services.scoring import estimate_scores

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIST_DIR = PROJECT_ROOT / "frontend" / "dist"
FRONTEND_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"
FRONTEND_DEMO_DIR = FRONTEND_DIST_DIR / "demo"


app = FastAPI(
    title="Biofouling Decision Platform",
    version="0.1.0",
    description="Backend service for AIS and marine-environment biofouling analysis.",
)


def _allowed_origins() -> list[str]:
    origins = {
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    }
    extra_origins = os.getenv("FRONTEND_ORIGIN", "")
    for origin in extra_origins.split(","):
        normalized = origin.strip()
        if normalized:
            origins.add(normalized)
    return sorted(origins)


app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["system"], response_model=None)
def root():
    index_file = FRONTEND_DIST_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Biofouling platform backend is initialized."}


@app.get("/health", tags=["system"], response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version="0.1.0")


@app.post("/scoring/estimate", tags=["scoring"], response_model=ScoreEstimateResponse)
def scoring_estimate(payload: ScoreEstimateRequest) -> ScoreEstimateResponse:
    return estimate_scores(payload)


@app.get("/api/demo/summary", tags=["demo"], response_model=DemoSummaryResponse)
def demo_summary() -> DemoSummaryResponse:
    return get_demo_summary()


@app.get("/api/demo/vessels", tags=["demo"], response_model=list[VesselRecord])
def demo_vessels() -> list[VesselRecord]:
    return get_demo_vessels()


@app.get("/api/demo/risk-cells", tags=["demo"], response_model=list[RiskCellRecord])
def demo_risk_cells() -> list[RiskCellRecord]:
    return get_demo_risk_cells()


@app.get("/api/demo/vessels/{mmsi}", tags=["demo"], response_model=VesselDetailResponse)
def demo_vessel_detail(mmsi: str) -> VesselDetailResponse:
    try:
        return get_vessel_detail(mmsi)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/api/demo/vessels/{mmsi}/track", tags=["demo"], response_model=VesselTrackResponse)
def demo_vessel_track(mmsi: str) -> VesselTrackResponse:
    try:
        return get_vessel_track(mmsi)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/api/demo/vessels/{mmsi}/trend", tags=["demo"], response_model=VesselTrendResponse)
def demo_vessel_trend(mmsi: str) -> VesselTrendResponse:
    try:
        return get_vessel_trend(mmsi)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/api/demo/vessels/{mmsi}/forecast", tags=["demo"], response_model=VesselForecastResponse)
def demo_vessel_forecast(mmsi: str) -> VesselForecastResponse:
    try:
        return get_vessel_forecast(mmsi)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (FileNotFoundError, RuntimeError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/api/demo/anomalies", tags=["demo"], response_model=VesselAnomalyResponse)
def demo_anomalies() -> VesselAnomalyResponse:
    try:
        return get_demo_anomaly_summary()
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/api/demo/vessels/{mmsi}/anomaly", tags=["demo"], response_model=VesselAnomalyDetailResponse)
def demo_vessel_anomaly(mmsi: str) -> VesselAnomalyDetailResponse:
    try:
        return get_vessel_anomaly_detail(mmsi)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/api/demo/regional-stats", tags=["demo"], response_model=RegionalStatsResponse)
def demo_regional_stats() -> RegionalStatsResponse:
    return get_regional_stats()


@app.get("/api/demo/reports/overview", tags=["demo"], response_model=ReportPreviewResponse)
def demo_report_overview() -> ReportPreviewResponse:
    return get_overview_report_preview()


@app.get("/api/demo/reports/vessels/{mmsi}", tags=["demo"], response_model=ReportPreviewResponse)
def demo_vessel_report_preview(mmsi: str) -> ReportPreviewResponse:
    try:
        return get_vessel_report_preview(mmsi)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/api/demo/science/materials", tags=["demo"], response_model=ScienceMaterialsResponse)
def demo_science_materials() -> ScienceMaterialsResponse:
    return get_science_materials()


if FRONTEND_ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_ASSETS_DIR)), name="frontend-assets")

if FRONTEND_DEMO_DIR.exists():
    app.mount("/demo", StaticFiles(directory=str(FRONTEND_DEMO_DIR)), name="frontend-demo")


@app.get("/{full_path:path}", include_in_schema=False, response_model=None)
def frontend_routes(full_path: str):
    index_file = FRONTEND_DIST_DIR / "index.html"
    blocked_prefixes = ("api", "docs", "redoc", "openapi.json", "health", "scoring")
    if full_path == "" or full_path.startswith(blocked_prefixes):
        raise HTTPException(status_code=404, detail=f"Route '{full_path}' not found")
    if not index_file.exists():
        raise HTTPException(status_code=404, detail=f"Route '{full_path}' not found")
    return FileResponse(index_file)
