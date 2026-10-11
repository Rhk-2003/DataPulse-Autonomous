
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "reports"
MANIFEST_PATH = REPORT_DIR / "batch_manifest.csv"
QUALITY_REPORT_DIR = REPORT_DIR / "quality"

REQUIRED_COLUMNS = [
    "lpep_pickup_datetime",
    "lpep_dropoff_datetime",
    "trip_distance",
    "fare_amount",
    "total_amount",
]


def profile_batch(file_path: Path, expected_rows: int) -> dict:
    """Profile a single batch using selected columns."""
    parquet_file = pq.ParquetFile(file_path)
    schema_names = parquet_file.schema_arrow.names

    selected_columns = [
        name for name in REQUIRED_COLUMNS if name in schema_names
    ]

    missing_columns = [
        name for name in REQUIRED_COLUMNS if name not in schema_names
    ]

    table = parquet_file.read(columns=selected_columns)
    df = table.to_pandas()

    row_count = len(df)

    null_counts = {
        name: int(count)
        for name, count in df.isna().sum().items()
    }

    null_percentages = {
        name: round(count / row_count * 100, 4) if row_count else 0.0
        for name, count in null_counts.items()
    }

    checks = {}

    if {"lpep_pickup_datetime", "lpep_dropoff_datetime"}.issubset(df.columns):
        pickup = df["lpep_pickup_datetime"]
        dropoff = df["lpep_dropoff_datetime"]

        checks["missing_pickup_timestamp"] = int(pickup.isna().sum())
        checks["missing_dropoff_timestamp"] = int(dropoff.isna().sum())
        checks["dropoff_before_pickup"] = int(
            (dropoff < pickup).fillna(False).sum()
        )

    if "trip_distance" in df.columns:
        checks["negative_trip_distance"] = int(
            (df["trip_distance"] < 0).fillna(False).sum()
        )
        checks["zero_trip_distance"] = int(
            (df["trip_distance"] == 0).fillna(False).sum()
        )

    if "fare_amount" in df.columns:
        checks["negative_fare_amount"] = int(
            (df["fare_amount"] < 0).fillna(False).sum()
        )

    if "total_amount" in df.columns:
        checks["negative_total_amount"] = int(
            (df["total_amount"] < 0).fillna(False).sum()
        )

    # Exact duplicate detection across the selected columns only.
    # This is NOT a full-row duplicate check across the entire dataset.
    duplicate_count = int(df.duplicated().sum())

    checks["duplicates_in_selected_columns"] = duplicate_count

    if missing_columns:
        status = "SCHEMA_INCOMPLETE"
    elif row_count != expected_rows:
        status = "ROW_COUNT_MISMATCH"
    else:
        status = "PROFILED"

    return {
        "file_name": file_path.name,
        "file_path": str(file_path.resolve()),
        "profiled_at_utc": datetime.now(timezone.utc).isoformat(),
        "expected_rows": expected_rows,
        "actual_rows": row_count,
        "column_count_profiled": len(selected_columns),
        "missing_required_columns": missing_columns,
        "null_counts": null_counts,
        "null_percentages": null_percentages,
        "checks": checks,
        "status": status,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Profile a TLC Parquet batch for data quality."
    )
    parser.add_argument(
        "--batch",
        default="green_tripdata_2015-07.parquet",
        help="Parquet filename to profile",
    )
    args = parser.parse_args()

    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"Manifest not found: {MANIFEST_PATH}"
        )

    import pandas as pd

    manifest = pd.read_csv(MANIFEST_PATH)
    match = manifest.loc[
        (manifest["file_name"] == args.batch)
        & (manifest["status"] == "SUCCESS")
    ]

    if match.empty:
        raise ValueError(
            f"No successfully inventoried batch found: {args.batch}"
        )

    record = match.iloc[0]
    file_path = Path(str(record["file_path"]))

    if not file_path.is_file():
        raise FileNotFoundError(f"Source file missing: {file_path}")

    result = profile_batch(
        file_path=file_path,
        expected_rows=int(record["row_count"]),
    )

    QUALITY_REPORT_DIR.mkdir(parents=True, exist_ok=True)

    quality_report_path = (
    QUALITY_REPORT_DIR / f"{Path(args.batch).stem}.json"
    )

    with quality_report_path.open("w", encoding="utf-8") as output:
        json.dump(result, output, indent=2, default=str)

        print(f"Batch: {result['file_name']}")
        print(f"Expected rows: {result['expected_rows']:,}")
        print(f"Actual rows: {result['actual_rows']:,}")
        print(f"Status: {result['status']}")
        print(f"Quality report: {quality_report_path}")
        print("\nQuality checks:")

    for check, value in result["checks"].items():
        print(f"  {check}: {value}")

    if result["missing_required_columns"]:
        print(
        "Missing required columns:",
        result["missing_required_columns"],
        )


if __name__ == "__main__":
    main()
