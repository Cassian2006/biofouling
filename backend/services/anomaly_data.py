from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

from backend.schemas.demo import (
    VesselAnomalyDetailResponse,
    VesselAnomalyDriver,
    VesselAnomalyRecord,
    VesselAnomalyResponse,
)
from backend.services.demo_data import PROCESSED_DIR, PROJECT_ROOT, _latest_file, _window_label_from_features
from scripts.exposure_anomaly import (
    ANOMALY_TYPE_LABELS,
    build_anomaly_type_summary,
    classify_anomaly_type,
)


MODELS_DIR = PROJECT_ROOT / "outputs" / "models"

FEATURE_LABELS = {
    "ping_count": "轨迹点数",
    "low_speed_ratio": "低速暴露比例",
    "mean_sst": "平均海温暴露",
    "mean_chlorophyll_a": "平均叶绿素暴露",
    "mean_salinity": "平均盐度暴露",
    "current_speed": "海流强度",
    "track_duration_hours": "轨迹时长",
    "fpi_proxy": "FPI 代理值",
    "ecp_proxy": "ECP 代理值",
}

FEATURE_INTERPRETATIONS = {
    "ping_count": "说明该船在研究窗口内的活动记录密度与同批对象差异明显。",
    "low_speed_ratio": "说明该船的停留、等待或低速活动结构偏离样本主流。",
    "mean_sst": "说明该船暴露的海温条件与同批对象差异较大。",
    "mean_chlorophyll_a": "说明该船处于更特殊的生物活跃环境。",
    "mean_salinity": "说明该船接触到的盐度环境与样本主流不同。",
    "current_speed": "说明该船所处水动力环境强度存在明显偏离。",
    "track_duration_hours": "说明该船在研究窗口内的停留跨度与主流对象不同。",
    "fpi_proxy": "说明规则链路下的污损倾向判断与同批船差异较大。",
    "ecp_proxy": "说明环境复合压力与同批对象相比更突出。",
}


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


def _cohort_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.loc[frame["anomaly_level"] != "observation_insufficient"].reset_index(drop=True)


def _metric_value(row: pd.Series, feature_key: str) -> float | None:
    value = row.get(feature_key)
    if pd.isna(value):
        return None
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def _parse_explanation(explanation: str) -> tuple[str | None, str]:
    normalized = str(explanation).strip()
    if not normalized:
        return None, ""
    if " higher than " in normalized:
        feature_key = normalized.split(" higher than ", 1)[0].strip()
        return feature_key, "higher"
    if " lower than " in normalized:
        feature_key = normalized.split(" lower than ", 1)[0].strip()
        return feature_key, "lower"
    return None, normalized


def _driver_interpretation(feature_key: str, direction: str) -> str:
    base = FEATURE_INTERPRETATIONS.get(feature_key, "说明该特征与同批对象相比存在明显偏离。")
    if direction == "higher":
        return f"{base[:-1]}，且当前对象处于相对偏高水平。"
    if direction == "lower":
        return f"{base[:-1]}，且当前对象处于相对偏低水平。"
    return base


def _build_driver_details(row: pd.Series, cohort_frame: pd.DataFrame) -> list[VesselAnomalyDriver]:
    drivers: list[VesselAnomalyDriver] = []
    for column_name in ["explanation_1", "explanation_2", "explanation_3"]:
        explanation = row.get(column_name)
        if pd.isna(explanation) or not str(explanation).strip():
            continue
        feature_key, direction = _parse_explanation(str(explanation))
        if feature_key is None:
            continue
        cohort_median = None
        if feature_key in cohort_frame.columns:
            cohort_median = _metric_value(pd.Series({feature_key: cohort_frame[feature_key].median()}), feature_key)
        drivers.append(
            VesselAnomalyDriver(
                feature_key=feature_key,
                feature_label=FEATURE_LABELS.get(feature_key, feature_key),
                vessel_value=_metric_value(row, feature_key),
                cohort_median=cohort_median,
                direction=direction,
                interpretation=_driver_interpretation(feature_key, direction),
            )
        )
    return drivers


def _anomaly_severity(row: pd.Series) -> str:
    level = str(row.get("anomaly_level", "normal"))
    score = float(row.get("anomaly_score", 0.0))
    if level == "observation_insufficient":
        return "证据不足"
    if level == "highly_abnormal":
        return "高" if score >= 0.6 else "中高"
    if level == "suspicious":
        return "中" if score >= 0.2 else "中低"
    return "低"


def _dominant_evidence(drivers: list[VesselAnomalyDriver]) -> tuple[str | None, str | None]:
    if not drivers:
        return None, None
    primary = drivers[0]
    direction = "偏高" if primary.direction == "higher" else "偏低" if primary.direction == "lower" else "偏离"
    title = f"{primary.feature_label}{direction}"
    return title, primary.interpretation


def _build_summary_sentence(
    row: pd.Series,
    cohort_frame: pd.DataFrame,
) -> str:
    mmsi = str(row["mmsi"])
    level = str(row["anomaly_level"])
    if level == "observation_insufficient":
        ping_count = int(float(row.get("ping_count", 0)))
        duration = round(float(row.get("track_duration_hours", 0.0)), 1)
        return f"该船当前仅有 {ping_count} 个 AIS 点、约 {duration} 小时轨迹，观测不足，暂不参与异常排序。"

    drivers = _build_driver_details(row, cohort_frame)
    if not drivers:
        return f"该船当前被识别为{level}，但暂缺可解释的主导偏离项。"

    level_label = "高度异常" if level == "highly_abnormal" else "需复核" if level == "suspicious" else "正常"
    lead_labels = "、".join(driver.feature_label for driver in drivers[:2])
    trend_words = []
    for driver in drivers[:2]:
        if driver.direction == "higher":
            trend_words.append(f"{driver.feature_label}偏高")
        elif driver.direction == "lower":
            trend_words.append(f"{driver.feature_label}偏低")
    trend_phrase = "，".join(trend_words) if trend_words else lead_labels
    return f"这艘船的主要问题在于 {trend_phrase}，其暴露模式在同批船舶中属于{level_label}。"


