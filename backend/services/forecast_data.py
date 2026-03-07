from __future__ import annotations

from functools import lru_cache
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from backend.schemas.demo import ForecastSignal, VesselForecastResponse
from backend.services.demo_data import (
    PROCESSED_DIR,
    PROJECT_ROOT,
    _latest_file,
    _load_ais_csv,
    _load_csv,
    _window_label_from_features,
)
from scripts.evaluate_fpi_lstm import (
    DEFAULT_HIGH_THRESHOLD,
    DEFAULT_LOW_THRESHOLD,
    assign_risk_label_with_thresholds,
)
from scripts.fpi_forecast import build_latest_inference_sequences, build_window_feature_frame
from scripts.train_fpi_lstm import LSTMForecaster, require_torch


MODELS_DIR = PROJECT_ROOT / "outputs" / "models"


def _optional_latest_file(directory: Path, pattern: str) -> Path | None:
    matches = sorted(directory.glob(pattern))
    if not matches:
        return None
    return matches[-1]


def _forecast_signature() -> tuple[str, ...]:
    features_path = _latest_file(PROCESSED_DIR, "vessel_features_*.csv")
    ais_path = _latest_file(PROCESSED_DIR, "ais_*_cleaned.csv")
    env_path = _optional_latest_file(PROCESSED_DIR, "env_*.csv")
    model_dir = _select_best_model_dir()

    signature_paths = [features_path, ais_path, model_dir / "model.pt", model_dir / "metrics.json"]
    evaluation_path = model_dir / "evaluation" / "evaluation.json"
    if evaluation_path.exists():
        signature_paths.append(evaluation_path)
    predictions_path = model_dir / "evaluation" / "validation_predictions.csv"
    if predictions_path.exists():
        signature_paths.append(predictions_path)
    if env_path is not None:
        signature_paths.append(env_path)

    return tuple(
        f"{path.resolve()}::{path.stat().st_mtime_ns}"
        for path in signature_paths
        if path.exists()
    )


def _select_best_model_dir() -> Path:
    if not MODELS_DIR.exists():
        raise FileNotFoundError("No model directory available under outputs/models.")

    candidates = []
    for candidate in sorted(MODELS_DIR.glob("fpi_lstm_*")):
        if not candidate.is_dir():
            continue
        metrics_path = candidate / "metrics.json"
        model_path = candidate / "model.pt"
        if not metrics_path.exists() or not model_path.exists():
            continue

        evaluation_path = candidate / "evaluation" / "evaluation.json"
        if evaluation_path.exists():
            evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
            score = float(evaluation["regression_metrics"]["rmse"])
        else:
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            score = float(metrics.get("best_val_loss", 999.0))
        candidates.append((score, candidate))

    if not candidates:
        raise FileNotFoundError("No usable FPI forecast model found.")
    return min(candidates, key=lambda item: item[0])[1]


def _zscore(value: float | None, series: pd.Series) -> float:
    if value is None or pd.isna(value):
        return 0.0
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return 0.0
    std = float(numeric.std(ddof=0))
    if std <= 1e-9:
        return 0.0
    return (float(value) - float(numeric.mean())) / std


def _confidence_level(predicted_fpi: float, low_threshold: float, high_threshold: float, rmse: float | None) -> str:
    if rmse is None:
        return "medium"
    margin = min(abs(predicted_fpi - low_threshold), abs(predicted_fpi - high_threshold))
    if margin >= rmse:
        return "high"
    if margin >= rmse * 0.5:
        return "medium"
    return "low"


def _build_signals(inference_frame: pd.DataFrame, row: pd.Series) -> list[ForecastSignal]:
    latest_step = max(int(column[1:3]) for column in inference_frame.columns if column.startswith("t"))
    suffix = f"t{latest_step:02d}_"
    candidates = [
        {
            "title": "近期低速暴露",
            "value": row.get(f"{suffix}low_speed_ratio"),
            "score": _zscore(row.get(f"{suffix}low_speed_ratio"), inference_frame[f"{suffix}low_speed_ratio"]),
            "detail": "最近一个 6 小时窗口的低速比例高于同批船舶。",
        },
        {
            "title": "近期平均航速偏低",
            "value": row.get(f"{suffix}mean_sog"),
            "score": -_zscore(row.get(f"{suffix}mean_sog"), inference_frame[f"{suffix}mean_sog"]),
            "detail": "最近一个 6 小时窗口的平均航速偏低，通常意味着等待或低速通行暴露更强。",
        },
        {
            "title": "海温暴露偏高",
            "value": row.get(f"{suffix}mean_sst"),
            "score": _zscore(row.get(f"{suffix}mean_sst"), inference_frame[f"{suffix}mean_sst"]),
            "detail": "最近窗口的海温暴露高于样本均值。",
        },
        {
            "title": "叶绿素暴露偏高",
            "value": row.get(f"{suffix}mean_chlorophyll_a"),
            "score": _zscore(
                row.get(f"{suffix}mean_chlorophyll_a"),
                inference_frame[f"{suffix}mean_chlorophyll_a"],
            ),
            "detail": "最近窗口的叶绿素暴露高于样本均值，意味着更活跃的生物环境。",
        },
    ]

    selected: list[ForecastSignal] = []
    for candidate in sorted(candidates, key=lambda item: float(item["score"]), reverse=True):
        if len(selected) >= 3:
            break
        if float(candidate["score"]) <= 0.15:
            continue
        value = candidate["value"]
        rendered_value = "暂无"
        if value is not None and not pd.isna(value):
            rendered_value = f"{float(value):.3f}"
        selected.append(
            ForecastSignal(
                title=str(candidate["title"]),
                value=rendered_value,
                assessment="偏高",
                detail=str(candidate["detail"]),
            )
        )

    if selected:
        return selected

    return [
        ForecastSignal(
            title="近期暴露结构",
            value="样本中等",
            assessment="平稳",
            detail="最近连续窗口的行为与环境暴露没有明显偏离当前样本分布。",
        )
    ]


