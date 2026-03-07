from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

try:
    from scripts.exposure_anomaly import (
        ANOMALY_FEATURE_COLUMNS,
        fit_scaler,
        load_vessel_features,
        prepare_anomaly_features,
        split_train_validation,
        transform_with_scaler,
    )
except ModuleNotFoundError:  # pragma: no cover
    from exposure_anomaly import (  # type: ignore
        ANOMALY_FEATURE_COLUMNS,
        fit_scaler,
        load_vessel_features,
        prepare_anomaly_features,
        split_train_validation,
        transform_with_scaler,
    )


def require_torch():
    try:
        import torch
        from torch import nn
        from torch.utils.data import DataLoader, TensorDataset
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "PyTorch is required for anomaly autoencoder training. Install it separately before running this script."
        ) from exc
    return torch, nn, DataLoader, TensorDataset


class ExposureAutoencoder:
    @staticmethod
    def build(nn, input_size: int, latent_size: int):
        hidden_size = max(latent_size * 2, 8)

        class _Model(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.encoder = nn.Sequential(
                    nn.Linear(input_size, hidden_size),
                    nn.ReLU(),
                    nn.Linear(hidden_size, latent_size),
                    nn.ReLU(),
                )
                self.decoder = nn.Sequential(
                    nn.Linear(latent_size, hidden_size),
                    nn.ReLU(),
                    nn.Linear(hidden_size, input_size),
                )

            def forward(self, inputs):
                latent = self.encoder(inputs)
                return self.decoder(latent)

        return _Model()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a lightweight autoencoder for vessel exposure anomaly detection.")
    parser.add_argument("--dataset", required=True, help="Path to vessel_features CSV.")
    parser.add_argument("--output-dir", default="outputs/models/exposure_autoencoder", help="Directory for checkpoint and metrics.")
    parser.add_argument("--latent-size", type=int, default=4, help="Latent bottleneck size.")
    parser.add_argument("--epochs", type=int, default=40, help="Training epochs.")
    parser.add_argument("--batch-size", type=int, default=32, help="Training batch size.")
    parser.add_argument("--learning-rate", type=float, default=1e-3, help="Learning rate.")
    parser.add_argument("--validation-fraction", type=float, default=0.2, help="Validation fraction.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    torch, nn, DataLoader, TensorDataset = require_torch()
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    raw = load_vessel_features(Path(args.dataset))
    prepared = prepare_anomaly_features(raw)
    train_frame, validation_frame = split_train_validation(
        prepared,
        validation_fraction=args.validation_fraction,
        seed=args.seed,
    )
    scaling = fit_scaler(train_frame, ANOMALY_FEATURE_COLUMNS)
    train_matrix = transform_with_scaler(train_frame, scaling, ANOMALY_FEATURE_COLUMNS)
    validation_matrix = transform_with_scaler(validation_frame, scaling, ANOMALY_FEATURE_COLUMNS)

    model = ExposureAutoencoder.build(nn, input_size=train_matrix.shape[1], latent_size=args.latent_size)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
    loss_fn = nn.MSELoss()

    train_loader = DataLoader(
        TensorDataset(torch.tensor(train_matrix)),
        batch_size=args.batch_size,
        shuffle=True,
    )
    validation_tensor = torch.tensor(validation_matrix)

    history: list[dict[str, float]] = []
    best_val_loss = float("inf")
    best_state_dict = None
    best_epoch = None

    for epoch in range(1, args.epochs + 1):
        model.train()
        running_loss = 0.0
        for (batch_inputs,) in train_loader:
            optimizer.zero_grad()
            reconstructed = model(batch_inputs)
            loss = loss_fn(reconstructed, batch_inputs)
            loss.backward()
            optimizer.step()
            running_loss += float(loss.item()) * len(batch_inputs)

        model.eval()
        with torch.no_grad():
            validation_reconstructed = model(validation_tensor)
            val_loss = float(loss_fn(validation_reconstructed, validation_tensor).item())

        record = {
            "epoch": epoch,
            "train_loss": running_loss / max(len(train_matrix), 1),
            "val_loss": val_loss,
        }
        history.append(record)
        print(record)
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
        "dataset_path": str(Path(args.dataset).resolve()),
        "rows": int(len(prepared)),
        "train_rows": int(len(train_frame)),
        "validation_rows": int(len(validation_frame)),
        "feature_columns": ANOMALY_FEATURE_COLUMNS,
        "latent_size": int(args.latent_size),
        "epochs": int(args.epochs),
        "batch_size": int(args.batch_size),
        "learning_rate": float(args.learning_rate),
        "validation_fraction": float(args.validation_fraction),
        "seed": int(args.seed),
        "best_epoch": int(best_epoch),
        "best_val_loss": float(best_val_loss),
        "scaling": {
            "means": scaling.means,
            "stds": scaling.stds,
        },
        "history": history,
    }
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Model written to: {(output_dir / 'model.pt').resolve()}")
    print(f"Metrics written to: {(output_dir / 'metrics.json').resolve()}")


if __name__ == "__main__":
    main()
