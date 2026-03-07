from pathlib import Path

import pandas as pd

from scripts.build_vessel_catalog import build_ais_derived_catalog, load_static_profiles, merge_static_profiles
from scripts.summarize_validation_events import load_validation_events, summarize_validation_events


def test_build_ais_derived_catalog_creates_profile_from_ais_fields() -> None:
    ais = pd.DataFrame(
        [
            {
                "mmsi": "123456789",
                "timestamp": "2026-01-15T00:00:00Z",
                "draught": 8.5,
                "destination": "SG SIN",
                "nav_status": "0",
            },
            {
                "mmsi": "123456789",
                "timestamp": "2026-01-15T06:00:00Z",
                "draught": 8.9,
                "destination": "SG SIN",
                "nav_status": "0",
            },
        ]
    )

    catalog = build_ais_derived_catalog(ais)

    assert len(catalog) == 1
    assert catalog.loc[0, "mmsi"] == "123456789"
    assert catalog.loc[0, "observed_draught_m"] == 8.7
    assert catalog.loc[0, "dominant_destination"] == "SG SIN"
    assert catalog.loc[0, "profile_source"] == "ais_derived"


def test_merge_static_profiles_overrides_profile_source_when_external_data_exists(tmp_path: Path) -> None:
    derived = pd.DataFrame(
        [
            {
                "mmsi": "123456789",
                "first_seen": "2026-01-15T00:00:00+00:00",
                "last_seen": "2026-01-15T06:00:00+00:00",
                "observed_draught_m": 8.7,
                "max_observed_draught_m": 8.9,
                "dominant_destination": "SG SIN",
                "dominant_nav_status": "0",
                "profile_source": "ais_derived",
                "static_source": None,
            }
        ]
    )
    static_path = tmp_path / "vessel_static_profiles.csv"
    static_path.write_text(
        "mmsi,vessel_name,imo,ship_type,flag,length_m,beam_m,source\n"
        "123456789,DEMO VESSEL,9876543,Container,SG,210,32,manual_catalog\n",
        encoding="utf-8",
    )

    static_profiles = load_static_profiles(static_path)
    merged = merge_static_profiles(derived, static_profiles)

    assert merged.loc[0, "vessel_name"] == "DEMO VESSEL"
    assert merged.loc[0, "profile_source"] == "external_merge"
    assert merged.loc[0, "static_source"] == "manual_catalog"


def test_summarize_validation_events_rolls_up_latest_event_and_sources(tmp_path: Path) -> None:
    validation_path = tmp_path / "validation_events.csv"
    validation_path.write_text(
        "validation_id,mmsi,event_type,event_start,event_end,port_name,source,notes\n"
        "1,123456789,arrival,2026-01-15T00:00:00Z,2026-01-15T01:00:00Z,Singapore Port,mpa,checked\n"
        "2,123456789,departure,2026-01-16T00:00:00Z,2026-01-16T01:00:00Z,Singapore Port,manual,\n",
        encoding="utf-8",
    )

    events = load_validation_events(validation_path)
    summary = summarize_validation_events(events)

    assert len(summary) == 1
    assert summary.loc[0, "event_count"] == 2
    assert summary.loc[0, "source_count"] == 2
    assert summary.loc[0, "latest_event_type"] == "departure"
    assert summary.loc[0, "latest_port_name"] == "Singapore Port"
