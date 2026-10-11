
from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
QUALITY_DIR = PROJECT_ROOT / "reports" / "quality"
DECISION_DIR = PROJECT_ROOT / "reports" / "quality_decisions"

# Initial investigation thresholds, not universal industry standards.
MAX_ZERO_DISTANCE_RATE = 0.02
MAX_NEGATIVE_FARE_RATE = 0.005
MAX_NEGATIVE_TOTAL_RATE = 0.005


def evaluate_report(report: dict) -> dict:
    checks = report["checks"]
    rows = report["actual_rows"]
    issues = []

    if report["missing_required_columns"]:
        issues.append({
            "rule": "required_columns_present",
            "severity": "FAIL",
            "message": "One or more required columns are missing.",
        })

    if report["actual_rows"] != report["expected_rows"]:
        issues.append({
            "rule": "row_count_matches_manifest",
            "severity": "FAIL",
            "message": "Actual row count differs from the manifest.",
        })

    if rows > 0:
        rates = {
            "zero_trip_distance": (
                checks.get("zero_trip_distance", 0) / rows
            ),
            "negative_fare_amount": (
                checks.get("negative_fare_amount", 0) / rows
            ),
            "negative_total_amount": (
                checks.get("negative_total_amount", 0) / rows
            ),
        }

        thresholds = {
            "zero_trip_distance": MAX_ZERO_DISTANCE_RATE,
            "negative_fare_amount": MAX_NEGATIVE_FARE_RATE,
            "negative_total_amount": MAX_NEGATIVE_TOTAL_RATE,
        }

        for rule, rate in rates.items():
            if rate > thresholds[rule]:
                issues.append({
                    "rule": rule,
                    "severity": "WARNING",
                    "observed_rate": round(rate, 6),
                    "threshold": thresholds[rule],
                    "message": (
                        f"{rule} rate exceeds the configured "
                        "investigation threshold."
                    ),
                })

    if checks.get("missing_pickup_timestamp", 0) > 0:
        issues.append({
            "rule": "missing_pickup_timestamp",
            "severity": "WARNING",
            "message": "Pickup timestamps are missing.",
        })

    if checks.get("missing_dropoff_timestamp", 0) > 0:
        issues.append({
            "rule": "missing_dropoff_timestamp",
            "severity": "WARNING",
            "message": "Drop-off timestamps are missing.",
        })

    if checks.get("dropoff_before_pickup", 0) > 0:
        issues.append({
            "rule": "dropoff_before_pickup",
            "severity": "WARNING",
            "message": "Some drop-offs precede pickups.",
        })

    if checks.get("duplicates_in_selected_columns", 0) > 0:
        issues.append({
            "rule": "duplicates_in_selected_columns",
            "severity": "WARNING",
            "message": (
                "Repeated rows exist across the profiled columns; "
                "these are not confirmed full-record duplicates."
            ),
        })

    if any(issue["severity"] == "FAIL" for issue in issues):
        decision = "FAIL"
    elif any(issue["severity"] == "WARNING" for issue in issues):
        decision = "WARNING"
    else:
        decision = "PASS"

    return {
        "batch_id": report["file_name"],
        "decision": decision,
        "issues": issues,
        "rules_evaluated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
    }


def main() -> None:
    if not QUALITY_DIR.exists():
        raise FileNotFoundError(
            f"No quality reports found: {QUALITY_DIR}. "
            "Run the quality profiler first."
        )

    report_paths = sorted(QUALITY_DIR.glob("*.json"))

    if not report_paths:
        raise FileNotFoundError("No batch quality reports found.")

    DECISION_DIR.mkdir(parents=True, exist_ok=True)

    for report_path in report_paths:
        with report_path.open(encoding="utf-8") as source:
            report = json.load(source)

        result = evaluate_report(report)

        output_path = DECISION_DIR / report_path.name
        with output_path.open("w", encoding="utf-8") as output:
            json.dump(result, output, indent=2)

        print(f"{result['batch_id']}: {result['decision']}")

        for issue in result["issues"]:
            print(
                f"  [{issue['severity']}] "
                f"{issue['rule']}: {issue['message']}"
            )


if __name__ == "__main__":
    main()
