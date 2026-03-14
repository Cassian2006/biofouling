import json
from functools import lru_cache
from pathlib import Path

import math
import pandas as pd

from backend.schemas.demo import (
    DemoSummaryResponse,
    ReferenceSiteRecord,
    RegionalStatsResponse,
    ReportPreviewResponse,
    RiskCellRecord,
    TopCellSummary,
    TopVesselSummary,
    ValidationSummary,
    VesselDetailResponse,
    VesselRecord,
    VesselStaticProfile,
    VesselTrendPoint,
    VesselTrendResponse,
    VesselTrackPoint,
    VesselTrackResponse,
)
from scripts.build_vessel_catalog import build_ais_derived_catalog, load_static_profiles, merge_static_profiles
from scripts.summarize_validation_events import load_validation_events, summarize_validation_events


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EXTERNAL_DIR = PROJECT_ROOT / "data" / "external"
REFERENCE_DIR = PROJECT_ROOT / "data" / "reference"
MAPS_DIR = PROJECT_ROOT / "outputs" / "maps"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"
COMPETITION_BASELINE_PATH = CONFIG_DIR / "competition_baseline.json"


def _latest_file(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No files found for pattern '{pattern}' in {directory}")
    return matches[-1]


def _load_csv(path: Path) -> pd.DataFrame:
    dataframe = pd.read_csv(path)
    dataframe.columns = [column.strip().lower() for column in dataframe.columns]
    return dataframe


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_ais_csv(path: Path) -> pd.DataFrame:
    dataframe = _load_csv(path)
    dataframe["mmsi"] = dataframe["mmsi"].astype(str)
    dataframe["timestamp"] = pd.to_datetime(dataframe["timestamp"], utc=True)
    if "is_low_speed" in dataframe.columns:
        dataframe["is_low_speed"] = dataframe["is_low_speed"].fillna(False).astype(bool)
    return dataframe


def _optional_latest_file(directory: Path, pattern: str) -> Path | None:
    matches = sorted(directory.glob(pattern))
    if not matches:
        return None
    return matches[-1]


def _load_reference_sites(path: Path | None = None) -> pd.DataFrame:
    path = path or (REFERENCE_DIR / "singapore_reference_sites.csv")
    if not path.exists():
        return pd.DataFrame(
            columns=["site_id", "name", "site_type", "zone", "latitude", "longitude", "description"]
        )
    dataframe = _load_csv(path)
    dataframe["latitude"] = pd.to_numeric(dataframe["latitude"], errors="coerce")
    dataframe["longitude"] = pd.to_numeric(dataframe["longitude"], errors="coerce")
    return dataframe.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)


def _serialize_reference_sites(reference_sites: pd.DataFrame) -> list[ReferenceSiteRecord]:
    records: list[ReferenceSiteRecord] = []
    for row in reference_sites.itertuples(index=False):
        records.append(
            ReferenceSiteRecord(
                site_id=str(row.site_id),
                name=str(row.name),
                site_type=str(row.site_type),
                zone=str(row.zone),
                latitude=round(float(row.latitude), 6),
                longitude=round(float(row.longitude), 6),
                description=str(row.description) if pd.notna(row.description) else None,
            )
        )
    return records


def _distance_km(latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float) -> float:
    radius_km = 6371.0
    lat_a = math.radians(latitude_a)
    lat_b = math.radians(latitude_b)
    delta_lat = math.radians(latitude_b - latitude_a)
    delta_lon = math.radians(longitude_b - longitude_a)

    hav = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(hav), math.sqrt(1 - hav))


def _nearest_reference_from_sites(
    latitude: float,
    longitude: float,
    reference_sites: list[ReferenceSiteRecord],
) -> tuple[ReferenceSiteRecord | None, float | None]:
    if not reference_sites:
        return None, None

    nearest = None
    best_distance = None
    for site in reference_sites:
        distance = _distance_km(latitude, longitude, site.latitude, site.longitude)
        if best_distance is None or distance < best_distance:
            nearest = site
            best_distance = distance

    return nearest, round(best_distance, 2) if best_distance is not None else None


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
                mean_salinity=_maybe_round(getattr(row, "mean_salinity", None)),
                mean_current_u=_maybe_round(getattr(row, "mean_current_u", None)),
                mean_current_v=_maybe_round(getattr(row, "mean_current_v", None)),
                track_duration_hours=_maybe_round(row.track_duration_hours, 2),
                fpi_proxy=_maybe_round(row.fpi_proxy),
                ecp_proxy=_maybe_round(row.ecp_proxy),
                recommendation=str(row.recommendation),
            )
        )
    return vessels


