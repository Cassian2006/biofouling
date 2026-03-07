import argparse
import csv
import json
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import requests


DEFAULT_TOKEN_URL = "https://svc.data.myvessel.cn/ada/oauth/token"
DEFAULT_REGION_EVENTS_URL = (
    "https://svc.data.myvessel.cn/sdc-tob/v1/mkt/vessels/events/cross/region/his/page"
)
DEFAULT_TRACKS_URL = "https://svc.data.myvessel.cn/sdc-tob/v1/mkt/ais/track"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
}


@dataclass
class JobConfig:
    mode: str
    start_time: datetime
    end_time: datetime
    slice_hours: int
    output_dir: Path
    state_file: Path
    region: dict[str, Any] | None = None
    mmsi_csv: Path | None = None
    region_events_url: str = DEFAULT_REGION_EVENTS_URL
    tracks_url: str = DEFAULT_TRACKS_URL
    token_url: str = DEFAULT_TOKEN_URL
    retry_delay_seconds: int = 30


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sliced AIS downloader with resumable state and persistent retries."
    )
    parser.add_argument("--job", required=True, help="Path to download job JSON.")
    return parser.parse_args()


def parse_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).astimezone(UTC)


def load_job(path: Path) -> JobConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    output_dir = Path(payload["output_dir"])
    state_file = Path(payload.get("state_file", output_dir / "download_state.json"))

    return JobConfig(
        mode=payload["mode"],
        start_time=parse_datetime(payload["start_time"]),
        end_time=parse_datetime(payload["end_time"]),
        slice_hours=int(payload.get("slice_hours", 6)),
        output_dir=output_dir,
        state_file=state_file,
        region=payload.get("region"),
        mmsi_csv=Path(payload["mmsi_csv"]) if payload.get("mmsi_csv") else None,
        region_events_url=payload.get("region_events_url", DEFAULT_REGION_EVENTS_URL),
        tracks_url=payload.get("tracks_url", DEFAULT_TRACKS_URL),
        token_url=payload.get("token_url", DEFAULT_TOKEN_URL),
        retry_delay_seconds=int(payload.get("retry_delay_seconds", 30)),
    )


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"completed": [], "failed": {}, "last_token_time": None}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_client_credentials() -> tuple[str, str]:
    client_id = os.getenv("MYVESSEL_CLIENT_ID")
    client_secret = os.getenv("MYVESSEL_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise SystemExit(
            "Missing MYVESSEL_CLIENT_ID or MYVESSEL_CLIENT_SECRET environment variables."
        )
    return client_id, client_secret


