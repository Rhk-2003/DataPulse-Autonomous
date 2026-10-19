
"""Validate a Parquet schema against a versioned DataPulse contract."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT = PROJECT_ROOT / "contracts" / "green_taxi_v1.json"


def validate_schema(schema, contract: dict) -> dict:
    """Compare a PyArrow schema with a DataPulse JSON contract."""

    contract_fields = contract["fields"]
    actual_fields = {field.name: field for field in schema}

    issues = []
    warnings = []
    information = []

    # 1. Check required fields and their data types.
    for name, rules in contract_fields.items():
        if name not in actual_fields:
            issues.append({
                "field": name,
                "issue": "MISSING_REQUIRED_COLUMN",
                "expected": rules["expected_type"],
            })
            continue

        actual_field = actual_fields[name]
        actual_type = str(actual_field.type)
        expected_type = rules["expected_type"]
        accepted_types = rules.get("accepted_types", [expected_type])

        # A field declared as Arrow null may evolve to a concrete type.
        if (
            actual_type != expected_type
            and expected_type == "null"
            and rules.get("allow_type_evolution", False)
            and actual_type != "null"
        ):
            warnings.append({
                "field": name,
                "issue": "TYPE_EVOLUTION",
                "expected": expected_type,
                "actual": actual_type,
                "message": "A previously untyped field now has a concrete type.",
            })

        elif actual_type not in accepted_types:
            issues.append({
                "field": name,
                "issue": "INCOMPATIBLE_TYPE",
                "expected": accepted_types,
                "actual": actual_type,
            })

        # A contract can prohibit nullable fields.
        if not rules.get("nullable", True) and actual_field.nullable:
            issues.append({
                "field": name,
                "issue": "NULLABLE_SCHEMA_FIELD_NOT_ALLOWED",
                "expected_nullable": False,
                "actual_nullable": True,
            })

    # 2. Check additional fields.
    extra_columns = sorted(set(actual_fields) - set(contract_fields))

    if extra_columns and not contract.get("allow_extra_columns", False):
        for name in extra_columns:
            issues.append({
                "field": name,
                "issue": "UNEXPECTED_COLUMN",
                "actual": str(actual_fields[name].type),
            })

    elif extra_columns:
        information.append({
            "issue": "EXTRA_COLUMNS_ALLOWED",
            "columns": [
                {"name": name, "type": str(actual_fields[name].type)}
                for name in extra_columns
            ],
        })

    # 3. Determine the overall decision.
    if issues:
        decision = "FAIL"
    elif warnings:
        decision = "WARNING"
    else:
        decision = "PASS"

    return {
        "contract_name": contract.get("contract_name", "unknown"),
        "contract_version": contract.get("contract_version", "unknown"),
        "decision": decision,
        "expected_field_count": len(contract_fields),
        "actual_field_count": len(actual_fields),
        "missing_columns": sorted(set(contract_fields) - set(actual_fields)),
        "extra_columns": extra_columns,
        "issues": issues,
        "warnings": warnings,
        "information": information,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a Parquet schema against a DataPulse contract."
    )
    parser.add_argument(
        "parquet_file",
        help="Path to the Parquet batch to validate.",
    )
    parser.add_argument(
        "--contract",
        default=str(DEFAULT_CONTRACT),
        help="Path to the JSON contract.",
    )
    args = parser.parse_args()

    parquet_path = Path(args.parquet_file)
    contract_path = Path(args.contract)

    if not parquet_path.is_absolute():
        parquet_path = PROJECT_ROOT / parquet_path

    if not contract_path.is_absolute():
        contract_path = PROJECT_ROOT / contract_path

    if not parquet_path.is_file():
        parser.error(f"Parquet file not found: {parquet_path}")

    if not contract_path.is_file():
        parser.error(f"Contract file not found: {contract_path}")

    with contract_path.open("r", encoding="utf-8") as file:
        contract = json.load(file)

    schema = pq.ParquetFile(parquet_path).schema_arrow
    result = validate_schema(schema, contract)

    result.update({
        "batch": parquet_path.name,
        "contract_path": str(contract_path),
        "validated_at": datetime.now(timezone.utc).isoformat(),
    })

    report_dir = PROJECT_ROOT / "reports" / "contracts"
    report_dir.mkdir(parents=True, exist_ok=True)

    report_path = report_dir / f"{parquet_path.stem}_contract_validation.json"
    report_path.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    print(f"Batch: {parquet_path.name}")
    print(f"Contract: {contract['contract_name']} v{contract['contract_version']}")
    print(f"Decision: {result['decision']}")
    print(f"Missing columns: {len(result['missing_columns'])}")
    print(f"Extra columns: {len(result['extra_columns'])}")
    print(f"Issues: {len(result['issues'])}")
    print(f"Warnings: {len(result['warnings'])}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
