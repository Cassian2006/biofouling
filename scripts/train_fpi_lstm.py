from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scripts.fpi_forecast import assign_risk_label, sequence_feature_columns
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from fpi_forecast import assign_risk_label, sequence_feature_columns  # type: ignore


def require_torch():
    try:
        import torch
        from torch import nn
        from torch.utils.data import DataLoader, TensorDataset, WeightedRandomSampler
    except ImportError as exc:  # pragma: no cover - depends on optional dependency
        raise RuntimeError(
            "PyTorch is required for LSTM training. Install it separately before running this script."
        ) from exc
    return torch, nn, DataLoader, TensorDataset, WeightedRandomSampler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a lightweight LSTM forecaster for FPI.")
    parser.add_argument("--dataset", required=True, help="Path to flattened sequence dataset CSV.")
    parser.add_argument(
        "--output-dir",
        default="outputs/models/fpi_lstm",
        help="Directory for model checkpoint and metrics.",
    )
    parser.add_argument("--hidden-size", type=int, default=32, help="LSTM hidden size.")
    parser.add_argument("--layers", type=int, default=1, help="Number of LSTM layers.")
    parser.add_argument("--epochs", type=int, default=12, help="Training epochs.")
    parser.add_argument("--batch-size", type=int, default=32, help="Training batch size.")
    parser.add_argument("--learning-rate", type=float, default=1e-3, help="Learning rate.")
    parser.add_argument(
        "--sampling-strategy",
        choices=["uniform", "balanced"],
        default="balanced",
        help="How to sample training rows across risk labels.",
    )
    parser.add_argument(
        "--loss-weighting",
        choices=["uniform", "balanced"],
        default="balanced",
        help="How to weight regression loss across risk labels.",
    )
    parser.add_argument(
        "--sampling-balance-power",
        type=float,
        default=1.0,
        help="Power applied to balanced sampling weights. Lower than 1.0 makes balancing milder.",
    )
    parser.add_argument(
        "--loss-balance-power",
        type=float,
        default=1.0,
        help="Power applied to balanced loss weights. Lower than 1.0 makes weighting milder.",
    )
    return parser.parse_args()


class LSTMForecaster:
    @staticmethod
    def build(nn, input_size: int, hidden_size: int, layers: int):
        class _Model(nn.Module):
            def __init__(self, input_size: int, hidden_size: int, layers: int) -> None:
                super().__init__()
                self.lstm = nn.LSTM(
                    input_size=input_size,
                    hidden_size=hidden_size,
                    num_layers=layers,
                    batch_first=True,
                )
                self.head = nn.Linear(hidden_size, 1)

            def forward(self, inputs):
                output, _ = self.lstm(inputs)
                return self.head(output[:, -1, :]).squeeze(-1)

        return _Model(input_size=input_size, hidden_size=hidden_size, layers=layers)


def load_dataset(path: Path) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, list[str]]:
    dataframe = pd.read_csv(path)
    feature_columns = sequence_feature_columns(dataframe)
    if not feature_columns:
        raise ValueError("Sequence dataset does not contain flattened timestep features.")

    history_steps = len({column.split("_", 1)[0] for column in feature_columns})
    base_features = len(feature_columns) // history_steps
    features = dataframe[feature_columns].fillna(0.0).to_numpy(dtype=np.float32)
    targets = dataframe["target_fpi_proxy"].to_numpy(dtype=np.float32)
    reshaped = features.reshape(len(dataframe), history_steps, base_features)
    return dataframe, reshaped, targets, feature_columns


