
from src.datapulse.schema_drift import parse_schema


def test_parser_ignores_pandas_metadata():
    schema_text = (
        "trip_distance: double | trip_type: int64 "
        "| -- schema metadata -- "
        "| pandas: '{\"index_columns\": []}'"
    )

    result = parse_schema(schema_text)

    assert result == {
        "trip_distance": "double",
        "trip_type": "int64",
    }
    assert "pandas" not in result