def _serialize_risk_cells(
    risk: pd.DataFrame,
    reference_sites: list[ReferenceSiteRecord],
) -> list[RiskCellRecord]:
    ordered = risk.sort_values(["rri_score", "traffic_points"], ascending=[False, False]).copy()
    cells: list[RiskCellRecord] = []
    for rank, row in enumerate(ordered.itertuples(index=False), start=1):
        nearest_reference, nearest_distance = _nearest_reference_from_sites(
            float(row.grid_lat),
            float(row.grid_lon),
            reference_sites,
        )
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
                nearest_reference_name=nearest_reference.name if nearest_reference else None,
                nearest_reference_type=nearest_reference.site_type if nearest_reference else None,
                nearest_reference_zone=nearest_reference.zone if nearest_reference else None,
                nearest_reference_distance_km=nearest_distance,
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


def _load_vessel_catalog(
    ais: pd.DataFrame,
    catalog_path: Path | None = None,
    static_path: Path | None = None,
) -> pd.DataFrame:
    catalog_path = catalog_path or _optional_latest_file(PROCESSED_DIR, "vessel_catalog*.csv")
    if catalog_path:
        catalog = _load_csv(catalog_path)
        catalog["mmsi"] = catalog["mmsi"].astype(str)
        return catalog

    derived = build_ais_derived_catalog(ais)
    static_path = static_path or _optional_latest_file(EXTERNAL_DIR, "vessel_static*.csv")
    if static_path:
        static_profiles = load_static_profiles(static_path)
        return merge_static_profiles(derived, static_profiles)
    return derived


def _load_validation_summary(
    validation_summary_path: Path | None = None,
    validation_events_path: Path | None = None,
) -> pd.DataFrame:
    validation_summary_path = validation_summary_path or _optional_latest_file(PROCESSED_DIR, "validation_summary*.csv")
    if validation_summary_path:
        summary = _load_csv(validation_summary_path)
        summary["mmsi"] = summary["mmsi"].astype(str)
        return summary

    validation_events_path = validation_events_path or _optional_latest_file(EXTERNAL_DIR, "validation_events*.csv")
    if validation_events_path:
        events = load_validation_events(validation_events_path)
        summary = summarize_validation_events(events)
        summary["mmsi"] = summary["mmsi"].astype(str)
        return summary

    return pd.DataFrame(
        columns=[
            "mmsi",
            "event_count",
            "source_count",
            "sources",
            "latest_event_type",
            "latest_event_start",
            "latest_port_name",
            "notes_count",
        ]
    )


def _find_static_profile(mmsi: str) -> VesselStaticProfile | None:
    catalog = load_demo_payload()["vessel_catalog"]  # type: ignore[assignment]
    row = catalog.loc[catalog["mmsi"] == mmsi]
    if row.empty:
        return None
    record = row.iloc[0]
    build_year = record.get("build_year")
    return VesselStaticProfile(
        mmsi=mmsi,
        first_seen=str(record.get("first_seen")) if pd.notna(record.get("first_seen")) else None,
        last_seen=str(record.get("last_seen")) if pd.notna(record.get("last_seen")) else None,
        vessel_name=str(record.get("vessel_name")) if pd.notna(record.get("vessel_name")) else None,
        imo=str(record.get("imo")) if pd.notna(record.get("imo")) else None,
        ship_type=str(record.get("ship_type")) if pd.notna(record.get("ship_type")) else None,
        flag=str(record.get("flag")) if pd.notna(record.get("flag")) else None,
        build_year=int(build_year) if pd.notna(build_year) else None,
        length_m=_maybe_round(record.get("length_m")),
        beam_m=_maybe_round(record.get("beam_m")),
        design_draught_m=_maybe_round(record.get("design_draught_m")),
        observed_draught_m=_maybe_round(record.get("observed_draught_m")),
        max_observed_draught_m=_maybe_round(record.get("max_observed_draught_m")),
        dwt=_maybe_round(record.get("dwt")),
        grt=_maybe_round(record.get("grt")),
        teu=_maybe_round(record.get("teu")),
        dominant_destination=str(record.get("dominant_destination"))
        if pd.notna(record.get("dominant_destination"))
        else None,
        dominant_nav_status=str(record.get("dominant_nav_status"))
        if pd.notna(record.get("dominant_nav_status"))
        else None,
        profile_source=str(record.get("profile_source") or "ais_derived"),
        static_source=str(record.get("static_source")) if pd.notna(record.get("static_source")) else None,
    )


