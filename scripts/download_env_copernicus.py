import argparse
import json
import os
from pathlib import Path
from typing import Any

import copernicusmarine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download an environment subset from Copernicus Marine."
    )
    parser.add_argument("--job", required=True, help="Path to Copernicus job JSON.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the request without downloading files.",
    )
    return parser.parse_args()


def load_job(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def get_credentials() -> tuple[str | None, str | None]:
    username = os.getenv("COPERNICUSMARINE_SERVICE_USERNAME")
    password = os.getenv("COPERNICUSMARINE_SERVICE_PASSWORD")
    return username, password


def main() -> None:
    args = parse_args()
    job = load_job(Path(args.job))
    username, password = get_credentials()

    output_directory = Path(job["output_directory"])
    output_directory.mkdir(parents=True, exist_ok=True)

    response = copernicusmarine.subset(
        dataset_id=job["dataset_id"],
        dataset_version=job.get("dataset_version"),
        dataset_part=job.get("dataset_part"),
        username=username,
        password=password,
        variables=job.get("variables"),
        minimum_longitude=job["bbox"]["west"],
        maximum_longitude=job["bbox"]["east"],
        minimum_latitude=job["bbox"]["south"],
        maximum_latitude=job["bbox"]["north"],
        minimum_depth=job.get("minimum_depth"),
        maximum_depth=job.get("maximum_depth"),
        start_datetime=job["start_time"],
        end_datetime=job["end_time"],
        output_directory=output_directory,
        output_filename=job.get("output_filename"),
        file_format=job.get("file_format", "netcdf"),
        service=job.get("service"),
        coordinates_selection_method=job.get("coordinates_selection_method", "inside"),
        overwrite=job.get("overwrite", False),
        skip_existing=job.get("skip_existing", True),
        dry_run=args.dry_run,
        disable_progress_bar=job.get("disable_progress_bar", False),
    )

    print(f"Copernicus request completed for dataset: {job['dataset_id']}")
    print(f"Output directory: {output_directory.resolve()}")
    print(f"Response: {response}")


if __name__ == "__main__":
    main()
