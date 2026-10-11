
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from src.datapulse.schema_drift import (
    compare_schemas,
    parse_schema,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "reports" / "batch_manifest.csv"
HISTORY_DIR = PROJECT_ROOT / "reports" / "schema_history"


def load_batches(
    dataset_type: str,
    start_year: int,
    start_month: int,
) -> list[dict]:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"Manifest not found: {MANIFEST_PATH}"
        )

    with MANIFEST_PATH.open(
        "r", newline="", encoding="utf-8-sig"
    ) as file:
        records = list(csv.DictReader(file))

    batches = []

    for record in records:
        if record.get("status") != "SUCCESS":
            continue

        if record.get("dataset_type") != dataset_type:
            continue

        try:
            year = int(record["year"])
            month = int(record["month"])
        except (TypeError, ValueError):
            continue

        if not 1 <= month <= 12:
            continue

        if (year, month) < (start_year, start_month):
            continue

        record["_year"] = year
        record["_month"] = month
        batches.append(record)

    # A monthly dataset should have one file per period.
    # Fail explicitly if multiple files map to the same month.
    periods = [
        (batch["_year"], batch["_month"]) for batch in batches
    ]

    if len(periods) != len(set(periods)):
        raise ValueError(
            "Multiple eligible files exist for the same month. "
            "Define a selection policy before replaying history."
        )

    return sorted(
        batches,
        key=lambda batch: (batch["_year"], batch["_month"]),
    )


def main() -> None:
    batches = load_batches(
        dataset_type="green_tripdata",
        start_year=2015,
        start_month=7,
    )

    if len(batches) < 2:
        raise ValueError(
            "At least two eligible batches are required."
        )

    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    summary_rows = []

    for previous, current in zip(batches, batches[1:]):
        baseline_schema = parse_schema(previous["schema"])
        candidate_schema = parse_schema(current["schema"])

        result = compare_schemas(
            baseline_name=previous["file_name"],
            baseline_schema=baseline_schema,
            candidate_name=current["file_name"],
            candidate_schema=candidate_schema,
        )

        result["monitoring_run_at_utc"] = (
            datetime.now(timezone.utc).isoformat()
        )

        report_name = (
            f"{Path(previous['file_name']).stem}__vs__"
            f"{Path(current['file_name']).stem}.json"
        )

        report_path = HISTORY_DIR / report_name

        with report_path.open("w", encoding="utf-8") as file:
            json.dump(result, file, indent=2)

        summary_rows.append({
            "baseline_batch": result["baseline_batch"],
            "candidate_batch": result["candidate_batch"],
            "baseline_columns": result["baseline_column_count"],
            "candidate_columns": result["candidate_column_count"],
            "added_count": len(result["added_columns"]),
            "removed_count": len(result["removed_columns"]),
            "type_change_count": len(result["type_changes"]),
            "status": result["status"],
        })

        print(
            f"{result['baseline_batch']} -> "
            f"{result['candidate_batch']}: {result['status']}"
        )

        for change in result["type_changes"]:
            print(
                f"  TYPE CHANGE: {change['column']}: "
                f"{change['baseline_type']} -> "
                f"{change['candidate_type']}"
            )

        for column in result["added_columns"]:
            print(f"  ADDED COLUMN: {column}")

        for column in result["removed_columns"]:
            print(f"  REMOVED COLUMN: {column}")

    summary_path = HISTORY_DIR / "schema_history.csv"

    with summary_path.open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "baseline_batch",
                "candidate_batch",
                "baseline_columns",
                "candidate_columns",
                "added_count",
                "removed_count",
                "type_change_count",
                "status",
            ],
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    drift_count = sum(
        row["status"] == "DRIFT_DETECTED"
        for row in summary_rows
    )

    print("\nSchema monitoring complete")
    print(f"Batches compared: {len(summary_rows)}")
    print(f"Comparisons with drift: {drift_count}")
    print(f"Summary: {summary_path}")
    print(f"Detailed reports: {HISTORY_DIR}")


if __name__ == "__main__":
    main()