def _find_validation_summary(mmsi: str) -> ValidationSummary:
    summary = load_demo_payload()["validation_summary"]  # type: ignore[assignment]
    row = summary.loc[summary["mmsi"] == mmsi]
    if row.empty:
        return ValidationSummary(
            mmsi=mmsi,
            event_count=0,
            source_count=0,
            sources=[],
            latest_event_type=None,
            latest_event_start=None,
            latest_port_name=None,
            notes_count=0,
        )
    record = row.iloc[0]
    sources = str(record.get("sources") or "").split(" | ")
    sources = [source for source in sources if source]
    return ValidationSummary(
        mmsi=mmsi,
        event_count=int(record.get("event_count") or 0),
        source_count=int(record.get("source_count") or 0),
        sources=sources,
        latest_event_type=str(record.get("latest_event_type"))
        if pd.notna(record.get("latest_event_type"))
        else None,
        latest_event_start=str(record.get("latest_event_start"))
        if pd.notna(record.get("latest_event_start"))
        else None,
        latest_port_name=str(record.get("latest_port_name"))
        if pd.notna(record.get("latest_port_name"))
        else None,
        notes_count=int(record.get("notes_count") or 0),
    )


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


def get_competition_baseline_manifest() -> dict[str, object]:
    manifest = _load_json(COMPETITION_BASELINE_PATH)
    artifacts = manifest.get("artifacts", {})
    if not isinstance(artifacts, dict):
        raise ValueError(f"Invalid competition baseline artifacts in {COMPETITION_BASELINE_PATH}")

    resolved_artifacts: dict[str, str] = {}
    for name, relative_path in artifacts.items():
        if relative_path in (None, ""):
            continue
        artifact_path = (PROJECT_ROOT / str(relative_path)).resolve()
        if not artifact_path.exists():
            raise FileNotFoundError(
                f"Competition baseline artifact '{name}' is missing: {artifact_path}"
            )
        resolved_artifacts[name] = str(artifact_path)

    manifest["resolved_artifacts"] = resolved_artifacts
    return manifest


def _demo_source_bundle() -> dict[str, object]:
    if COMPETITION_BASELINE_PATH.exists():
        manifest = get_competition_baseline_manifest()
        artifacts = manifest["resolved_artifacts"]  # type: ignore[assignment]
        return {
            "source_mode": "competition_baseline",
            "baseline_version": manifest.get("version"),
            "manifest_path": COMPETITION_BASELINE_PATH,
            "window_label": str(manifest.get("window_label") or ""),
            "features_path": Path(artifacts["vessel_features"]),
            "risk_path": Path(artifacts["regional_risk"]),
            "report_path": Path(artifacts["voyage_report"]),
            "ais_path": Path(artifacts["processed_ais"]),
            "reference_path": Path(artifacts["reference_sites"]),
            "catalog_path": Path(artifacts["vessel_catalog"]) if "vessel_catalog" in artifacts else None,
            "static_path": Path(artifacts["vessel_static"]) if "vessel_static" in artifacts else None,
            "validation_summary_path": (
                Path(artifacts["validation_summary"]) if "validation_summary" in artifacts else None
            ),
            "validation_events_path": (
                Path(artifacts["validation_events"]) if "validation_events" in artifacts else None
            ),
        }

    return {
        "source_mode": "latest_files",
        "baseline_version": None,
        "manifest_path": None,
        "features_path": _latest_file(PROCESSED_DIR, "vessel_features_*.csv"),
        "risk_path": _latest_file(MAPS_DIR, "regional_risk_*.csv"),
        "report_path": _latest_file(REPORTS_DIR, "voyage_report_*.md"),
        "ais_path": _latest_file(PROCESSED_DIR, "ais_*_cleaned.csv"),
        "reference_path": REFERENCE_DIR / "singapore_reference_sites.csv",
        "catalog_path": _optional_latest_file(PROCESSED_DIR, "vessel_catalog*.csv"),
        "static_path": _optional_latest_file(EXTERNAL_DIR, "vessel_static*.csv"),
        "validation_summary_path": _optional_latest_file(PROCESSED_DIR, "validation_summary*.csv"),
        "validation_events_path": _optional_latest_file(EXTERNAL_DIR, "validation_events*.csv"),
    }


