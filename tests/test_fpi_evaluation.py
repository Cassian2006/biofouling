import numpy as np

from scripts.evaluate_fpi_lstm import compute_classification_metrics, compute_regression_metrics


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
