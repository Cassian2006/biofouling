import pandas as pd

from scripts.exposure_anomaly import (
    ANOMALY_FEATURE_COLUMNS,
    HIGHLY_ABNORMAL_SCORE_THRESHOLD,
    MIN_OBSERVATION_HOURS,
    MIN_OBSERVATION_PINGS,
    SUSPICIOUS_SCORE_THRESHOLD,
    classify_anomaly_levels,
    explain_anomaly_row,
    fit_scaler,
    prepare_anomaly_features,
    split_train_validation,
    transform_with_scaler,
)


def sample_feature_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "mmsi": ["111", "222", "333", "444"],
            "ping_count": [120, 300, 90, 1000],
            "low_speed_ratio": [0.1, 0.8, 0.3, 0.95],
            "mean_sst": [27.3, 27.8, 27.5, 28.1],
            "mean_chlorophyll_a": [0.2, 0.5, 0.3, 0.7],
            "mean_salinity": [31.1, 31.3, 31.0, 31.8],
            "mean_current_u": [-0.2, -0.4, -0.1, -0.5],
            "mean_current_v": [0.1, -0.1, 0.0, 0.2],
            "track_duration_hours": [12, 48, 20, 120],
            "fpi_proxy": [0.3, 0.7, 0.45, 0.95],
            "ecp_proxy": [0.3, 0.75, 0.45, 1.1],
        }
    )


def test_prepare_anomaly_features_adds_current_speed() -> None:
    prepared = prepare_anomaly_features(sample_feature_frame())

    assert prepared.columns.tolist() == ["mmsi"] + ANOMALY_FEATURE_COLUMNS
    assert round(float(prepared.loc[0, "current_speed"]), 6) == round(((-0.2) ** 2 + 0.1**2) ** 0.5, 6)


def test_transform_with_scaler_returns_standardized_matrix() -> None:
    prepared = prepare_anomaly_features(sample_feature_frame())
    scaling = fit_scaler(prepared, ANOMALY_FEATURE_COLUMNS)
    matrix = transform_with_scaler(prepared, scaling, ANOMALY_FEATURE_COLUMNS)

    assert matrix.shape == (4, len(ANOMALY_FEATURE_COLUMNS))
    assert round(float(matrix.mean()), 6) == 0.0


def test_classify_anomaly_levels_and_explanations() -> None:
    scores = pd.Series([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    frame = pd.DataFrame(
        {
            "ping_count": [MIN_OBSERVATION_PINGS - 1] + [MIN_OBSERVATION_PINGS] * 9,
            "track_duration_hours": [MIN_OBSERVATION_HOURS - 1] + [MIN_OBSERVATION_HOURS] * 9,
        }
    )
    labels = classify_anomaly_levels(scores, frame)

    assert labels.iloc[0] == "observation_insufficient"
    assert labels.iloc[1] == "suspicious"
    assert labels.iloc[2] == "suspicious"
    assert labels.iloc[3] == "highly_abnormal"
    assert labels.iloc[-1] == "highly_abnormal"
    assert SUSPICIOUS_SCORE_THRESHOLD == 0.12
    assert HIGHLY_ABNORMAL_SCORE_THRESHOLD == 0.35

    standardized = pd.Series(
        {
            "ping_count": 2.0,
            "low_speed_ratio": 1.5,
            "mean_sst": 0.2,
            "mean_chlorophyll_a": 0.1,
            "mean_salinity": -0.4,
            "current_speed": 0.05,
            "track_duration_hours": 1.2,
            "fpi_proxy": 0.8,
            "ecp_proxy": 0.9,
        }
    )
    reconstructed = [0.5, 0.2, 0.1, 0.0, -0.1, 0.0, 0.3, 0.1, 0.2]
    explanations = explain_anomaly_row(standardized, reconstructed, ANOMALY_FEATURE_COLUMNS, top_k=2)

    assert len(explanations) == 2
    assert explanations[0].startswith("ping_count")
    assert "model reconstruction" in explanations[0]


def test_split_train_validation_keeps_rows() -> None:
    prepared = prepare_anomaly_features(sample_feature_frame())
    train, validation = split_train_validation(prepared, validation_fraction=0.25, seed=7)

    assert len(train) + len(validation) == len(prepared)
    assert not train.empty
    assert not validation.empty
