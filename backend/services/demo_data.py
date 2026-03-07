from functools import lru_cache
from pathlib import Path

import pandas as pd

from backend.schemas.demo import (
    DemoSummaryResponse,
    RegionalStatsResponse,
    ReportPreviewResponse,
    RiskCellRecord,
    TopCellSummary,
    TopVesselSummary,
    VesselDetailResponse,
    VesselRecord,
    VesselTrendPoint,
    VesselTrendResponse,
    VesselTrackPoint,
    VesselTrackResponse,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MAPS_DIR = PROJECT_ROOT / "outputs" / "maps"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"


def _latest_file(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No files found for pattern '{pattern}' in {directory}")
    return matches[-1]


def _load_csv(path: Path) -> pd.DataFrame:
    dataframe = pd.read_csv(path)
    dataframe.columns = [column.strip().lower() for column in dataframe.columns]
    return dataframe


def _load_ais_csv(path: Path) -> pd.DataFrame:
    dataframe = _load_csv(path)
    dataframe["mmsi"] = dataframe["mmsi"].astype(str)
    dataframe["timestamp"] = pd.to_datetime(dataframe["timestamp"], utc=True)
    if "is_low_speed" in dataframe.columns:
        dataframe["is_low_speed"] = dataframe["is_low_speed"].fillna(False).astype(bool)
    return dataframe


def _maybe_round(value: object, digits: int = 3) -> float | None:
    if pd.isna(value):
        return None
    return round(float(value), digits)


def _window_label_from_features(path: Path) -> str:
    stem = path.stem.replace("vessel_features_", "")
    if "_" not in stem:
        return stem
    parts = stem.split("_")
    if len(parts) < 2:
        return stem
    return f"{parts[0]} to {parts[1]}"


def _serialize_vessels(features: pd.DataFrame) -> list[VesselRecord]:
    ordered = features.sort_values(["fpi_proxy", "ping_count"], ascending=[False, False]).copy()
    vessels: list[VesselRecord] = []
    for rank, row in enumerate(ordered.itertuples(index=False), start=1):
        vessels.append(
            VesselRecord(
                rank=rank,
                mmsi=str(row.mmsi),
                ping_count=int(row.ping_count),
                track_start=str(row.track_start),
                track_end=str(row.track_end),
                mean_latitude=_maybe_round(row.mean_latitude, 4),
                mean_longitude=_maybe_round(row.mean_longitude, 4),
                low_speed_ratio=_maybe_round(row.low_speed_ratio),
                mean_sst=_maybe_round(row.mean_sst),
                mean_chlorophyll_a=_maybe_round(row.mean_chlorophyll_a),
                track_duration_hours=_maybe_round(row.track_duration_hours, 2),
                fpi_proxy=_maybe_round(row.fpi_proxy),
                ecp_proxy=_maybe_round(row.ecp_proxy),
                recommendation=str(row.recommendation),
            )
        )
    return vessels


def _serialize_risk_cells(risk: pd.DataFrame) -> list[RiskCellRecord]:
    ordered = risk.sort_values(["rri_score", "traffic_points"], ascending=[False, False]).copy()
    cells: list[RiskCellRecord] = []
    for rank, row in enumerate(ordered.itertuples(index=False), start=1):
        cells.append(
            RiskCellRecord(
                rank=rank,
                grid_lat=_maybe_round(row.grid_lat, 4),
                grid_lon=_maybe_round(row.grid_lon, 4),
                traffic_points=int(row.traffic_points),
                vessel_count=int(row.vessel_count),
                low_speed_ratio=_maybe_round(row.low_speed_ratio),
                mean_sst=_maybe_round(row.mean_sst),
                mean_chlorophyll_a=_maybe_round(row.mean_chlorophyll_a),
                traffic_score=_maybe_round(row.traffic_score),
                low_speed_score=_maybe_round(row.low_speed_score),
                environment_score=_maybe_round(row.environment_score),
                rri_score=_maybe_round(row.rri_score),
                risk_level=str(row.risk_level),
            )
        )
    return cells


def _recommendation_counts(vessels: list[VesselRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for vessel in vessels:
        counts[vessel.recommendation] = counts.get(vessel.recommendation, 0) + 1
    return counts


def _extract_vessel_report_section(report_text: str, mmsi: str) -> list[str]:
    target_header = f"### MMSI {mmsi}"
    lines = report_text.splitlines()
    collected: list[str] = []
    capture = False
    for line in lines:
        if line.startswith("### MMSI "):
            if capture:
                break
            capture = line.strip() == target_header
            continue
        if capture and line.strip():
            collected.append(line.strip())
    return collected


def _build_fallback_report_lines(vessel: VesselRecord) -> list[str]:
    return [
        f"Track window: {vessel.track_start} -> {vessel.track_end}",
        f"Ping count: {vessel.ping_count}",
        f"Low-speed ratio: {vessel.low_speed_ratio}",
        f"FPI proxy: {vessel.fpi_proxy}",
        f"ECP proxy: {vessel.ecp_proxy}",
        f"Recommendation: {vessel.recommendation}",
    ]


def _downsample_track(track: pd.DataFrame, max_points: int = 320) -> pd.DataFrame:
    if len(track) <= max_points:
        return track
    indices = sorted(
        {
            round(index * (len(track) - 1) / (max_points - 1))
            for index in range(max_points)
        }
    )
    return track.iloc[indices].copy()


@lru_cache(maxsize=1)
def load_demo_payload() -> dict[str, object]:
    features_path = _latest_file(PROCESSED_DIR, "vessel_features_*.csv")
    risk_path = _latest_file(MAPS_DIR, "regional_risk_*.csv")
    report_path = _latest_file(REPORTS_DIR, "voyage_report_*.md")
    ais_path = _latest_file(PROCESSED_DIR, "ais_*_cleaned.csv")

    features = _load_csv(features_path)
    risk = _load_csv(risk_path)
    ais = _load_ais_csv(ais_path)
    vessels = _serialize_vessels(features)
    risk_cells = _serialize_risk_cells(risk)
    window_label = _window_label_from_features(features_path)
    recommendation_counts = _recommendation_counts(vessels)
    report_text = report_path.read_text(encoding="utf-8")

    payload = {
        "window_label": window_label,
        "vessels": vessels,
        "risk_cells": risk_cells,
        "report_text": report_text,
        "ais": ais,
        "summary": DemoSummaryResponse(
            window_label=window_label,
            vessels_summarized=len(vessels),
            grid_cells=len(risk_cells),
            high_risk_cells=sum(1 for cell in risk_cells if cell.risk_level == "high"),
            medium_risk_cells=sum(1 for cell in risk_cells if cell.risk_level == "medium"),
            recommendation_counts=recommendation_counts,
            top_vessel=TopVesselSummary(
                mmsi=vessels[0].mmsi,
                fpi_proxy=vessels[0].fpi_proxy,
                ecp_proxy=vessels[0].ecp_proxy,
                recommendation=vessels[0].recommendation,
            ),
            top_cell=TopCellSummary(
                grid_lat=risk_cells[0].grid_lat,
                grid_lon=risk_cells[0].grid_lon,
                rri_score=risk_cells[0].rri_score,
                risk_level=risk_cells[0].risk_level,
            ),
            top_vessels=vessels[:6],
            top_cells=risk_cells[:6],
        ),
    }
    return payload


def _find_vessel(mmsi: str) -> VesselRecord:
    for vessel in get_demo_vessels():
        if vessel.mmsi == mmsi:
            return vessel
    raise LookupError(f"Vessel {mmsi} not found")


def get_demo_summary() -> DemoSummaryResponse:
    return load_demo_payload()["summary"]  # type: ignore[return-value]


def get_demo_vessels() -> list[VesselRecord]:
    return load_demo_payload()["vessels"]  # type: ignore[return-value]


def get_demo_risk_cells() -> list[RiskCellRecord]:
    return load_demo_payload()["risk_cells"]  # type: ignore[return-value]


def get_vessel_detail(mmsi: str) -> VesselDetailResponse:
    vessels = get_demo_vessels()
    vessel = _find_vessel(mmsi)
    peer_vessels = [item for item in vessels if item.mmsi != mmsi][:8]
    return VesselDetailResponse(
        window_label=load_demo_payload()["window_label"],  # type: ignore[arg-type]
        vessel=vessel,
        cohort_size=len(vessels),
        rank_fraction=f"{vessel.rank} / {len(vessels)}",
        peer_vessels=peer_vessels,
    )


def get_vessel_track(mmsi: str) -> VesselTrackResponse:
    _find_vessel(mmsi)
    ais = load_demo_payload()["ais"]  # type: ignore[assignment]
    vessel_track = ais.loc[ais["mmsi"] == mmsi].sort_values("timestamp").copy()
    if vessel_track.empty:
        raise LookupError(f"Track for vessel {mmsi} not found")

    sampled = _downsample_track(vessel_track)
    points = [
        VesselTrackPoint(
            timestamp=row.timestamp.isoformat(),
            latitude=round(float(row.latitude), 6),
            longitude=round(float(row.longitude), 6),
            sog=_maybe_round(row.sog, 2),
            is_low_speed=bool(row.is_low_speed),
        )
        for row in sampled.itertuples(index=False)
    ]
    return VesselTrackResponse(
        window_label=load_demo_payload()["window_label"],  # type: ignore[arg-type]
        mmsi=mmsi,
        point_count=int(len(vessel_track)),
        rendered_point_count=int(len(points)),
        low_speed_point_count=int(vessel_track["is_low_speed"].sum()),
        track_start=vessel_track["timestamp"].min().isoformat(),
        track_end=vessel_track["timestamp"].max().isoformat(),
        min_latitude=round(float(vessel_track["latitude"].min()), 6),
        max_latitude=round(float(vessel_track["latitude"].max()), 6),
        min_longitude=round(float(vessel_track["longitude"].min()), 6),
        max_longitude=round(float(vessel_track["longitude"].max()), 6),
        points=points,
    )


def get_vessel_trend(mmsi: str, interval_hours: int = 6) -> VesselTrendResponse:
    _find_vessel(mmsi)
    ais = load_demo_payload()["ais"]  # type: ignore[assignment]
    vessel_track = ais.loc[ais["mmsi"] == mmsi].sort_values("timestamp").copy()
    if vessel_track.empty:
        raise LookupError(f"Trend for vessel {mmsi} not found")

    vessel_track["window_start"] = vessel_track["timestamp"].dt.floor(f"{interval_hours}h")
    grouped = (
        vessel_track.groupby("window_start", dropna=False)
        .agg(
            point_count=("timestamp", "size"),
            mean_sog=("sog", "mean"),
            low_speed_ratio=("is_low_speed", "mean"),
        )
        .reset_index()
        .sort_values("window_start")
    )

    windows = [
        VesselTrendPoint(
            window_start=row.window_start.isoformat(),
            point_count=int(row.point_count),
            mean_sog=_maybe_round(row.mean_sog, 3),
            low_speed_ratio=_maybe_round(row.low_speed_ratio, 3),
        )
        for row in grouped.itertuples(index=False)
    ]

    max_mean_sog = grouped["mean_sog"].max()
    max_low_speed_ratio = grouped["low_speed_ratio"].max()
    return VesselTrendResponse(
        window_label=load_demo_payload()["window_label"],  # type: ignore[arg-type]
        mmsi=mmsi,
        interval_hours=interval_hours,
        windows=windows,
        max_point_count=int(grouped["point_count"].max()),
        max_mean_sog=_maybe_round(max_mean_sog, 3),
        max_low_speed_ratio=_maybe_round(max_low_speed_ratio, 3),
    )


def get_regional_stats() -> RegionalStatsResponse:
    risk_cells = get_demo_risk_cells()
    total_cells = len(risk_cells)
    risk_level_counts = {
        "high": sum(1 for cell in risk_cells if cell.risk_level == "high"),
        "medium": sum(1 for cell in risk_cells if cell.risk_level == "medium"),
        "low": sum(1 for cell in risk_cells if cell.risk_level == "low"),
    }

    def average(attr: str) -> float | None:
        values = [getattr(cell, attr) for cell in risk_cells if getattr(cell, attr) is not None]
        if not values:
            return None
        return round(sum(values) / len(values), 3)

    return RegionalStatsResponse(
        window_label=load_demo_payload()["window_label"],  # type: ignore[arg-type]
        total_cells=total_cells,
        risk_level_counts=risk_level_counts,
        average_rri=average("rri_score"),
        average_traffic_score=average("traffic_score"),
        average_low_speed_score=average("low_speed_score"),
        average_environment_score=average("environment_score"),
        top_cell=risk_cells[0],
        top_cells=risk_cells[:10],
    )


def get_vessel_report_preview(mmsi: str) -> ReportPreviewResponse:
    vessel = _find_vessel(mmsi)
    report_text = load_demo_payload()["report_text"]  # type: ignore[assignment]
    lines = _extract_vessel_report_section(report_text, mmsi)
    if not lines:
        lines = _build_fallback_report_lines(vessel)
    markdown = "\n".join(lines)
    return ReportPreviewResponse(
        window_label=load_demo_payload()["window_label"],  # type: ignore[arg-type]
        scope="vessel",
        title=f"MMSI {mmsi} report preview",
        markdown=markdown,
        lines=lines,
    )


def get_overview_report_preview() -> ReportPreviewResponse:
    report_text = load_demo_payload()["report_text"]  # type: ignore[assignment]
    lines: list[str] = []
    for line in report_text.splitlines():
        if line.startswith("## Vessel Summaries"):
            break
        if line.strip():
            lines.append(line.strip())
    return ReportPreviewResponse(
        window_label=load_demo_payload()["window_label"],  # type: ignore[arg-type]
        scope="overview",
        title="Voyage report overview",
        markdown="\n".join(lines),
        lines=lines,
    )
