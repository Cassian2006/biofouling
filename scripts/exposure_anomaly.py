from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


ANOMALY_FEATURE_COLUMNS = [
    "ping_count",
    "low_speed_ratio",
    "mean_sst",
    "mean_chlorophyll_a",
    "mean_salinity",
    "current_speed",
    "track_duration_hours",
    "fpi_proxy",
    "ecp_proxy",
]

ANOMALY_TYPE_SPARSE = "sparse_observation"
ANOMALY_TYPE_LONG_LOW_SPEED = "long_dwell_low_speed"
ANOMALY_TYPE_WARM_PRODUCTIVE = "warm_productive_water"
ANOMALY_TYPE_MIXED = "mixed_anomaly"

ANOMALY_TYPE_LABELS = {
    ANOMALY_TYPE_SPARSE: "观测稀疏型",
    ANOMALY_TYPE_LONG_LOW_SPEED: "长时低速型",
    ANOMALY_TYPE_WARM_PRODUCTIVE: "高温高叶绿素型",
    ANOMALY_TYPE_MIXED: "混合异常型",
}


def _safe_float(value: object, default: float = 0.0) -> float:
    numeric = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric):
        return default
    return float(numeric)

MIN_OBSERVATION_PINGS = 50
MIN_OBSERVATION_HOURS = 12.0
SUSPICIOUS_SCORE_THRESHOLD = 0.12
HIGHLY_ABNORMAL_SCORE_THRESHOLD = 0.35


@dataclass
class ScalingStats:
    means: dict[str, float]
    stds: dict[str, float]


def load_vessel_features(path: Path) -> pd.DataFrame:
    dataframe = pd.read_csv(path)
    dataframe.columns = [column.strip().lower() for column in dataframe.columns]
    dataframe["mmsi"] = dataframe["mmsi"].astype(str)
    return dataframe


def prepare_anomaly_features(dataframe: pd.DataFrame) -> pd.DataFrame:
    frame = dataframe.copy()
    for column in [
        "ping_count",
        "low_speed_ratio",
        "mean_sst",
        "mean_chlorophyll_a",
        "mean_salinity",
        "mean_current_u",
        "mean_current_v",
        "track_duration_hours",
        "fpi_proxy",
        "ecp_proxy",
    ]:
        if column not in frame.columns:
            frame[column] = np.nan
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame["current_speed"] = np.sqrt(
        np.square(frame["mean_current_u"].fillna(0.0))
        + np.square(frame["mean_current_v"].fillna(0.0))
    )
    prepared = frame[["mmsi"] + ANOMALY_FEATURE_COLUMNS].copy()
    prepared[ANOMALY_FEATURE_COLUMNS] = prepared[ANOMALY_FEATURE_COLUMNS].fillna(
        prepared[ANOMALY_FEATURE_COLUMNS].median(numeric_only=True)
    )
    return prepared


def fit_scaler(dataframe: pd.DataFrame, feature_columns: list[str] | None = None) -> ScalingStats:
    feature_columns = feature_columns or ANOMALY_FEATURE_COLUMNS
    means: dict[str, float] = {}
    stds: dict[str, float] = {}
    for column in feature_columns:
        means[column] = float(dataframe[column].mean())
        std = float(dataframe[column].std(ddof=0))
        stds[column] = std if std > 1e-9 else 1.0
    return ScalingStats(means=means, stds=stds)


def transform_with_scaler(
    dataframe: pd.DataFrame,
    scaling: ScalingStats,
    feature_columns: list[str] | None = None,
) -> np.ndarray:
    feature_columns = feature_columns or ANOMALY_FEATURE_COLUMNS
    matrix = []
    for column in feature_columns:
        values = pd.to_numeric(dataframe[column], errors="coerce").fillna(scaling.means[column])
        normalized = (values - scaling.means[column]) / scaling.stds[column]
        matrix.append(normalized.to_numpy(dtype=np.float32))
    return np.column_stack(matrix).astype(np.float32)


