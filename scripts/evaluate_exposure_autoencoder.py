from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scripts.exposure_anomaly import (
        ANOMALY_FEATURE_COLUMNS,
        ScalingStats,
        classify_anomaly_levels,
        explain_anomaly_row,
        load_vessel_features,
        prepare_anomaly_features,
        transform_with_scaler,
    )
    from scripts.train_exposure_autoencoder import ExposureAutoencoder, require_torch
except ModuleNotFoundError:  # pragma: no cover
    from exposure_anomaly import (  # type: ignore
        ANOMALY_FEATURE_COLUMNS,
        ScalingStats,
        classify_anomaly_levels,
        explain_anomaly_row,
        load_vessel_features,
        prepare_anomaly_features,
        transform_with_scaler,
    )
    from train_exposure_autoencoder import ExposureAutoencoder, require_torch  # type: ignore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a trained vessel exposure anomaly autoencoder.")
    parser.add_argument("--dataset", required=True, help="Path to vessel_features CSV.")
    parser.add_argument("--model-dir", required=True, help="Directory containing model.pt and metrics.json.")
    parser.add_argument("--output-dir", help="Directory for anomaly outputs. Defaults to <model-dir>/evaluation.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir) if args.output_dir else Path(args.model_dir) / "evaluation"
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics = json.loads((Path(args.model_dir) / "metrics.json").read_text(encoding="utf-8"))
    scaling = metrics["scaling"]
    raw = load_vessel_features(Path(args.dataset))
    prepared = prepare_anomaly_features(raw)
    feature_matrix = transform_with_scaler(
        prepared,
        scaling=ScalingStats(means=scaling["means"], stds=scaling["stds"]),
        feature_columns=ANOMALY_FEATURE_COLUMNS,
    )

    torch, nn, _, _ = require_torch()
    try:
        state_dict = torch.load(Path(args.model_dir) / "model.pt", map_location="cpu", weights_only=True)
    except TypeError:  # pragma: no cover
        state_dict = torch.load(Path(args.model_dir) / "model.pt", map_location="cpu")
    model = ExposureAutoencoder.build(
        nn,
        input_size=len(ANOMALY_FEATURE_COLUMNS),
        latent_size=int(metrics["latent_size"]),
    )
    model.load_state_dict(state_dict)
    model.eval()

    input_tensor = torch.tensor(feature_matrix)
    with torch.no_grad():
        reconstructed_matrix = model(input_tensor).numpy()

    reconstruction_error = np.mean(np.square(feature_matrix - reconstructed_matrix), axis=1)
    anomaly_score = (reconstruction_error - reconstruction_error.min()) / max(
        reconstruction_error.max() - reconstruction_error.min(),
        1e-9,
    )
    anomaly_level = classify_anomaly_levels(pd.Series(anomaly_score))

    result = prepared.copy()
    result["anomaly_score"] = anomaly_score.round(6)
    result["anomaly_level"] = anomaly_level
    result["explanation_1"] = ""
    result["explanation_2"] = ""
    result["explanation_3"] = ""

    original_standardized = pd.DataFrame(feature_matrix, columns=ANOMALY_FEATURE_COLUMNS)
    for index, row in original_standardized.iterrows():
        explanations = explain_anomaly_row(
            row,
            reconstructed_matrix[index],
            feature_columns=ANOMALY_FEATURE_COLUMNS,
            top_k=3,
        )
        for slot, explanation in enumerate(explanations, start=1):
            result.at[index, f"explanation_{slot}"] = explanation

    result = result.sort_values(["anomaly_score", "mmsi"], ascending=[False, True]).reset_index(drop=True)
    result.to_csv(output_dir / "vessel_anomaly_scores.csv", index=False)

    summary = {
        "rows": int(len(result)),
        "feature_columns": ANOMALY_FEATURE_COLUMNS,
        "anomaly_level_counts": result["anomaly_level"].value_counts().to_dict(),
        "top_vessels": result[["mmsi", "anomaly_score", "anomaly_level"]].head(10).to_dict(orient="records"),
        "best_val_loss": float(metrics["best_val_loss"]),
    }
    (output_dir / "evaluation.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Evaluation written to: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
