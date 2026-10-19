
import pyarrow as pa

from src.datapulse.contract_validator import validate_schema


def make_contract():
    return {
        "contract_name": "test_contract",
        "contract_version": "1.0.0",
        "allow_extra_columns": True,
        "fields": {
            "VendorID": {
                "expected_type": "int64",
                "accepted_types": ["int64", "int32"],
                "nullable": True,
            },
            "store_and_fwd_flag": {
                "expected_type": "string",
                "accepted_types": ["string", "large_string"],
                "nullable": True,
            },
            "ehail_fee": {
                "expected_type": "null",
                "nullable": True,
                "allow_type_evolution": True,
            },
        },
    }


def make_valid_schema():
    return pa.schema([
        pa.field("VendorID", pa.int64(), nullable=True),
        pa.field("store_and_fwd_flag", pa.string(), nullable=True),
        pa.field("ehail_fee", pa.null(), nullable=True),
    ])


def test_matching_schema_passes():
    result = validate_schema(make_valid_schema(), make_contract())

    assert result["decision"] == "PASS"
    assert result["issues"] == []
    assert result["warnings"] == []


def test_accepted_integer_type_passes():
    schema = pa.schema([
        pa.field("VendorID", pa.int32(), nullable=True),
        pa.field("store_and_fwd_flag", pa.string(), nullable=True),
        pa.field("ehail_fee", pa.null(), nullable=True),
    ])

    result = validate_schema(schema, make_contract())

    assert result["decision"] == "PASS"
    assert result["issues"] == []


def test_accepted_large_string_type_passes():
    schema = pa.schema([
        pa.field("VendorID", pa.int64(), nullable=True),
        pa.field("store_and_fwd_flag", pa.large_string(), nullable=True),
        pa.field("ehail_fee", pa.null(), nullable=True),
    ])

    result = validate_schema(schema, make_contract())

    assert result["decision"] == "PASS"
    assert result["issues"] == []


def test_missing_required_column_fails():
    schema = pa.schema([
        pa.field("VendorID", pa.int64(), nullable=True),
        pa.field("ehail_fee", pa.null(), nullable=True),
    ])

    result = validate_schema(schema, make_contract())

    assert result["decision"] == "FAIL"
    assert "store_and_fwd_flag" in result["missing_columns"]


def test_unaccepted_type_fails():
    schema = pa.schema([
        pa.field("VendorID", pa.string(), nullable=True),
        pa.field("store_and_fwd_flag", pa.string(), nullable=True),
        pa.field("ehail_fee", pa.null(), nullable=True),
    ])

    result = validate_schema(schema, make_contract())

    assert result["decision"] == "FAIL"
    assert any(
        issue["field"] == "VendorID"
        and issue["issue"] == "INCOMPATIBLE_TYPE"
        for issue in result["issues"]
    )


def test_null_type_evolution_warns():
    schema = pa.schema([
        pa.field("VendorID", pa.int64(), nullable=True),
        pa.field("store_and_fwd_flag", pa.string(), nullable=True),
        pa.field("ehail_fee", pa.float64(), nullable=True),
    ])

    result = validate_schema(schema, make_contract())

    assert result["decision"] == "WARNING"
    assert result["issues"] == []
    assert any(
        warning["field"] == "ehail_fee"
        and warning["issue"] == "TYPE_EVOLUTION"
        for warning in result["warnings"]
    )


def test_extra_column_is_allowed():
    schema = pa.schema([
        pa.field("VendorID", pa.int64(), nullable=True),
        pa.field("store_and_fwd_flag", pa.string(), nullable=True),
        pa.field("ehail_fee", pa.null(), nullable=True),
        pa.field("cbd_congestion_fee", pa.float64(), nullable=True),
    ])

    result = validate_schema(schema, make_contract())

    assert result["decision"] == "PASS"
    assert result["issues"] == []
    assert result["extra_columns"] == ["cbd_congestion_fee"]
    assert result["information"][0]["issue"] == "EXTRA_COLUMNS_ALLOWED"


def test_extra_column_fails_when_disallowed():
    contract = make_contract()
    contract["allow_extra_columns"] = False

    schema = pa.schema([
        pa.field("VendorID", pa.int64(), nullable=True),
        pa.field("store_and_fwd_flag", pa.string(), nullable=True),
        pa.field("ehail_fee", pa.null(), nullable=True),
        pa.field("unexpected_field", pa.string(), nullable=True),
    ])

    result = validate_schema(schema, contract)

    assert result["decision"] == "FAIL"
    assert any(
        issue["issue"] == "UNEXPECTED_COLUMN"
        for issue in result["issues"]
    )
