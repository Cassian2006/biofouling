from scripts.train_fpi_lstm import compute_label_weights, sample_weight_array


def test_compute_label_weights_balances_minority_class() -> None:
    labels = ["high"] * 8 + ["medium"] * 2 + ["low"] * 2

    weights = compute_label_weights(labels, mode="balanced")

    assert round(weights["high"], 6) == 0.5
    assert round(weights["medium"], 6) == 2.0
    assert round(weights["low"], 6) == 2.0


def test_sample_weight_array_maps_weights_in_label_order() -> None:
    labels = ["high", "medium", "low", "high"]
    weight_map = {"high": 0.5, "medium": 2.0, "low": 2.0}

    weights = sample_weight_array(labels, weight_map)

    assert weights.tolist() == [0.5, 2.0, 2.0, 0.5]