def split_by_vessel(
    dataframe: pd.DataFrame, features: np.ndarray, targets: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    vessel_ids = sorted(dataframe["mmsi"].astype(str).unique())
    if len(vessel_ids) < 2:
        return features, targets, features, targets

    split_index = max(1, int(len(vessel_ids) * 0.8))
    train_ids = set(vessel_ids[:split_index])
    train_mask = dataframe["mmsi"].astype(str).isin(train_ids).to_numpy()
    val_mask = ~train_mask
    if not val_mask.any():
        val_mask = train_mask.copy()
    return features[train_mask], targets[train_mask], features[val_mask], targets[val_mask]


def risk_labels_from_targets(targets: np.ndarray) -> list[str]:
    return [assign_risk_label(float(value)) for value in targets.tolist()]


def compute_label_weights(
    labels: list[str], mode: str = "balanced", power: float = 1.0
) -> dict[str, float]:
    unique_labels = sorted(set(labels))
    if mode == "uniform":
        return {label: 1.0 for label in unique_labels}

    counts = pd.Series(labels).value_counts()
    total = float(sum(counts.values))
    class_count = float(len(counts))
    weights = {
        label: (total / (class_count * float(counts[label]))) ** power for label in counts.index
    }
    return {label: float(weights.get(label, 1.0)) for label in unique_labels}


def sample_weight_array(labels: list[str], weight_map: dict[str, float]) -> np.ndarray:
    return np.array([weight_map.get(label, 1.0) for label in labels], dtype=np.float32)


def main() -> None:
    args = parse_args()
    torch, nn, DataLoader, TensorDataset, WeightedRandomSampler = require_torch()

    dataframe, features, targets, feature_columns = load_dataset(Path(args.dataset))
    train_x, train_y, val_x, val_y = split_by_vessel(dataframe, features, targets)
    train_labels = risk_labels_from_targets(train_y)
    train_weight_map = compute_label_weights(
        train_labels, mode=args.sampling_strategy, power=args.sampling_balance_power
    )
    loss_weight_map = compute_label_weights(
        train_labels, mode=args.loss_weighting, power=args.loss_balance_power
    )
    train_sample_weights = sample_weight_array(train_labels, train_weight_map)
    train_loss_weights = torch.tensor(
        sample_weight_array(train_labels, loss_weight_map), dtype=torch.float32
    )
    model = LSTMForecaster.build(
        nn,
        input_size=train_x.shape[2],
        hidden_size=args.hidden_size,
        layers=args.layers,
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)

    train_dataset = TensorDataset(
        torch.tensor(train_x),
        torch.tensor(train_y),
        train_loss_weights,
    )
    if args.sampling_strategy == "balanced":
        sampler = WeightedRandomSampler(
            weights=torch.tensor(train_sample_weights, dtype=torch.float32),
            num_samples=len(train_sample_weights),
            replacement=True,
        )
        train_loader = DataLoader(train_dataset, batch_size=args.batch_size, sampler=sampler)
    else:
        train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)

    val_inputs = torch.tensor(val_x)
    val_targets = torch.tensor(val_y)

    history: list[dict[str, float]] = []
    best_val_loss = float("inf")
    best_state_dict = None
    best_epoch = None
    for epoch in range(1, args.epochs + 1):
        model.train()
        running_loss = 0.0
        for batch_inputs, batch_targets, batch_weights in train_loader:
            optimizer.zero_grad()
            predictions = model(batch_inputs)
            per_item_loss = torch.square(predictions - batch_targets)
            if args.loss_weighting == "balanced":
                loss = (per_item_loss * batch_weights).mean()
            else:
                loss = per_item_loss.mean()
            loss.backward()
            optimizer.step()
            running_loss += float(loss.item()) * len(batch_inputs)

        model.eval()
        with torch.no_grad():
            val_predictions = model(val_inputs)
            val_loss = float(torch.mean(torch.square(val_predictions - val_targets)).item())

        epoch_record = {
            "epoch": epoch,
            "train_loss": running_loss / max(len(train_x), 1),
            "val_loss": val_loss,
        }
        history.append(epoch_record)
        print(epoch_record)
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch
            best_state_dict = {
                key: value.detach().cpu().clone() for key, value in model.state_dict().items()
            }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if best_state_dict is None:
        best_state_dict = {key: value.detach().cpu() for key, value in model.state_dict().items()}
        best_epoch = args.epochs
        best_val_loss = history[-1]["val_loss"]
    torch.save(best_state_dict, output_dir / "model.pt")
    metrics = {
        "rows": int(len(dataframe)),
        "train_rows": int(len(train_x)),
        "val_rows": int(len(val_x)),
        "dataset_path": str(Path(args.dataset).resolve()),
        "history_steps": int(train_x.shape[1]),
        "input_size": int(train_x.shape[2]),
        "feature_columns": feature_columns,
        "hidden_size": int(args.hidden_size),
        "layers": int(args.layers),
        "label_set": sorted(set(risk_labels_from_targets(targets))),
        "sampling_strategy": args.sampling_strategy,
        "loss_weighting": args.loss_weighting,
        "sampling_balance_power": float(args.sampling_balance_power),
        "loss_balance_power": float(args.loss_balance_power),
        "label_weights": loss_weight_map,
        "best_epoch": int(best_epoch),
        "best_val_loss": float(best_val_loss),
        "history": history,
    }
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Model written to: {(output_dir / 'model.pt').resolve()}")
    print(f"Metrics written to: {(output_dir / 'metrics.json').resolve()}")


if __name__ == "__main__":
    main()