def _demo_payload_signature() -> tuple[str, ...]:
    source_bundle = _demo_source_bundle()
    signature_items: list[Path] = [
        source_bundle["features_path"],  # type: ignore[list-item]
        source_bundle["risk_path"],  # type: ignore[list-item]
        source_bundle["report_path"],  # type: ignore[list-item]
        source_bundle["ais_path"],  # type: ignore[list-item]
        source_bundle["reference_path"],  # type: ignore[list-item]
    ]

    manifest_path = source_bundle.get("manifest_path")
    if isinstance(manifest_path, Path) and manifest_path.exists():
        signature_items.append(manifest_path)

    optional_keys = [
        "catalog_path",
        "validation_summary_path",
        "static_path",
        "validation_events_path",
    ]
    for key in optional_keys:
        optional_path = source_bundle.get(key)
        if isinstance(optional_path, Path) and optional_path.exists():
            signature_items.append(optional_path)

    return tuple(
        f"{path.resolve()}::{path.stat().st_mtime_ns}"
        for path in signature_items
    )


@lru_cache(maxsize=4)
def _load_demo_payload_by_signature(signature: tuple[str, ...]) -> dict[str, object]:
    source_bundle = _demo_source_bundle()
    features_path = source_bundle["features_path"]  # type: ignore[assignment]
    risk_path = source_bundle["risk_path"]  # type: ignore[assignment]
    report_path = source_bundle["report_path"]  # type: ignore[assignment]
    ais_path = source_bundle["ais_path"]  # type: ignore[assignment]
    reference_path = source_bundle["reference_path"]  # type: ignore[assignment]

    features = _load_csv(features_path)
    risk = _load_csv(risk_path)
    ais = _load_ais_csv(ais_path)
    vessel_catalog = _load_vessel_catalog(
        ais,
        catalog_path=source_bundle.get("catalog_path"),  # type: ignore[arg-type]
        static_path=source_bundle.get("static_path"),  # type: ignore[arg-type]
    )
    validation_summary = _load_validation_summary(
        validation_summary_path=source_bundle.get("validation_summary_path"),  # type: ignore[arg-type]
        validation_events_path=source_bundle.get("validation_events_path"),  # type: ignore[arg-type]
    )
    reference_sites = _serialize_reference_sites(_load_reference_sites(reference_path))
    vessels = _serialize_vessels(features)
    risk_cells = _serialize_risk_cells(risk, reference_sites)
    window_label = str(source_bundle.get("window_label") or _window_label_from_features(features_path))
    recommendation_counts = _recommendation_counts(vessels)
    report_text = report_path.read_text(encoding="utf-8")

    payload = {
        "window_label": window_label,
        "vessels": vessels,
        "risk_cells": risk_cells,
        "reference_sites": reference_sites,
        "report_text": report_text,
        "ais": ais,
        "vessel_catalog": vessel_catalog,
        "validation_summary": validation_summary,
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


def load_demo_payload() -> dict[str, object]:
    return _load_demo_payload_by_signature(_demo_payload_signature())


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
    reference_sites = load_demo_payload()["reference_sites"]  # type: ignore[assignment]
    nearest_reference, nearest_distance = (
        _nearest_reference_from_sites(vessel.mean_latitude, vessel.mean_longitude, reference_sites)
        if vessel.mean_latitude is not None and vessel.mean_longitude is not None
        else (None, None)
    )
    return VesselDetailResponse(
        window_label=load_demo_payload()["window_label"],  # type: ignore[arg-type]
        vessel=vessel,
        cohort_size=len(vessels),
        rank_fraction=f"{vessel.rank} / {len(vessels)}",
        peer_vessels=peer_vessels,
        static_profile=_find_static_profile(mmsi),
        validation_summary=_find_validation_summary(mmsi),
        nearest_reference=nearest_reference,
        nearest_reference_distance_km=nearest_distance,
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
    reference_sites = load_demo_payload()["reference_sites"]  # type: ignore[assignment]
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
        reference_sites=reference_sites,
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
