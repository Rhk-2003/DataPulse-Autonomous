from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "schema_compatibility"


def classify_type_change(
    baseline_type: str,
    candidate_type: str,
) -> tuple[str, str]:
    """Return an initial severity and explanation for a type change."""
    old_type = baseline_type.strip().lower()
    new_type = candidate_type.strip().lower()

    # Arrow string representations with equivalent logical meaning.
    if (old_type, new_type) in {
        ("string", "large_string"),
        ("large_string", "string"),
    }:
        return (
            "INFO",
            "String representation changed; verify consumer compatibility.",
        )

    # A null-only column becoming populated with a concrete type.
    if old_type == "null" and new_type != "null":
        return (
            "WARNING",
            "Column changed from null type to a concrete type; "
            "validate values and downstream null handling.",
        )

    # Numeric type changes can affect precision, range, and casting.
    numeric_types = {
        "int8", "int16", "int32", "int64",
        "uint8", "uint16", "uint32", "uint64",
        "float", "double", "halffloat",
    }

    if old_type in numeric_types and new_type in numeric_types:
        return (
            "WARNING",
            "Numeric representation changed; validate range, precision, "
            "fractional values, and downstream conversions.",
        )

    return (
        "WARNING",
        "Column type changed; validate conversion and consumer compatibility.",
    )


def evaluate_compatibility(
    drift_report: dict,
    required_columns: set[str] | None = None,
) -> dict:
    """Evaluate a schema-drift report against an initial policy."""
    required_columns = required_columns or set()
    issues = []

    added_details = drift_report.get("added_column_details", [])
    removed_details = drift_report.get("removed_column_details", [])

    # Support reports created before detailed column types were recorded.
    added_columns = drift_report.get("added_columns", [])
    removed_columns = drift_report.get("removed_columns", [])

    if added_details:
        for item in added_details:
            issues.append({
                "rule": "column_added",
                "severity": "INFO",
                "column": item["column"],
                "candidate_type": item.get("candidate_type"),
                "message": (
                    "New column detected. Confirm downstream consumers "
                    "allow additional columns."
                ),
            })
    else:
        for column in added_columns:
            issues.append({
                "rule": "column_added",
                "severity": "INFO",
                "column": column,
                "message": (
                    "New column detected. Confirm downstream consumers "
                    "allow additional columns."
                ),
            })

    if removed_details:
        for item in removed_details:
            column = item["column"]
            is_required = column in required_columns

            issues.append({
                "rule": (
                    "required_column_removed"
                    if is_required
                    else "column_removed"
                ),
                "severity": "FAIL" if is_required else "WARNING",
                "column": column,
                "baseline_type": item.get("baseline_type"),
                "message": (
                    "A required column was removed from the schema."
                    if is_required
                    else "A column was removed; review downstream dependencies."
                ),
            })
    else:
        for column in removed_columns:
            is_required = column in required_columns

            issues.append({
                "rule": (
                    "required_column_removed"
                    if is_required
                    else "column_removed"
                ),
                "severity": "FAIL" if is_required else "WARNING",
                "column": column,
                "message": (
                    "A required column was removed from the schema."
                    if is_required
                    else "A column was removed; review downstream dependencies."
                ),
            })

    for change in drift_report.get("type_changes", []):
        severity, message = classify_type_change(
            change["baseline_type"],
            change["candidate_type"],
        )

        issues.append({
            "rule": "column_type_changed",
            "severity": severity,
            "column": change["column"],
            "baseline_type": change["baseline_type"],
            "candidate_type": change["candidate_type"],
            "message": message,
        })

    if any(issue["severity"] == "FAIL" for issue in issues):
        decision = "FAIL"
    elif any(issue["severity"] == "WARNING" for issue in issues):
        decision = "WARNING"
    elif any(issue["severity"] == "INFO" for issue in issues):
        decision = "INFO"
    else:
        decision = "PASS"

    return {
        "baseline_batch": drift_report["baseline_batch"],
        "candidate_batch": drift_report["candidate_batch"],
        "schema_drift_status": drift_report["status"],
        "compatibility_decision": decision,
        "required_columns": sorted(required_columns),
        "issues": issues,
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate schema drift against a compatibility policy."
    )
    parser.add_argument(
        "--report",
        required=True,
        help="Path to an existing schema-drift JSON report.",
    )
    parser.add_argument(
        "--required-columns",
        default="",
        help="Comma-separated list of columns that must not be removed.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for compatibility decision reports.",
    )

    args = parser.parse_args()

    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = PROJECT_ROOT / report_path

    if not report_path.exists():
        parser.error(f"Schema-drift report not found: {report_path}")

    with report_path.open(encoding="utf-8") as file:
        drift_report = json.load(file)

    required_columns = {
        column.strip()
        for column in args.required_columns.split(",")
        if column.strip()
    }

    result = evaluate_compatibility(
        drift_report,
        required_columns=required_columns,
    )

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / report_path.name

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(result, file, indent=2)

    print(f"Baseline: {result['baseline_batch']}")
    print(f"Candidate: {result['candidate_batch']}")
    print(f"Schema drift: {result['schema_drift_status']}")
    print(f"Compatibility decision: {result['compatibility_decision']}")

    for issue in result["issues"]:
        print(
            f"  [{issue['severity']}] {issue['rule']}: "
            f"{issue['column']} — {issue['message']}"
        )

    print(f"Report saved to: {output_path}")


if __name__ == "__main__":
    main()