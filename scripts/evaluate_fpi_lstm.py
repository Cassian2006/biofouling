from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from scripts.fpi_forecast import assign_risk_label
    from scripts.train_fpi_lstm import LSTMForecaster, load_dataset, require_torch, split_by_vessel
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from fpi_forecast import assign_risk_label  # type: ignore
    from train_fpi_lstm import (  # type: ignore
        LSTMForecaster,
        load_dataset,
        require_torch,
        split_by_vessel,
    )


DEFAULT_LOW_THRESHOLD = 0.4
DEFAULT_HIGH_THRESHOLD = 0.7


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a trained FPI LSTM model.")
    parser.add_argument("--dataset", required=True, help="Path to sequence dataset CSV.")
    parser.add_argument(
        "--model-dir",
        required=True,
        help="Directory containing model.pt and metrics.json from training.",
    )
    parser.add_argument(
        "--output-dir",
        help="Directory for evaluation outputs. Defaults to <model-dir>/evaluation.",
    )
    return parser.parse_args()


def assign_risk_label_with_thresholds(
    score: float,
    low_threshold: float = DEFAULT_LOW_THRESHOLD,
    high_threshold: float = DEFAULT_HIGH_THRESHOLD,
) -> str:
    if score >= high_threshold:
        return "high"
    if score >= low_threshold:
        return "medium"
    return "low"