def request_token(token_url: str) -> str:
    client_id, client_secret = get_client_credentials()
    response = requests.post(
        token_url,
        params={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise RuntimeError("Token response did not contain access_token.")
    return token


def headers_with_token(token: str) -> dict[str, str]:
    headers = dict(DEFAULT_HEADERS)
    headers["Authorization"] = f"Bearer {token}"
    return headers


def iter_time_slices(start: datetime, end: datetime, slice_hours: int) -> list[tuple[datetime, datetime]]:
    slices: list[tuple[datetime, datetime]] = []
    cursor = start
    while cursor < end:
        next_cursor = min(cursor + timedelta(hours=slice_hours), end)
        slices.append((cursor, next_cursor))
        cursor = next_cursor
    return slices


def read_mmsi_list(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.reader(file)
        rows = [row for row in reader if row]

    values = [row[0].strip() for row in rows if row[0].strip()]
    if values and values[0].lower() == "mmsi":
        values = values[1:]
    return list(dict.fromkeys(values))


def safe_slice_label(start: datetime, end: datetime) -> str:
    return f"{start:%Y%m%dT%H%M%SZ}_{end:%Y%m%dT%H%M%SZ}"


def safe_key_to_filename(key: str) -> str:
    return key.replace("::", "__")


def post_json(url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    return response.json()


def should_refresh_token(exc: Exception) -> bool:
    if not isinstance(exc, requests.HTTPError):
        return False
    response = exc.response
    if response is None:
        return False
    return response.status_code in {401, 403}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def mark_completed(state: dict[str, Any], key: str) -> None:
    if key not in state["completed"]:
        state["completed"].append(key)
    state["failed"].pop(key, None)


def mark_failed(state: dict[str, Any], key: str, error_text: str) -> None:
    state["failed"][key] = {
        "error": error_text,
        "updated_at": datetime.now(UTC).isoformat(),
    }


def run_region_events_job(config: JobConfig, token: str, state: dict[str, Any]) -> None:
    if not config.region:
        raise SystemExit("Region job requires `region` in the job file.")

    headers = headers_with_token(token)
    for slice_start, slice_end in iter_time_slices(
        config.start_time, config.end_time, config.slice_hours
    ):
        key = f"region::{safe_slice_label(slice_start, slice_end)}"
        if key in state["completed"]:
            print(f"[skip] {key}")
            continue

        while True:
            try:
                page_num = 1
                pages: list[dict[str, Any]] = []
                total_pages = 1

                while page_num <= total_pages:
                    payload = {
                        "dwt": 0,
                        "teu": 0,
                        "grt": 0,
                        "vesselSubType": [],
                        "teu2": 40000,
                        "grt2": 40000,
                        "dwt2": 400000,
                        "startTime": slice_start.strftime("%Y-%m-%d %H:%M:%S"),
                        "endTime": slice_end.strftime("%Y-%m-%d %H:%M:%S"),
                        "page": {"pageSize": 100, "pageNum": page_num},
                        "region": config.region,
                    }
                    response_payload = post_json(config.region_events_url, headers, payload)
                    pages.append(response_payload)

                    page_info = response_payload.get("data", {}).get("page", {})
                    total_pages = max(page_info.get("pages", 1), 1)
                    page_num += 1

                combined_payload = {
                    "slice_start": slice_start.isoformat(),
                    "slice_end": slice_end.isoformat(),
                    "page_count": len(pages),
                    "pages": pages,
                }
                output_path = (
                    config.output_dir
                    / "region_events"
                    / f"{safe_key_to_filename(key)}.json"
                )
                write_json(output_path, combined_payload)
                mark_completed(state, key)
                save_state(config.state_file, state)
                print(f"[done] {key} -> {output_path}")
                break
            except Exception as exc:
                error_text = str(exc)
                mark_failed(state, key, error_text)
                save_state(config.state_file, state)
                print(f"[retry] {key} failed: {error_text}")
                if should_refresh_token(exc):
                    token = request_token(config.token_url)
                    headers = headers_with_token(token)
                    state["last_token_time"] = datetime.now(UTC).isoformat()
                    save_state(config.state_file, state)
                time.sleep(max(5, config.retry_delay_seconds))


def run_tracks_job(config: JobConfig, token: str, state: dict[str, Any]) -> None:
    if not config.mmsi_csv:
        raise SystemExit("Tracks job requires `mmsi_csv` in the job file.")

    headers = headers_with_token(token)
    mmsis = read_mmsi_list(config.mmsi_csv)
    for mmsi in mmsis:
        for slice_start, slice_end in iter_time_slices(
            config.start_time, config.end_time, config.slice_hours
        ):
            key = f"track::{mmsi}::{safe_slice_label(slice_start, slice_end)}"
            if key in state["completed"]:
                print(f"[skip] {key}")
                continue

            payload = {
                "mmsi": mmsi,
                "startTime": slice_start.strftime("%Y-%m-%d %H:%M:%S"),
                "endTime": slice_end.strftime("%Y-%m-%d %H:%M:%S"),
            }

            while True:
                try:
                    response_payload = post_json(config.tracks_url, headers, payload)
                    output_path = config.output_dir / "tracks" / mmsi / (
                        f"{safe_slice_label(slice_start, slice_end)}.json"
                    )
                    write_json(output_path, response_payload)
                    mark_completed(state, key)
                    save_state(config.state_file, state)
                    print(f"[done] {key} -> {output_path}")
                    break
                except Exception as exc:
                    error_text = str(exc)
                    mark_failed(state, key, error_text)
                    save_state(config.state_file, state)
                    print(f"[retry] {key} failed: {error_text}")
                    if should_refresh_token(exc):
                        token = request_token(config.token_url)
                        headers = headers_with_token(token)
                        state["last_token_time"] = datetime.now(UTC).isoformat()
                        save_state(config.state_file, state)
                    time.sleep(max(5, config.retry_delay_seconds))


def main() -> None:
    args = parse_args()
    config = load_job(Path(args.job))
    config.output_dir.mkdir(parents=True, exist_ok=True)

    state = load_state(config.state_file)
    token = request_token(config.token_url)
    state["last_token_time"] = datetime.now(UTC).isoformat()
    save_state(config.state_file, state)

    if config.mode == "region_events":
        run_region_events_job(config, token, state)
        return
    if config.mode == "tracks":
        run_tracks_job(config, token, state)
        return

    raise SystemExit(f"Unsupported mode: {config.mode}")


if __name__ == "__main__":
    main()
