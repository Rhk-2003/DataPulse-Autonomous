
from src.datapulse.schema_compatibility import evaluate_compatibility


def make_report(
    added_columns=None,
    removed_columns=None,
    type_changes=None,
):
    added_columns = added_columns or []
    removed_columns = removed_columns or []
    type_changes = type_changes or []

    return {
        "baseline_batch": "baseline.parquet",
        "candidate_batch": "candidate.parquet",
        "status": (
            "DRIFT_DETECTED"
            if added_columns or removed_columns or type_changes
            else "NO_DRIFT"
        ),
        "added_columns": added_columns,
        "removed_columns": removed_columns,
        "type_changes": type_changes,
    }


def test_no_drift_passes():
    result = evaluate_compatibility(make_report())

    assert result["compatibility_decision"] == "PASS"
    assert result["issues"] == []


def test_added_column_is_informational():
    report = make_report(added_columns=["cbd_congestion_fee"])

    result = evaluate_compatibility(report)

    assert result["compatibility_decision"] == "INFO"
    assert result["issues"][0]["rule"] == "column_added"


def test_numeric_type_change_warns():
    report = make_report(
        type_changes=[
            {
                "column": "trip_type",
                "baseline_type": "double",
                "candidate_type": "int64",
            }
        ]
    )

    result = evaluate_compatibility(report)

    assert result["compatibility_decision"] == "WARNING"
    assert result["issues"][0]["severity"] == "WARNING"


def test_removed_optional_column_warns():
    report = make_report(removed_columns=["legacy_column"])

    result = evaluate_compatibility(report)

    assert result["compatibility_decision"] == "WARNING"


def test_removed_required_column_fails():
    report = make_report(removed_columns=["trip_type"])

    result = evaluate_compatibility(
        report,
        required_columns={"trip_type"},
    )

    assert result["compatibility_decision"] == "FAIL"
    assert result["issues"][0]["rule"] == "required_column_removed"


def test_string_representation_change_is_informational():
    report = make_report(
        type_changes=[
            {
                "column": "store_and_fwd_flag",
                "baseline_type": "string",
                "candidate_type": "large_string",
            }
        ]
    )

    result = evaluate_compatibility(report)

    assert result["compatibility_decision"] == "INFO"