def _anomaly_type_fields(row: pd.Series, cohort_frame: pd.DataFrame) -> tuple[str, str, str]:
    anomaly_type = classify_anomaly_type(row, cohort_frame)
    type_label = ANOMALY_TYPE_LABELS.get(anomaly_type, anomaly_type)
    type_summary = build_anomaly_type_summary(row, cohort_frame, anomaly_type)
    return anomaly_type, type_label, type_summary


def _explanations_from_row(row: pd.Series) -> list[str]:
    explanations = []
    for column in ["explanation_1", "explanation_2", "explanation_3"]:
        value = row.get(column)
        if pd.notna(value) and str(value).strip():
            explanations.append(str(value))
    return explanations


def _serialize_records(frame: pd.DataFrame, cohort_frame: pd.DataFrame) -> list[VesselAnomalyRecord]:
    records: list[VesselAnomalyRecord] = []
    for rank, row in enumerate(frame.itertuples(index=False), start=1):
        row_series = pd.Series(row._asdict())
        drivers = _build_driver_details(row_series, cohort_frame)
        dominant_title, _ = _dominant_evidence(drivers)
        explanations = [
            str(value)
            for value in [getattr(row, "explanation_1", ""), getattr(row, "explanation_2", ""), getattr(row, "explanation_3", "")]
            if str(value).strip()
        ]
        anomaly_type, anomaly_type_label, anomaly_type_summary = _anomaly_type_fields(row_series, cohort_frame)
        records.append(
            VesselAnomalyRecord(
                rank=rank,
                mmsi=str(row.mmsi),
                anomaly_score=round(float(row.anomaly_score), 6),
                anomaly_level=str(row.anomaly_level),
                anomaly_severity=_anomaly_severity(row_series),
                anomaly_type=anomaly_type,
                anomaly_type_label=anomaly_type_label,
                anomaly_type_summary=anomaly_type_summary,
                dominant_evidence=dominant_title,
                explanations=explanations,
                summary_sentence=_build_summary_sentence(row_series, cohort_frame),
            )
        )
    return records


@lru_cache(maxsize=4)
def _load_anomaly_payload_by_signature(signature: tuple[str, ...]) -> dict[str, object]:
    anomaly_path = _latest_anomaly_csv()
    features_path = _latest_file(PROCESSED_DIR, "vessel_features_*.csv")
    anomaly_frame = _normalize_columns(pd.read_csv(anomaly_path))
    anomaly_frame = anomaly_frame.sort_values(["anomaly_score", "mmsi"], ascending=[False, True]).reset_index(drop=True)
    cohort_frame = _cohort_frame(anomaly_frame)
    window_label = _window_label_from_features(features_path)
    level_counts = (
        anomaly_frame["anomaly_level"]
        .value_counts()
        .reindex(["highly_abnormal", "suspicious", "normal", "observation_insufficient"], fill_value=0)
        .to_dict()
    )
    type_counts = (
        anomaly_frame.apply(lambda row: classify_anomaly_type(row, anomaly_frame), axis=1)
        .value_counts()
        .reindex(
            ["long_dwell_low_speed", "warm_productive_water", "mixed_anomaly", "sparse_observation"],
            fill_value=0,
        )
        .to_dict()
    )
    top_anomalies = _serialize_records(cohort_frame.head(12), cohort_frame)
    return {
        "window_label": window_label,
        "anomaly_frame": anomaly_frame,
        "cohort_frame": cohort_frame,
        "summary": VesselAnomalyResponse(
            window_label=window_label,
            vessel_count=int(len(anomaly_frame)),
            anomaly_level_counts={str(key): int(value) for key, value in level_counts.items()},
            anomaly_type_counts={str(key): int(value) for key, value in type_counts.items()},
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
    cohort_frame = payload["cohort_frame"]  # type: ignore[assignment]
    row = anomaly_frame.loc[anomaly_frame["mmsi"] == str(mmsi)]
    if row.empty:
        raise LookupError(f"Anomaly detail for vessel {mmsi} not found")

    record = row.iloc[0]
    rank = int(row.index[0]) + 1
    percentile_rank = round(1 - ((rank - 1) / max(len(anomaly_frame) - 1, 1)), 4)
    peer_frame = cohort_frame.loc[cohort_frame["mmsi"] != str(mmsi)].head(6).reset_index(drop=True)
    driver_details = _build_driver_details(record, cohort_frame)
    dominant_title, dominant_summary = _dominant_evidence(driver_details)
    anomaly_type, anomaly_type_label, anomaly_type_summary = _anomaly_type_fields(record, cohort_frame)
    return VesselAnomalyDetailResponse(
        window_label=payload["window_label"],  # type: ignore[arg-type]
        mmsi=str(mmsi),
        anomaly_score=round(float(record["anomaly_score"]), 6),
        anomaly_level=str(record["anomaly_level"]),
        anomaly_severity=_anomaly_severity(record),
        anomaly_type=anomaly_type,
        anomaly_type_label=anomaly_type_label,
        anomaly_type_summary=anomaly_type_summary,
        dominant_evidence_title=dominant_title,
        dominant_evidence_summary=dominant_summary,
        percentile_rank=percentile_rank,
        summary_sentence=_build_summary_sentence(record, cohort_frame),
        explanations=_explanations_from_row(record),
        driver_details=driver_details,
        peer_anomalies=_serialize_records(peer_frame, cohort_frame),
    )
