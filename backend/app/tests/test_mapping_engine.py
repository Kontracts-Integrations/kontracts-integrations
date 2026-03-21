"""
Unit tests for the mapping engine transforms and validation.
"""
import pytest

from app.mapping_engine.engine import MappingEngine, _get_nested_value, _set_nested_value
from app.mapping_engine.transforms import apply_transform
from app.mapping_engine.validators import validate_payload


# ──────────────────────────────────────────────
# Transform tests
# ──────────────────────────────────────────────


class TestDirectTransform:
    def test_direct_copies_value(self):
        assert apply_transform("direct", "hello", {}) == "hello"

    def test_direct_passes_none_through(self):
        assert apply_transform("direct", None, {}) is None

    def test_direct_uses_default_for_none(self):
        assert apply_transform("direct", None, {"default": "N/A"}) == "N/A"


class TestConstantTransform:
    def test_constant_ignores_value(self):
        assert apply_transform("constant", "anything", {"value": "USD"}) == "USD"

    def test_constant_returns_none_if_unconfigured(self):
        assert apply_transform("constant", "x", {}) is None


class TestDateFormatTransform:
    def test_iso_to_date(self):
        result = apply_transform(
            "date_format",
            "2020-01-15T09:00:00Z",
            {"output_format": "%Y-%m-%d"},
        )
        assert result == "2020-01-15"

    def test_explicit_input_format(self):
        result = apply_transform(
            "date_format",
            "15/01/2020",
            {"input_format": "%d/%m/%Y", "output_format": "%Y-%m-%d"},
        )
        assert result == "2020-01-15"

    def test_null_value(self):
        assert apply_transform("date_format", None, {}) is None

    def test_invalid_date_returns_original(self):
        result = apply_transform("date_format", "not-a-date", {})
        assert result == "not-a-date"


class TestNumberConvertTransform:
    def test_string_to_float(self):
        assert apply_transform("number_convert", "75000.00", {}) == 75000.0

    def test_string_with_commas(self):
        assert apply_transform("number_convert", "1,234,567.89", {}) == 1234567.89

    def test_currency_string(self):
        result = apply_transform("number_convert", "$75,000.00", {})
        assert result == 75000.0

    def test_to_int(self):
        result = apply_transform("number_convert", "42.7", {"as_type": "int"})
        assert result == 43

    def test_divisor(self):
        result = apply_transform("number_convert", "3500", {"divisor": 100})
        assert result == 35.0

    def test_rounding(self):
        result = apply_transform("number_convert", "3.14159", {"decimals": 2})
        assert result == 3.14

    def test_percentage_to_decimal(self):
        result = apply_transform("number_convert", "3.5", {"divisor": 100, "decimals": 5})
        assert result == pytest.approx(0.035, rel=1e-4)

    def test_null_returns_default(self):
        result = apply_transform("number_convert", None, {"default": 0.0})
        assert result == 0.0


class TestBooleanConvertTransform:
    def test_true_string(self):
        assert apply_transform("boolean_convert", "true", {}) is True

    def test_false_string(self):
        assert apply_transform("boolean_convert", "false", {}) is False

    def test_yes_no(self):
        assert apply_transform("boolean_convert", "yes", {}) is True
        assert apply_transform("boolean_convert", "no", {}) is False

    def test_already_bool(self):
        assert apply_transform("boolean_convert", True, {}) is True
        assert apply_transform("boolean_convert", False, {}) is False

    def test_numeric_string(self):
        assert apply_transform("boolean_convert", "1", {}) is True
        assert apply_transform("boolean_convert", "0", {}) is False

    def test_null_returns_none(self):
        assert apply_transform("boolean_convert", None, {}) is None


class TestStringTemplateTransform:
    def test_simple_substitution(self):
        record = {"city": "New York", "state": "NY"}
        result = apply_transform(
            "string_template",
            "New York",
            {"template": "{city}, {state}"},
            source_record=record,
        )
        assert result == "New York, NY"

    def test_value_placeholder(self):
        result = apply_transform(
            "string_template",
            "hello",
            {"template": "prefix_{value}_suffix"},
        )
        assert result == "prefix_hello_suffix"

    def test_missing_field_is_empty(self):
        result = apply_transform(
            "string_template",
            "test",
            {"template": "{missing_field}"},
            source_record={},
        )
        assert result == ""


