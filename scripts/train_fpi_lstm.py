from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scripts.fpi_forecast import sequence_feature_columns
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from fpi_forecast import sequence_feature_columns  # type: ignore


def require_torch():
    try:
        import torch
        from torch import nn
        from torch.utils.data import DataLoader, TensorDataset
    except ImportError as exc:  # pragma: no cover - depends on optional dependency
        raise RuntimeError(
            "PyTorch is required for LSTM training. Install it separately before running this script."
        ) from exc
    return torch, nn, DataLoader, TensorDataset


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
    return parser.parse_args()


def load_dataset(path: Path) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    dataframe = pd.read_csv(path)
    feature_columns = sequence_feature_columns(dataframe)
    if not feature_columns:
        raise ValueError("Sequence dataset does not contain flattened timestep features.")

    history_steps = len({column.split("_", 1)[0] for column in feature_columns})
    base_features = len(feature_columns) // history_steps
    features = dataframe[feature_columns].fillna(0.0).to_numpy(dtype=np.float32)
    targets = dataframe["target_fpi_proxy"].to_numpy(dtype=np.float32)
    reshaped = features.reshape(len(dataframe), history_steps, base_features)
    return dataframe, reshaped, targets


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


def main() -> None:
    args = parse_args()
    torch, nn, DataLoader, TensorDataset = require_torch()

    dataframe, features, targets = load_dataset(Path(args.dataset))
    train_x, train_y, val_x, val_y = split_by_vessel(dataframe, features, targets)

    class LSTMForecaster(nn.Module):
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

    model = LSTMForecaster(
        input_size=train_x.shape[2],
        hidden_size=args.hidden_size,
        layers=args.layers,
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
    loss_fn = nn.MSELoss()

    train_loader = DataLoader(
        TensorDataset(torch.tensor(train_x), torch.tensor(train_y)),
        batch_size=args.batch_size,
        shuffle=True,
    )
    val_inputs = torch.tensor(val_x)
    val_targets = torch.tensor(val_y)

    history: list[dict[str, float]] = []
    for epoch in range(1, args.epochs + 1):
        model.train()
        running_loss = 0.0
        for batch_inputs, batch_targets in train_loader:
            optimizer.zero_grad()
            predictions = model(batch_inputs)
            loss = loss_fn(predictions, batch_targets)
            loss.backward()
            optimizer.step()
            running_loss += float(loss.item()) * len(batch_inputs)

        model.eval()
        with torch.no_grad():
            val_predictions = model(val_inputs)
            val_loss = float(loss_fn(val_predictions, val_targets).item())

        epoch_record = {
            "epoch": epoch,
            "train_loss": running_loss / max(len(train_x), 1),
            "val_loss": val_loss,
        }
        history.append(epoch_record)
        print(epoch_record)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), output_dir / "model.pt")
    metrics = {
        "rows": int(len(dataframe)),
        "train_rows": int(len(train_x)),
        "val_rows": int(len(val_x)),
        "history": history,
    }
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Model written to: {(output_dir / 'model.pt').resolve()}")
    print(f"Metrics written to: {(output_dir / 'metrics.json').resolve()}")


if __name__ == "__main__":
    main()
