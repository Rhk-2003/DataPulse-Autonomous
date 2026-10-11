
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "reports"
MANIFEST_PATH = REPORT_DIR / "batch_manifest.csv"
REPLAY_LOG_PATH = REPORT_DIR / "replay_log.csv"

LOG_COLUMNS = [
    "batch_id",
    "file_name",
    "dataset_type",
    "year",
    "month",
    "row_count",
    "file_size_bytes",
    "released_at_utc",
    "status",
]


def load_manifest() -> pd.DataFrame:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"Manifest not found: {MANIFEST_PATH}. "
            "Run the inventory module first."
        )

    manifest = pd.read_csv(MANIFEST_PATH)

    required = {
        "file_name",
        "file_path",
        "dataset_type",
        "year",
        "month",
        "row_count",
        "file_size_bytes",
        "status",
    }
    missing = required - set(manifest.columns)

    if missing:
        raise ValueError(
            f"Manifest is missing required columns: {sorted(missing)}"
        )

    return manifest


def load_released_batch_ids() -> set[str]:
    if not REPLAY_LOG_PATH.exists():
        return set()

    log = pd.read_csv(REPLAY_LOG_PATH)

    if not {"batch_id", "status"}.issubset(log.columns):
        raise ValueError("Replay log has an unexpected format.")

    released = log.loc[
        log["status"] == "RELEASED", "batch_id"
    ]

    return set(released.astype(str))


def append_replay_event(record: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    write_header = not REPLAY_LOG_PATH.exists()

    with REPLAY_LOG_PATH.open(
        "a", newline="", encoding="utf-8"
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file, fieldnames=LOG_COLUMNS
        )

        if write_header:
            writer.writeheader()

        writer.writerow(record)


def replay_next_batch(
    dataset_type: str,
    start_year: int,
    start_month: int,
) -> bool:
    manifest = load_manifest()

    # Only replay files successfully inspected by inventory.
    eligible = manifest.loc[
        (manifest["dataset_type"] == dataset_type)
        & (manifest["status"] == "SUCCESS")
    ].copy()

    eligible["year"] = pd.to_numeric(
        eligible["year"], errors="coerce"
    )
    eligible["month"] = pd.to_numeric(
        eligible["month"], errors="coerce"
    )

    eligible = eligible.dropna(subset=["year", "month"])

    # Keep batches on or after the requested starting month.
    eligible = eligible.loc[
        (eligible["year"] > start_year)
        | (
            (eligible["year"] == start_year)
            & (eligible["month"] >= start_month)
        )
    ]

    eligible = eligible.sort_values(
        ["year", "month", "file_name"]
    )

    released_ids = load_released_batch_ids()

    for _, batch in eligible.iterrows():
        batch_id = str(batch["file_name"])

        if batch_id in released_ids:
            continue

        # Verify the source still exists before announcing arrival.
        source_path = Path(str(batch["file_path"]))

        if not source_path.is_file():
            print(f"ERROR: Source file is missing: {source_path}")
            return False

        event = {
            "batch_id": batch_id,
            "file_name": batch["file_name"],
            "dataset_type": batch["dataset_type"],
            "year": int(batch["year"]),
            "month": int(batch["month"]),
            "row_count": int(batch["row_count"]),
            "file_size_bytes": int(batch["file_size_bytes"]),
            "released_at_utc": datetime.now(
                timezone.utc
            ).isoformat(),
            "status": "RELEASED",
        }

        append_replay_event(event)

        print("Batch released successfully")
        print(f"Batch ID: {event['batch_id']}")
        print(
            f"Period: {event['year']}-{event['month']:02d}"
        )
        print(f"Rows: {event['row_count']:,}")
        print(
            f"Size: {event['file_size_bytes']:,} bytes"
        )
        print(f"Replay log: {REPLAY_LOG_PATH}")

        return True

    print("No eligible unreleased batches remain.")
    return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replay historical TLC files as arriving batches."
    )

    parser.add_argument(
        "--dataset-type",
        default="green_tripdata",
        help="Dataset prefix, e.g. green_tripdata",
    )
    parser.add_argument("--start-year", type=int, default=2015)
    parser.add_argument("--start-month", type=int, default=7)

    args = parser.parse_args()

    if not 1 <= args.start_month <= 12:
        parser.error("--start-month must be between 1 and 12")

    replay_next_batch(
        dataset_type=args.dataset_type,
        start_year=args.start_year,
        start_month=args.start_month,
    )


if __name__ == "__main__":
    main()
