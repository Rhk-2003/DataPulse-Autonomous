
from src.datapulse.schema_drift import compare_schemas


def test_identical_schemas_have_no_drift():
    schema = {
        "pickup_time": "timestamp[us]",
        "trip_distance": "double",
    }

    result = compare_schemas(
        "july.parquet", schema,
        "august.parquet", schema,
    )

    assert result["status"] == "NO_DRIFT"
    assert result["added_columns"] == []
    assert result["removed_columns"] == []
    assert result["type_changes"] == []


def test_added_column_is_detected():
    baseline = {"trip_distance": "double"}
    candidate = {
        "trip_distance": "double",
        "new_column": "string",
    }

    result = compare_schemas(
        "july.parquet", baseline,
        "august.parquet", candidate,
    )

    assert result["added_columns"] == ["new_column"]
    assert result["schema_drift_detected"] is True


def test_removed_column_is_detected():
    baseline = {
        "trip_distance": "double",
        "fare_amount": "double",
    }
    candidate = {"trip_distance": "double"}

    result = compare_schemas(
        "july.parquet", baseline,
        "august.parquet", candidate,
    )

    assert result["removed_columns"] == ["fare_amount"]


def test_type_change_is_detected():
    baseline = {"trip_type": "double"}
    candidate = {"trip_type": "int64"}

    result = compare_schemas(
        "july.parquet", baseline,
        "august.parquet", candidate,
    )

    assert result["type_changes"] == [
        {
            "column": "trip_type",
            "baseline_type": "double",
            "candidate_type": "int64",
        }
    ]
