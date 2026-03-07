import numpy as np

from scripts.evaluate_fpi_lstm import (
    assign_risk_label_with_thresholds,
    compute_classification_metrics,
    compute_regression_metrics,
    optimize_label_thresholds,
)


def test_compute_regression_metrics_returns_expected_values() -> None:
    actual = np.array([0.2, 0.4, 0.6, 0.8], dtype=float)
    predicted = np.array([0.3, 0.5, 0.5, 0.9], dtype=float)

    metrics = compute_regression_metrics(actual, predicted)

    assert round(metrics["mae"], 6) == 0.1
    assert round(metrics["rmse"], 6) == 0.1
    assert round(metrics["mse"], 6) == 0.01
    assert round(metrics["r2"], 6) == 0.8


def test_compute_classification_metrics_returns_accuracy_and_confusion() -> None:
    actual_labels = ["low", "medium", "high", "high"]
    predicted_labels = ["low", "high", "high", "medium"]

    metrics = compute_classification_metrics(actual_labels, predicted_labels)

    assert round(float(metrics["accuracy"]), 6) == 0.5
    assert metrics["labels"] == ["low", "medium", "high"]
    assert metrics["confusion"]["low"]["low"] == 1
    assert metrics["confusion"]["medium"]["high"] == 1
    assert metrics["confusion"]["high"]["medium"] == 1
    assert round(float(metrics["balanced_accuracy"]), 6) == 0.5


def test_optimize_label_thresholds_improves_macro_f1_on_toy_scores() -> None:
    actual = np.array([0.18, 0.32, 0.46, 0.51, 0.73, 0.81], dtype=float)
    predicted = np.array([0.22, 0.44, 0.48, 0.57, 0.66, 0.78], dtype=float)

    default_actual_labels = [assign_risk_label_with_thresholds(value, 0.4, 0.7) for value in actual.tolist()]
    default_predicted_labels = [
        assign_risk_label_with_thresholds(value, 0.4, 0.7) for value in predicted.tolist()
    ]
    default_metrics = compute_classification_metrics(default_actual_labels, default_predicted_labels)

    optimized = optimize_label_thresholds(actual, predicted, objective="macro_f1", step=0.05)

    assert 0.2 <= float(optimized["low_threshold"]) < float(optimized["high_threshold"]) <= 0.9
    assert float(optimized["classification_metrics"]["macro_f1"]) >= float(default_metrics["macro_f1"])
