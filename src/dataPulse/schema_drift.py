from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "reports" / "batch_manifest.csv"
REPORT_DIR = PROJECT_ROOT / "reports" / "schema_drift"


def load_manifest() -> dict[str, dict]:
    """Load successfully inventoried batches, indexed by filename."""
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"Manifest not found: {MANIFEST_PATH}. "
            "Run the inventory module first."
        )

    with MANIFEST_PATH.open(
        "r", newline="", encoding="utf-8-sig"
    ) as file:
        records = list(csv.DictReader(file))

    return {
        record["file_name"]: record
        for record in records
        if record.get("status") == "SUCCESS"
    }


def parse_schema(schema_text: str) -> dict[str, str]:
    """Parse flattened Arrow fields while excluding serialized metadata."""
    # Pandas metadata describes serialization details, not ordinary columns.
    schema_text = schema_text.split(
        "-- schema metadata --", maxsplit=1
    )[0]

    columns: dict[str, str] = {}

    for item in schema_text.split("|"):
        item = item.strip()
        if not item or ":" not in item:
            continue

        name, data_type = item.split(":", maxsplit=1)
        name = name.strip()
        data_type = data_type.strip()
        if name and data_type:
            columns[name] = data_type

    if not columns:
        raise ValueError(
            "Could not parse schema fields. "
            "Check the schema format stored in the manifest."
        )

    return columns


def compare_schemas(
    baseline_name: str,
    baseline_schema: dict[str, str],
    candidate_name: str,
    candidate_schema: dict[str, str],
) -> dict:
    """Compare schemas and retain data types for added and removed fields.

    `added_columns` and `removed_columns` remain lists of names for backward
    compatibility with existing reports and tests. The corresponding detail
    fields provide types needed by downstream compatibility evaluation.
    """
    baseline_columns = set(baseline_schema)
    candidate_columns = set(candidate_schema)

    added = sorted(candidate_columns - baseline_columns)
    removed = sorted(baseline_columns - candidate_columns)
    common_columns = baseline_columns & candidate_columns

    added_details = [
        {"column": name, "candidate_type": candidate_schema[name]}
        for name in added
    ]
    removed_details = [
        {"column": name, "baseline_type": baseline_schema[name]}
        for name in removed
    ]
    type_changes = [
        {
            "column": name,
            "baseline_type": baseline_schema[name],
            "candidate_type": candidate_schema[name],
        }
        for name in sorted(common_columns)
        if baseline_schema[name] != candidate_schema[name]
    ]

    has_drift = bool(added or removed or type_changes)

    return {
        "baseline_batch": baseline_name,
        "candidate_batch": candidate_name,
        "compared_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_column_count": len(baseline_columns),
        "candidate_column_count": len(candidate_columns),
        "added_columns": added,
        "added_column_details": added_details,
        "removed_columns": removed,
        "removed_column_details": removed_details,
        "type_changes": type_changes,
        "schema_drift_detected": has_drift,
        "status": "DRIFT_DETECTED" if has_drift else "NO_DRIFT",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare schemas of two inventoried Parquet batches."
    )
    parser.add_argument(
        "--baseline",
        default="green_tripdata_2015-07.parquet",
        help="Baseline batch filename",
    )
    parser.add_argument(
        "--candidate",
        default="green_tripdata_2015-08.parquet",
        help="Batch to compare against the baseline",
    )
    args = parser.parse_args()

    if args.baseline == args.candidate:
        parser.error("Baseline and candidate must be different batches.")

    manifest = load_manifest()

    for filename in (args.baseline, args.candidate):
        if filename not in manifest:
            raise ValueError(
                f"Batch not found or not successfully inventoried: {filename}"
            )

    baseline_schema = parse_schema(manifest[args.baseline]["schema"])
    candidate_schema = parse_schema(manifest[args.candidate]["schema"])

    result = compare_schemas(
        args.baseline,
        baseline_schema,
        args.candidate,
        candidate_schema,
    )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_name = (
        f"{Path(args.baseline).stem}__vs__"
        f"{Path(args.candidate).stem}.json"
    )
    report_path = REPORT_DIR / report_name

    with report_path.open("w", encoding="utf-8") as file:
        json.dump(result, file, indent=2)

    print(f"Baseline: {result['baseline_batch']}")
    print(f"Candidate: {result['candidate_batch']}")
    print(f"Status: {result['status']}")
    print(f"Baseline columns: {result['baseline_column_count']}")
    print(f"Candidate columns: {result['candidate_column_count']}")
    print("Added columns:")
    if result["added_column_details"]:
        for column in result["added_column_details"]:
            print(f"  {column['column']}: {column['candidate_type']}")
    else:
        print("  None")

    print("Removed columns:")
    if result["removed_column_details"]:
        for column in result["removed_column_details"]:
            print(f"  {column['column']}: {column['baseline_type']}")
    else:
        print("  None")

    print(f"Type changes: {len(result['type_changes'])}")
    for change in result["type_changes"]:
        print(
            f"  {change['column']}: "
            f"{change['baseline_type']} -> "
            f"{change['candidate_type']}"
        )

    print(f"Report saved to: {report_path}")


if __name__ == "__main__":
    main()
