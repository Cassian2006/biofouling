import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check whether required datasets declared in a manifest are ready."
    )
    parser.add_argument(
        "--manifest",
        default="data/contracts/dataset_manifest.template.json",
        help="Path to dataset manifest JSON.",
    )
    return parser.parse_args()


def status_text(path: Path) -> str:
    return "READY" if path.exists() else "MISSING"


def main() -> None:
    args = parse_args()
    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    datasets = manifest.get("datasets", {})
    outputs = manifest.get("pipeline_outputs", {})

    print(f"Manifest: {manifest_path.resolve()}")
    print("")
    print("Dataset readiness")
    print("-" * 72)
    for name, config in datasets.items():
        dataset_path = Path(config["path"])
        print(f"{name:<16} {status_text(dataset_path):<8} {dataset_path}")

    print("")
    print("Planned outputs")
    print("-" * 72)
    for name, output_path in outputs.items():
        path = Path(output_path)
        print(f"{name:<16} {status_text(path):<8} {path}")


if __name__ == "__main__":
    main()