class TestLookupTableTransform:
    def test_exact_match(self):
        result = apply_transform(
            "lookup_table",
            "Operating",
            {"table": {"Operating": "operating", "Finance": "finance"}},
        )
        assert result == "operating"

    def test_no_match_uses_default(self):
        result = apply_transform(
            "lookup_table",
            "Unknown",
            {"table": {"A": "a"}, "default": "other"},
        )
        assert result == "other"

    def test_no_match_uses_original_value(self):
        result = apply_transform("lookup_table", "Unknown", {"table": {"A": "a"}})
        assert result == "Unknown"


class TestJsonPathTransform:
    def test_simple_path(self):
        record = {"address": {"city": "Chicago"}}
        result = apply_transform(
            "json_path",
            None,
            {"path": "$.address.city"},
            source_record=record,
        )
        assert result == "Chicago"

    def test_missing_path_returns_default(self):
        result = apply_transform(
            "json_path",
            None,
            {"path": "$.nonexistent", "default": "N/A"},
            source_record={},
        )
        assert result == "N/A"


# ──────────────────────────────────────────────
# MappingEngine tests
# ──────────────────────────────────────────────


SAMPLE_FIELD_MAPPINGS = [
    {
        "id": "1",
        "source_field": "triNameTX",
        "target_field": "name",
        "transform_type": "direct",
    },
    {
        "id": "2",
        "source_field": "triLeaseTypeCL",
        "target_field": "lease_type",
        "transform_type": "lookup_table",
        "transform_config": {
            "table": {"Operating": "operating", "Finance": "finance"},
            "default": "operating",
        },
    },
    {
        "id": "3",
        "source_field": "triCommenceDateDT",
        "target_field": "commencement_date",
        "transform_type": "date_format",
        "transform_config": {"output_format": "%Y-%m-%d"},
    },
    {
        "id": "4",
        "source_field": "triExpirationDateDT",
        "target_field": "expiration_date",
        "transform_type": "date_format",
        "transform_config": {"output_format": "%Y-%m-%d"},
    },
    {
        "id": "5",
        "source_field": "triBaseRentAmountNU",
        "target_field": "monthly_payment",
        "transform_type": "number_convert",
        "transform_config": {"decimals": 2},
    },
    {
        "id": "6",
        "source_field": "triDiscountRateNU",
        "target_field": "discount_rate",
        "transform_type": "number_convert",
        "transform_config": {"divisor": 100, "decimals": 5},
    },
    {
        "id": "7",
        "source_field": "triRenewalOptionsBL",
        "target_field": "has_renewal_options",
        "transform_type": "boolean_convert",
    },
    {
        "id": "8",
        "source_field": "",
        "target_field": "currency",
        "transform_type": "constant",
        "transform_config": {"value": "USD"},
    },
]

SAMPLE_SOURCE_RECORD = {
    "triNameTX": "HQ Office Lease - New York",
    "triLeaseTypeCL": "Operating",
    "triCommenceDateDT": "2020-01-01",
    "triExpirationDateDT": "2025-12-31",
    "triBaseRentAmountNU": 75000.0,
    "triDiscountRateNU": 3.5,
    "triRenewalOptionsBL": True,
    "triCurrencyCL": "USD",
    "triRecordIdSY": 100001,
}


