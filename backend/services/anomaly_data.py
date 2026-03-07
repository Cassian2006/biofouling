from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

from backend.schemas.demo import (
    VesselAnomalyDetailResponse,
    VesselAnomalyRecord,
    VesselAnomalyResponse,
)
from backend.services.demo_data import PROCESSED_DIR, PROJECT_ROOT, _latest_file, _window_label_from_features


MODELS_DIR = PROJECT_ROOT / "outputs" / "models"


def _latest_anomaly_csv() -> Path:
    matches = sorted(MODELS_DIR.glob("exposure_autoencoder_*/evaluation/vessel_anomaly_scores.csv"))
    if not matches:
        raise FileNotFoundError("No exposure anomaly evaluation CSV found.")
    return matches[-1]


def _anomaly_signature() -> tuple[str, ...]:
    anomaly_path = _latest_anomaly_csv()
    features_path = _latest_file(PROCESSED_DIR, "vessel_features_*.csv")
    paths = [anomaly_path, features_path]
    return tuple(f"{path.resolve()}::{path.stat().st_mtime_ns}" for path in paths)


def _normalize_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    frame = dataframe.copy()
    frame.columns = [column.strip().lower() for column in frame.columns]
    frame["mmsi"] = frame["mmsi"].astype(str)
    return frame


def _explanations_from_row(row: pd.Series) -> list[str]:
    explanations = []
    for column in ["explanation_1", "explanation_2", "explanation_3"]:
        value = row.get(column)
        if pd.notna(value) and str(value).strip():
            explanations.append(str(value))
    return explanations


def _serialize_records(frame: pd.DataFrame) -> list[VesselAnomalyRecord]:
    records: list[VesselAnomalyRecord] = []
    for rank, row in enumerate(frame.itertuples(index=False), start=1):
        explanations = [
            str(value)
            for value in [getattr(row, "explanation_1", ""), getattr(row, "explanation_2", ""), getattr(row, "explanation_3", "")]
            if str(value).strip()
        ]
        records.append(
            VesselAnomalyRecord(
                rank=rank,
                mmsi=str(row.mmsi),
                anomaly_score=round(float(row.anomaly_score), 6),
                anomaly_level=str(row.anomaly_level),
                explanations=explanations,
            )
        )
    return records


@lru_cache(maxsize=4)
def _load_anomaly_payload_by_signature(signature: tuple[str, ...]) -> dict[str, object]:
    anomaly_path = _latest_anomaly_csv()
    features_path = _latest_file(PROCESSED_DIR, "vessel_features_*.csv")
    anomaly_frame = _normalize_columns(pd.read_csv(anomaly_path))
    anomaly_frame = anomaly_frame.sort_values(["anomaly_score", "mmsi"], ascending=[False, True]).reset_index(drop=True)
    window_label = _window_label_from_features(features_path)
    level_counts = (
        anomaly_frame["anomaly_level"].value_counts().reindex(["highly_abnormal", "suspicious", "normal"], fill_value=0).to_dict()
    )
    top_anomalies = _serialize_records(anomaly_frame.head(12))
    return {
        "window_label": window_label,
        "anomaly_frame": anomaly_frame,
        "summary": VesselAnomalyResponse(
            window_label=window_label,
            vessel_count=int(len(anomaly_frame)),
            anomaly_level_counts={str(key): int(value) for key, value in level_counts.items()},
            top_anomalies=top_anomalies,
        ),
    }


def load_anomaly_payload() -> dict[str, object]:
    return _load_anomaly_payload_by_signature(_anomaly_signature())


def get_demo_anomaly_summary() -> VesselAnomalyResponse:
    return load_anomaly_payload()["summary"]  # type: ignore[return-value]


def get_vessel_anomaly_detail(mmsi: str) -> VesselAnomalyDetailResponse:
    payload = load_anomaly_payload()
    anomaly_frame = payload["anomaly_frame"]  # type: ignore[assignment]
    row = anomaly_frame.loc[anomaly_frame["mmsi"] == str(mmsi)]
    if row.empty:
        raise LookupError(f"Anomaly detail for vessel {mmsi} not found")

    record = row.iloc[0]
    rank = int(row.index[0]) + 1
    percentile_rank = round(1 - ((rank - 1) / max(len(anomaly_frame) - 1, 1)), 4)
    peer_frame = anomaly_frame.loc[anomaly_frame["mmsi"] != str(mmsi)].head(6).reset_index(drop=True)
    return VesselAnomalyDetailResponse(
        window_label=payload["window_label"],  # type: ignore[arg-type]
        mmsi=str(mmsi),
        anomaly_score=round(float(record["anomaly_score"]), 6),
        anomaly_level=str(record["anomaly_level"]),
        percentile_rank=percentile_rank,
        explanations=_explanations_from_row(record),
        peer_anomalies=_serialize_records(peer_frame),
    )