def infer_architecture_from_state_dict(state_dict: dict[str, object]) -> tuple[int, int]:
    weight_key = "lstm.weight_ih_l0"
    if weight_key not in state_dict:
        raise ValueError("State dict does not contain LSTM input weights.")
    input_size = int(state_dict[weight_key].shape[1])  # type: ignore[index]
    hidden_size = int(state_dict[weight_key].shape[0] // 4)  # type: ignore[index]
    layers = len([key for key in state_dict if key.startswith("lstm.weight_ih_l")])
    return input_size, max(layers, 1)


def compute_regression_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    residual = predicted - actual
    mse = float(np.mean(np.square(residual)))
    mae = float(np.mean(np.abs(residual)))
    actual_mean = float(np.mean(actual))
    total_variance = float(np.sum(np.square(actual - actual_mean)))
    residual_variance = float(np.sum(np.square(residual)))
    r2 = 0.0 if total_variance == 0 else 1.0 - residual_variance / total_variance
    return {
        "mae": mae,
        "rmse": math.sqrt(mse),
        "mse": mse,
        "r2": r2,
    }


def compute_classification_metrics(
    actual_labels: list[str], predicted_labels: list[str]
) -> dict[str, object]:
    labels = ["low", "medium", "high"]
    confusion = {
        actual_label: {predicted_label: 0 for predicted_label in labels}
        for actual_label in labels
    }
    for actual_label, predicted_label in zip(actual_labels, predicted_labels):
        confusion[actual_label][predicted_label] += 1

    correct = sum(confusion[label][label] for label in labels)
    total = max(len(actual_labels), 1)
    accuracy = correct / total
    recall_by_label: dict[str, float] = {}
    precision_by_label: dict[str, float] = {}
    f1_by_label: dict[str, float] = {}
    for label in labels:
        tp = confusion[label][label]
        actual_total = sum(confusion[label].values())
        predicted_total = sum(confusion[row][label] for row in labels)
        recall = tp / actual_total if actual_total else 0.0
        precision = tp / predicted_total if predicted_total else 0.0
        f1 = 0.0 if recall + precision == 0 else (2 * recall * precision) / (recall + precision)
        recall_by_label[label] = recall
        precision_by_label[label] = precision
        f1_by_label[label] = f1
    balanced_accuracy = sum(recall_by_label.values()) / len(labels)
    macro_f1 = sum(f1_by_label.values()) / len(labels)
    return {
        "accuracy": accuracy,
        "labels": labels,
        "confusion": confusion,
        "recall_by_label": recall_by_label,
        "precision_by_label": precision_by_label,
        "f1_by_label": f1_by_label,
        "balanced_accuracy": balanced_accuracy,
        "macro_f1": macro_f1,
    }


def optimize_label_thresholds(
    actual_scores: np.ndarray,
    predicted_scores: np.ndarray,
    *,
    objective: str = "macro_f1",
    step: float = 0.01,
) -> dict[str, object]:
    actual_labels = [
        assign_risk_label_with_thresholds(float(value), DEFAULT_LOW_THRESHOLD, DEFAULT_HIGH_THRESHOLD)
        for value in actual_scores.tolist()
    ]
    best_result: dict[str, object] | None = None

    low_values = np.arange(0.2, 0.66, step)
    high_values = np.arange(0.45, 0.91, step)
    for low_threshold in low_values:
        for high_threshold in high_values:
            low_threshold = round(float(low_threshold), 2)
            high_threshold = round(float(high_threshold), 2)
            if low_threshold >= high_threshold:
                continue
            predicted_labels = [
                assign_risk_label_with_thresholds(float(value), low_threshold, high_threshold)
                for value in predicted_scores.tolist()
            ]
            metrics = compute_classification_metrics(actual_labels, predicted_labels)
            score = float(metrics.get(objective, 0.0))
            tie_break = float(metrics["accuracy"])
            candidate = {
                "objective": objective,
                "low_threshold": low_threshold,
                "high_threshold": high_threshold,
                "classification_metrics": metrics,
                "score": score,
                "tie_break_accuracy": tie_break,
            }
            if best_result is None:
                best_result = candidate
                continue
            best_score = float(best_result["score"])
            best_tie_break = float(best_result["tie_break_accuracy"])
            if score > best_score or (math.isclose(score, best_score) and tie_break > best_tie_break):
                best_result = candidate

    if best_result is None:
        raise ValueError("Unable to optimize label thresholds.")
    return best_result


def plot_loss_curve(history: list[dict[str, float]], output_path: Path) -> None:
    epochs = [int(item["epoch"]) for item in history]
    train_loss = [float(item["train_loss"]) for item in history]
    val_loss = [float(item["val_loss"]) for item in history]

    plt.figure(figsize=(8, 5))
    plt.plot(epochs, train_loss, label="Train loss", linewidth=2)
    plt.plot(epochs, val_loss, label="Validation loss", linewidth=2)
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.title("FPI LSTM loss curve")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def plot_prediction_scatter(actual: np.ndarray, predicted: np.ndarray, output_path: Path) -> None:
    plt.figure(figsize=(6, 6))
    plt.scatter(actual, predicted, alpha=0.6, edgecolors="none")
    min_axis = min(float(actual.min()), float(predicted.min()))
    max_axis = max(float(actual.max()), float(predicted.max()))
    plt.plot([min_axis, max_axis], [min_axis, max_axis], linestyle="--", linewidth=1.5)
    plt.xlabel("Actual FPI proxy")
    plt.ylabel("Predicted FPI proxy")
    plt.title("Validation predictions vs actual")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def plot_confusion_matrix(confusion: dict[str, dict[str, int]], output_path: Path) -> None:
    labels = ["low", "medium", "high"]
    matrix = np.array([[confusion[row][column] for column in labels] for row in labels], dtype=float)

    plt.figure(figsize=(6, 5))
    plt.imshow(matrix, cmap="Blues")
    plt.xticks(range(len(labels)), labels)
    plt.yticks(range(len(labels)), labels)
    plt.xlabel("Predicted label")
    plt.ylabel("Actual label")
    plt.title("Risk label confusion matrix")

    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            plt.text(column, row, int(matrix[row, column]), ha="center", va="center", color="black")

    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir) if args.output_dir else Path(args.model_dir) / "evaluation"
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics_path = Path(args.model_dir) / "metrics.json"
    model_path = Path(args.model_dir) / "model.pt"
    training_metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

    torch, nn, _, _, _ = require_torch()
    dataframe, features, targets, _ = load_dataset(Path(args.dataset))
    _, _, val_x, val_y = split_by_vessel(dataframe, features, targets)
    try:
        state_dict = torch.load(model_path, map_location="cpu", weights_only=True)
    except TypeError:  # pragma: no cover - older torch compatibility
        state_dict = torch.load(model_path, map_location="cpu")

    input_size = int(training_metrics.get("input_size", val_x.shape[2]))
    hidden_size = training_metrics.get("hidden_size")
    layers = training_metrics.get("layers")
    if hidden_size is None or layers is None:
        inferred_hidden_size, inferred_layers = infer_architecture_from_state_dict(state_dict)
        hidden_size = inferred_hidden_size
        layers = inferred_layers

    model = LSTMForecaster.build(
        nn,
        input_size=input_size,
        hidden_size=int(hidden_size),
        layers=int(layers),
    )
    model.load_state_dict(state_dict)
    model.eval()

    val_inputs = torch.tensor(val_x)
    with torch.no_grad():
        predictions = model(val_inputs).numpy()

    regression_metrics = compute_regression_metrics(val_y, predictions)
    actual_labels = [assign_risk_label(float(value)) for value in val_y.tolist()]
    predicted_labels = [assign_risk_label(float(value)) for value in predictions.tolist()]
    classification_metrics = compute_classification_metrics(actual_labels, predicted_labels)
    calibration = optimize_label_thresholds(val_y, predictions, objective="macro_f1")
    calibrated_low_threshold = float(calibration["low_threshold"])
    calibrated_high_threshold = float(calibration["high_threshold"])
    calibrated_labels = [
        assign_risk_label_with_thresholds(float(value), calibrated_low_threshold, calibrated_high_threshold)
        for value in predictions.tolist()
    ]

    predictions_frame = pd.DataFrame(
        {
            "actual_fpi_proxy": val_y,
            "predicted_fpi_proxy": predictions,
            "actual_risk_label": actual_labels,
            "predicted_risk_label": predicted_labels,
            "calibrated_predicted_risk_label": calibrated_labels,
        }
    )
    predictions_frame.to_csv(output_dir / "validation_predictions.csv", index=False)

    evaluation_summary = {
        "validation_rows": int(len(val_y)),
        "regression_metrics": regression_metrics,
        "classification_metrics": classification_metrics,
        "label_calibration": {
            "objective": str(calibration["objective"]),
            "low_threshold": calibrated_low_threshold,
            "high_threshold": calibrated_high_threshold,
            "classification_metrics": calibration["classification_metrics"],
        },
        "best_training_epoch": min(training_metrics["history"], key=lambda item: item["val_loss"]),
    }
    (output_dir / "evaluation.json").write_text(
        json.dumps(evaluation_summary, indent=2), encoding="utf-8"
    )

    plot_loss_curve(training_metrics["history"], output_dir / "loss_curve.png")
    plot_prediction_scatter(val_y, predictions, output_dir / "prediction_scatter.png")
    plot_confusion_matrix(
        classification_metrics["confusion"], output_dir / "label_confusion.png"
    )

    print(json.dumps(evaluation_summary, indent=2))
    print(f"Evaluation written to: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
