from pathlib import Path

import pandas as pd
import xarray as xr

from scripts.process_env import clean_env, load_env_netcdf


def write_dataset(path: Path, variable_payload: dict[str, list[float]]) -> None:
    dataset = xr.Dataset(
        {
            name: (
                ("time", "depth", "latitude", "longitude"),
                [[[[value[0]]]]],
            )
            for name, value in variable_payload.items()
        },
        coords={
            "time": ["2026-01-15T00:00:00Z"],
            "depth": [0.5],
            "latitude": [1.2],
            "longitude": [103.5],
        },
    )
    dataset.to_netcdf(path)


def test_load_env_netcdf_merges_all_supported_environment_variables(tmp_path: Path) -> None:
    thetao_path = tmp_path / "thetao.nc"
    chl_path = tmp_path / "chl.nc"
    salinity_path = tmp_path / "salinity.nc"
    currents_path = tmp_path / "currents.nc"

    write_dataset(thetao_path, {"thetao": [28.4]})
    write_dataset(chl_path, {"chl": [0.18]})
    write_dataset(salinity_path, {"so": [33.1]})
    write_dataset(currents_path, {"uo": [0.24], "vo": [-0.11]})

    dataframe = load_env_netcdf(thetao_path, chl_path, salinity_path, currents_path)

    assert set(
        [
            "timestamp",
            "latitude",
            "longitude",
            "sst",
            "chlorophyll_a",
            "salinity",
            "current_u",
            "current_v",
        ]
    ).issubset(dataframe.columns)
    assert dataframe.loc[0, "sst"] == 28.4
    assert dataframe.loc[0, "chlorophyll_a"] == 0.18
    assert dataframe.loc[0, "salinity"] == 33.1
    assert dataframe.loc[0, "current_u"] == 0.24
    assert dataframe.loc[0, "current_v"] == -0.11


def test_clean_env_preserves_optional_columns_and_study_area() -> None:
    dataframe = pd.DataFrame(
        [
            {
                "timestamp": "2026-01-15T00:00:00Z",
                "latitude": 1.2,
                "longitude": 103.5,
                "sst": 28.4,
                "chlorophyll_a": 0.18,
                "salinity": 33.1,
                "current_u": 0.24,
                "current_v": -0.11,
            }
        ]
    )

    cleaned = clean_env(dataframe)

    assert len(cleaned) == 1
    assert cleaned.loc[0, "salinity"] == 33.1
    assert cleaned.loc[0, "current_u"] == 0.24
    assert cleaned.loc[0, "current_v"] == -0.11
    assert cleaned.loc[0, "study_area"] == "singapore_strait_v1"