@lru_cache(maxsize=2)
def _load_forecast_payload_by_signature(signature: tuple[str, ...]) -> dict[str, object]:
    model_dir = _select_best_model_dir()
    metrics = json.loads((model_dir / "metrics.json").read_text(encoding="utf-8"))
    evaluation_path = model_dir / "evaluation" / "evaluation.json"
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8")) if evaluation_path.exists() else {}

    calibration = evaluation.get("label_calibration", {})
    low_threshold = float(calibration.get("low_threshold", DEFAULT_LOW_THRESHOLD))
    high_threshold = float(calibration.get("high_threshold", DEFAULT_HIGH_THRESHOLD))
    validation_rmse = evaluation.get("regression_metrics", {}).get("rmse")
    validation_r2 = evaluation.get("regression_metrics", {}).get("r2")
    raw_accuracy = evaluation.get("classification_metrics", {}).get("accuracy")
    calibrated_accuracy = calibration.get("classification_metrics", {}).get("accuracy")

    history_windows = int(metrics["history_steps"])
    window_hours = 6
    features_path = _latest_file(PROCESSED_DIR, "vessel_features_*.csv")
    ais_path = _latest_file(PROCESSED_DIR, "ais_*_cleaned.csv")
    env_path = _optional_latest_file(PROCESSED_DIR, "env_*.csv")
    ais = _load_ais_csv(ais_path)
    env = _load_csv(env_path) if env_path is not None else None
    window_features = build_window_feature_frame(ais, env, window_hours=window_hours, min_pings=4)
    inference_frame = build_latest_inference_sequences(
        window_features,
        history_windows=history_windows,
    )
    if inference_frame.empty:
        raise LookupError("No latest inference sequences available for forecasting.")

    feature_columns = metrics["feature_columns"]
    input_size = int(metrics["input_size"])
    features = inference_frame[feature_columns].fillna(0.0).to_numpy(dtype=np.float32)
    features = features.reshape(len(inference_frame), history_windows, input_size)

    torch, nn, _, _, _ = require_torch()
    try:
        state_dict = torch.load(model_dir / "model.pt", map_location="cpu", weights_only=True)
    except TypeError:  # pragma: no cover - older torch compatibility
        state_dict = torch.load(model_dir / "model.pt", map_location="cpu")
    model = LSTMForecaster.build(
        nn,
        input_size=input_size,
        hidden_size=int(metrics["hidden_size"]),
        layers=int(metrics["layers"]),
    )
    model.load_state_dict(state_dict)
    model.eval()

    with torch.no_grad():
        predictions = model(torch.tensor(features)).numpy()

    forecast_rows = []
    for index, prediction in enumerate(predictions.tolist()):
        row = inference_frame.iloc[index]
        predicted_fpi = round(float(prediction), 4)
        raw_label = assign_risk_label_with_thresholds(
            predicted_fpi,
            DEFAULT_LOW_THRESHOLD,
            DEFAULT_HIGH_THRESHOLD,
        )
        calibrated_label = assign_risk_label_with_thresholds(
            predicted_fpi,
            low_threshold,
            high_threshold,
        )
        rmse_value = float(validation_rmse) if validation_rmse is not None else None
        forecast_rows.append(
            {
                "mmsi": str(row["mmsi"]),
                "window_label": _window_label_from_features(features_path),
                "history_start": str(row["history_start"]),
                "history_end": str(row["history_end"]),
                "forecast_window_start": str(row["forecast_window_start"]),
                "forecast_window_end": str(row["forecast_window_end"]),
                "predicted_fpi": predicted_fpi,
                "predicted_risk_label": calibrated_label,
                "raw_predicted_risk_label": raw_label,
                "low_threshold": round(low_threshold, 3),
                "high_threshold": round(high_threshold, 3),
                "validation_rmse": round(rmse_value, 4) if rmse_value is not None else None,
                "validation_r2": round(float(validation_r2), 4) if validation_r2 is not None else None,
                "raw_accuracy": round(float(raw_accuracy), 4) if raw_accuracy is not None else None,
                "calibrated_accuracy": round(float(calibrated_accuracy), 4)
                if calibrated_accuracy is not None
                else None,
                "confidence_band_low": round(max(0.0, predicted_fpi - (rmse_value or 0.0)), 4),
                "confidence_band_high": round(min(1.0, predicted_fpi + (rmse_value or 0.0)), 4),
                "confidence_level": _confidence_level(predicted_fpi, low_threshold, high_threshold, rmse_value),
                "model_name": model_dir.name,
                "history_windows": history_windows,
                "window_hours": window_hours,
                "signals": _build_signals(inference_frame, row),
            }
        )

    return {
        "model_dir": model_dir,
        "forecasts": forecast_rows,
    }


def load_forecast_payload() -> dict[str, object]:
    return _load_forecast_payload_by_signature(_forecast_signature())


def get_vessel_forecast(mmsi: str) -> VesselForecastResponse:
    forecasts = load_forecast_payload()["forecasts"]  # type: ignore[assignment]
    for forecast in forecasts:
        if forecast["mmsi"] == mmsi:
            return VesselForecastResponse(**forecast)
    raise LookupError(f"Forecast for vessel {mmsi} not found")