def split_train_validation(
    dataframe: pd.DataFrame,
    *,
    validation_fraction: float = 0.2,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if dataframe.empty:
        return dataframe.copy(), dataframe.copy()

    shuffled = dataframe.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    split_index = max(1, int(len(shuffled) * (1 - validation_fraction)))
    split_index = min(split_index, len(shuffled) - 1) if len(shuffled) > 1 else len(shuffled)
    if split_index <= 0:
        split_index = len(shuffled)
    train = shuffled.iloc[:split_index].reset_index(drop=True)
    validation = shuffled.iloc[split_index:].reset_index(drop=True)
    if validation.empty:
        validation = train.copy()
    return train, validation


def classify_anomaly_levels(
    scores: pd.Series,
    dataframe: pd.DataFrame | None = None,
) -> pd.Series:
    if scores.empty:
        return pd.Series(dtype=str)

    frame = dataframe.reindex(scores.index) if dataframe is not None else pd.DataFrame(index=scores.index)
    ping_count = pd.to_numeric(frame["ping_count"], errors="coerce") if "ping_count" in frame else None
    duration_hours = pd.to_numeric(frame["track_duration_hours"], errors="coerce") if "track_duration_hours" in frame else None

    labels: list[str] = []
    for index, value in scores.items():
        if ping_count is not None and duration_hours is not None:
            if float(ping_count.loc[index]) < MIN_OBSERVATION_PINGS or float(duration_hours.loc[index]) < MIN_OBSERVATION_HOURS:
                labels.append("observation_insufficient")
                continue
        if float(value) >= HIGHLY_ABNORMAL_SCORE_THRESHOLD:
            labels.append("highly_abnormal")
        elif float(value) >= SUSPICIOUS_SCORE_THRESHOLD:
            labels.append("suspicious")
        else:
            labels.append("normal")

    return pd.Series(labels, index=scores.index)


def classify_anomaly_type(
    row: pd.Series,
    cohort_frame: pd.DataFrame,
) -> str:
    ping_count = _safe_float(row.get("ping_count"))
    duration_hours = _safe_float(row.get("track_duration_hours"))
    if ping_count < MIN_OBSERVATION_PINGS or duration_hours < MIN_OBSERVATION_HOURS:
        return ANOMALY_TYPE_SPARSE

    if cohort_frame.empty:
        return ANOMALY_TYPE_MIXED

    low_speed_threshold = float(cohort_frame["low_speed_ratio"].quantile(0.75))
    duration_threshold = float(cohort_frame["track_duration_hours"].quantile(0.75))
    sst_threshold = float(cohort_frame["mean_sst"].quantile(0.75))
    chlorophyll_threshold = float(cohort_frame["mean_chlorophyll_a"].quantile(0.75))

    low_speed_ratio = _safe_float(row.get("low_speed_ratio"))
    mean_sst = _safe_float(row.get("mean_sst"))
    mean_chlorophyll = _safe_float(row.get("mean_chlorophyll_a"))

    if low_speed_ratio >= low_speed_threshold and duration_hours >= duration_threshold:
        return ANOMALY_TYPE_LONG_LOW_SPEED
    if mean_sst >= sst_threshold and mean_chlorophyll >= chlorophyll_threshold:
        return ANOMALY_TYPE_WARM_PRODUCTIVE
    return ANOMALY_TYPE_MIXED


def build_anomaly_type_summary(
    row: pd.Series,
    cohort_frame: pd.DataFrame,
    anomaly_type: str | None = None,
) -> str:
    resolved_type = anomaly_type or classify_anomaly_type(row, cohort_frame)
    if resolved_type == ANOMALY_TYPE_SPARSE:
        return "当前轨迹点数或覆盖时长不足，异常判断主要受观测充分性限制。"
    if resolved_type == ANOMALY_TYPE_LONG_LOW_SPEED:
        return "该船在较长时间内维持低速或停留状态，属于以行为暴露为主的异常模式。"
    if resolved_type == ANOMALY_TYPE_WARM_PRODUCTIVE:
        return "该船长期处于较高海温与较高叶绿素环境，属于以环境暴露为主的异常模式。"
    return "该船同时存在多项偏离信号，异常来源并非单一因素。"


def explain_anomaly_row(
    original_row: pd.Series,
    reconstructed_row: np.ndarray,
    feature_columns: list[str] | None = None,
    top_k: int = 3,
) -> list[str]:
    feature_columns = feature_columns or ANOMALY_FEATURE_COLUMNS
    residuals = []
    for index, column in enumerate(feature_columns):
        delta = float(original_row[column]) - float(reconstructed_row[index])
        residuals.append((column, abs(delta), delta))
    residuals.sort(key=lambda item: item[1], reverse=True)

    explanations: list[str] = []
    for column, _, delta in residuals[:top_k]:
        direction = "higher than" if delta > 0 else "lower than"
        explanations.append(f"{column} {direction} model reconstruction")
    return explanations
