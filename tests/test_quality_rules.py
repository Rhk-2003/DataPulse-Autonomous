
from src.datapulse.quality_rules import evaluate_report


def make_report(**overrides):
    report = {
        "file_name": "green_tripdata_2015-07.parquet",
        "expected_rows": 1000,
        "actual_rows": 1000,
        "missing_required_columns": [],
        "checks": {
            "zero_trip_distance": 10,
            "negative_fare_amount": 1,
            "negative_total_amount": 1,
            "missing_pickup_timestamp": 0,
            "missing_dropoff_timestamp": 0,
            "dropoff_before_pickup": 0,
            "duplicates_in_selected_columns": 0,
        },
    }
    report.update(overrides)
    return report


def test_clean_report_passes():
    result = evaluate_report(make_report())
    assert result["decision"] == "PASS"
    assert result["issues"] == []


def test_selected_column_duplicates_warn():
    report = make_report(
        checks={
            "zero_trip_distance": 10,
            "negative_fare_amount": 1,
            "negative_total_amount": 1,
            "missing_pickup_timestamp": 0,
            "missing_dropoff_timestamp": 0,
            "dropoff_before_pickup": 0,
            "duplicates_in_selected_columns": 3,
        }
    )

    result = evaluate_report(report)

    assert result["decision"] == "WARNING"
    assert any(
        issue["rule"] == "duplicates_in_selected_columns"
        for issue in result["issues"]
    )


def test_missing_required_column_fails():
    result = evaluate_report(
        make_report(missing_required_columns=["trip_distance"])
    )

    assert result["decision"] == "FAIL"


def test_row_count_mismatch_fails():
    result = evaluate_report(make_report(actual_rows=999))

    assert result["decision"] == "FAIL"