class TestMappingEngine:
    def test_apply_basic_mapping(self):
        engine = MappingEngine(SAMPLE_FIELD_MAPPINGS)
        payload, warnings = engine.apply(SAMPLE_SOURCE_RECORD)

        assert payload["name"] == "HQ Office Lease - New York"
        assert payload["lease_type"] == "operating"
        assert payload["commencement_date"] == "2020-01-01"
        assert payload["expiration_date"] == "2025-12-31"
        assert payload["monthly_payment"] == 75000.0
        assert payload["has_renewal_options"] is True
        assert payload["currency"] == "USD"
        assert len(warnings) == 0

    def test_discount_rate_conversion(self):
        engine = MappingEngine(SAMPLE_FIELD_MAPPINGS)
        payload, _ = engine.apply(SAMPLE_SOURCE_RECORD)
        assert abs(payload["discount_rate"] - 0.035) < 1e-4

    def test_constant_ignores_source(self):
        engine = MappingEngine(SAMPLE_FIELD_MAPPINGS)
        payload, _ = engine.apply(SAMPLE_SOURCE_RECORD)
        assert payload["currency"] == "USD"

    def test_empty_mapping_list(self):
        engine = MappingEngine([])
        payload, warnings = engine.apply(SAMPLE_SOURCE_RECORD)
        assert payload == {}
        assert warnings == []

    def test_apply_batch(self):
        records = [SAMPLE_SOURCE_RECORD, SAMPLE_SOURCE_RECORD]
        engine = MappingEngine(SAMPLE_FIELD_MAPPINGS)
        results = engine.apply_batch(records)
        assert len(results) == 2
        for payload, warnings, error in results:
            assert error is None
            assert "name" in payload


# ──────────────────────────────────────────────
# Nested value helpers
# ──────────────────────────────────────────────


class TestNestedValueHelpers:
    def test_get_top_level(self):
        d = {"a": 1}
        assert _get_nested_value(d, "a") == 1

    def test_get_nested(self):
        d = {"a": {"b": {"c": 42}}}
        assert _get_nested_value(d, "a.b.c") == 42

    def test_get_missing_returns_none(self):
        assert _get_nested_value({}, "x.y") is None

    def test_set_top_level(self):
        d = {}
        _set_nested_value(d, "a", 1)
        assert d["a"] == 1

    def test_set_nested_creates_dicts(self):
        d = {}
        _set_nested_value(d, "a.b.c", 42)
        assert d["a"]["b"]["c"] == 42


# ──────────────────────────────────────────────
# Validator tests
# ──────────────────────────────────────────────


class TestValidatePayload:
    SCHEMA_FIELDS = [
        {"name": "name", "type": "string", "required": True, "max_length": 255},
        {"name": "lease_type", "type": "string", "required": True, "enum": ["operating", "finance"]},
        {"name": "commencement_date", "type": "string", "format": "date", "required": True},
        {"name": "expiration_date", "type": "string", "format": "date", "required": True},
        {"name": "monthly_payment", "type": "number", "required": False},
        {"name": "discount_rate", "type": "number", "required": False},
    ]

    def test_valid_payload(self):
        payload = {
            "name": "Test Lease",
            "lease_type": "operating",
            "commencement_date": "2020-01-01",
            "expiration_date": "2025-12-31",
        }
        is_valid, errors = validate_payload(payload, self.SCHEMA_FIELDS)
        assert is_valid
        assert errors == []

    def test_missing_required_field(self):
        payload = {
            "name": "Test Lease",
            "lease_type": "operating",
            # missing commencement_date and expiration_date
        }
        is_valid, errors = validate_payload(payload, self.SCHEMA_FIELDS)
        assert not is_valid
        error_fields = [e.field for e in errors]
        assert "commencement_date" in error_fields
        assert "expiration_date" in error_fields

    def test_invalid_enum(self):
        payload = {
            "name": "Test",
            "lease_type": "invalid_type",
            "commencement_date": "2020-01-01",
            "expiration_date": "2025-12-31",
        }
        is_valid, errors = validate_payload(payload, self.SCHEMA_FIELDS)
        assert not is_valid
        assert any(e.field == "lease_type" for e in errors)

    def test_invalid_date_format(self):
        payload = {
            "name": "Test",
            "lease_type": "operating",
            "commencement_date": "01/01/2020",  # wrong format
            "expiration_date": "2025-12-31",
        }
        is_valid, errors = validate_payload(payload, self.SCHEMA_FIELDS)
        assert not is_valid

    def test_max_length_violation(self):
        payload = {
            "name": "A" * 300,  # exceeds 255
            "lease_type": "operating",
            "commencement_date": "2020-01-01",
            "expiration_date": "2025-12-31",
        }
        is_valid, errors = validate_payload(payload, self.SCHEMA_FIELDS)
        assert not is_valid
        assert any(e.field == "name" for e in errors)
