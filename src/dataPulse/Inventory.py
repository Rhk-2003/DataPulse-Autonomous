
from __future__ import annotations

import csv
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "TLC_Data"
REPORT_DIR = PROJECT_ROOT / "reports"

# Examples: green_tripdata_2015-07.parquet
FILENAME_PATTERN = re.compile(
    r"^(?P<dataset_type>.+)_"
    r"(?P<year>\d{4})-(?P<month>\d{2})\.parquet$",
    re.IGNORECASE,
)

MANIFEST_COLUMNS = [
    "file_name",
    "file_path",
    "dataset_type",
    "year",
    "month",
    "file_size_bytes",
    "row_count",
    "column_count",
    "schema",
    "schema_fingerprint",
    "status",
    "error",
    "scanned_at_utc",
]


def inspect_parquet(file_path: Path) -> dict:
    """Inspect one Parquet file without loading its full dataset."""
    stat = file_path.stat()
    match = FILENAME_PATTERN.match(file_path.name)

    record = {
        "file_name": file_path.name,
        "file_path": str(file_path.resolve()),
        "dataset_type": match.group("dataset_type") if match else "",
        "year": match.group("year") if match else "",
        "month": match.group("month") if match else "",
        "file_size_bytes": stat.st_size,
        "row_count": "",
        "column_count": "",
        "schema": "",
        "schema_fingerprint": "",
        "status": "SUCCESS",
        "error": "",
        "scanned_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    try:
        parquet_file = pq.ParquetFile(file_path)
        schema = parquet_file.schema_arrow
        schema_text = str(schema)

        record.update({
            "row_count": parquet_file.metadata.num_rows,
            "column_count": len(schema),
            "schema": schema_text.replace("\n", " | "),
            "schema_fingerprint": hashlib.sha256(
                schema_text.encode("utf-8")
            ).hexdigest(),
        })

    except Exception as exc:
        record["status"] = "FAILED"
        record["error"] = f"{type(exc).__name__}: {exc}"

    return record


def build_manifest() -> Path:
    """Scan all Parquet files and write a CSV batch manifest."""
    if not DATA_DIR.exists():
        raise FileNotFoundError(
            f"Data directory does not exist: {DATA_DIR}"
        )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    parquet_files = sorted(
        path for path in DATA_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() == ".parquet"
    )

    records = [inspect_parquet(path) for path in parquet_files]

    manifest_path = REPORT_DIR / "batch_manifest.csv"

    with manifest_path.open(
        "w", newline="", encoding="utf-8-sig"
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file, fieldnames=MANIFEST_COLUMNS
        )
        writer.writeheader()
        writer.writerows(records)

    successful = sum(r["status"] == "SUCCESS" for r in records)
    failed = len(records) - successful

    print(f"Files discovered: {len(records)}")
    print(f"Successfully inspected: {successful}")
    print(f"Failed inspections: {failed}")
    print(f"Manifest saved to: {manifest_path}")

    return manifest_path


if __name__ == "__main__":
    build_manifest()
