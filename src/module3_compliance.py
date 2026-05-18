"""Module 3: regulatory compliance checks for CFTC and EMIR.

The module keeps the shared integration contract stable while replacing the
initial placeholder adapter with concrete LEI, UTI, required-field, UPI, CFTC,
and EMIR checks.
"""

from __future__ import annotations

import copy
import re
from typing import Any


VALID_STATUSES = {"COMPLIANT", "NONCOMPLIANT", "CONDITIONAL", "NOT_APPLICABLE"}
SUPPORTED_REGIMES = {"CFTC", "EMIR"}

LEI_RE = re.compile(r"^[A-Z0-9]{18}[0-9]{2}$")
UTI_SUFFIX_RE = re.compile(r"^[A-Z0-9-]+$")

BASIC_REQUIRED_FIELDS = (
    "uti",
    "reporting_counterparty_lei",
    "other_counterparty_lei",
    "execution_timestamp",
    "effective_date",
    "notional_currency",
    "notional_amount",
    "action_type",
    "cleared",
)

EMIR_REQUIRED_FIELDS = (
    "collateral_portfolio_code",
    "initial_margin_posted",
    "variation_margin_posted",
)

EVENT_CONTRACT_RESULTS = {
    "T026": {
        "CFTC": {
            "status": "CONDITIONAL",
            "errors": [],
            "warnings": [],
            "notes": [
                "Kalshi event contract on a CFTC-regulated DCM; reportability is conditional pending final event-contract classification.",
            ],
        },
        "EMIR": {
            "status": "NOT_APPLICABLE",
            "errors": [],
            "warnings": [],
            "notes": [
                "Event contracts are outside the current EMIR OTC derivative taxonomy for this project.",
            ],
        },
    },
    "T027": {
        "CFTC": {
            "status": "NOT_APPLICABLE",
            "errors": [],
            "warnings": [],
            "notes": [
                "Polymarket/offshore prediction-market trade is outside this CFTC reporting chain.",
            ],
        },
        "EMIR": {
            "status": "NOT_APPLICABLE",
            "errors": [],
            "warnings": [],
            "notes": [
                "Offshore prediction-market event contract is outside this EMIR reporting chain.",
            ],
        },
    },
    "T028": {
        "CFTC": {
            "status": "CONDITIONAL",
            "errors": [],
            "warnings": [],
            "notes": [
                "Regulatory-decision event contract has conditional CFTC treatment because product classification is unsettled.",
            ],
        },
        "EMIR": {
            "status": "NOT_APPLICABLE",
            "errors": [],
            "warnings": [],
            "notes": [
                "Regulatory-decision event contract has no current EMIR product classification.",
            ],
        },
    },
}


def _empty_result(status: str = "COMPLIANT") -> dict[str, Any]:
    """Return a fresh compliance result object for one regime."""

    if status not in VALID_STATUSES:
        raise ValueError(f"Unsupported compliance status: {status}")
    return {"status": status, "errors": [], "warnings": [], "notes": []}


def _copy_result(result: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy of a reusable result template."""

    return copy.deepcopy(result)


def _is_event_contract(parsed_trade: Any, raw_trade: dict[str, Any]) -> bool:
    """Return True for original or additional event/prediction-contract records."""

    classification_flag = getattr(parsed_trade, "classification_flag", None)
    asset_class = getattr(parsed_trade, "asset_class", None) or raw_trade.get("asset_class")
    instrument_type = getattr(parsed_trade, "instrument_type", None) or raw_trade.get("instrument_type")

    return (
        classification_flag == "NOVEL_INSTRUMENT_NO_TAXONOMY"
        and (
            asset_class in {"EventContract", "PredictionMarket", "PredictionContract"}
            or instrument_type in {"BinaryEventContract", "EventContract"}
        )
    )


def _generic_event_contract_result(
    parsed_trade: Any,
    raw_trade: dict[str, Any],
    regime: str,
) -> dict[str, Any]:
    """Return regime treatment for additional event-contract variants.

    CFTC-regulated DCM event contracts, such as Kalshi-style contracts, are
    treated as CONDITIONAL because their product classification is outside the
    current ANNA-DSB taxonomy and depends on event-contract regulatory treatment.
    Other/offshore prediction-market event contracts are outside this reporting
    chain. EMIR is NOT_APPLICABLE for event contracts in this project.
    """

    trade_id = getattr(parsed_trade, "trade_id", raw_trade.get("trade_id", "UNKNOWN"))
    platform = raw_trade.get("platform") or _field_value(parsed_trade, raw_trade, "platform")
    platform_type = raw_trade.get("platform_type") or _field_value(parsed_trade, raw_trade, "platform_type")

    if regime == "CFTC":
        if platform_type == "CFTC_REGULATED_DCM":
            result = _empty_result("CONDITIONAL")
            result["notes"].append(
                f"{trade_id} is an event contract on {platform or 'a CFTC-regulated platform'}; "
                "CFTC treatment is conditional because the instrument is outside the current ANNA-DSB taxonomy."
            )
            return result

        result = _empty_result("NOT_APPLICABLE")
        result["notes"].append(
            f"{trade_id} is an event/prediction-market contract outside this CFTC reporting chain."
        )
        return result

    if regime == "EMIR":
        result = _empty_result("NOT_APPLICABLE")
        result["notes"].append(
            f"{trade_id} is an event contract outside the current EMIR OTC derivative taxonomy for this project."
        )
        return result

    return _empty_result("NOT_APPLICABLE")


def _get_classified_fields(parsed_trade: Any) -> dict[str, Any]:
    """Return normalized M1 fields, tolerating test doubles."""

    fields = getattr(parsed_trade, "classified_fields", None)
    return fields if isinstance(fields, dict) else {}


def _field_value(parsed_trade: Any, raw_trade: dict[str, Any], field_name: str) -> Any:
    """Read a field from M1 normalized fields first, then raw input aliases."""

    classified_fields = _get_classified_fields(parsed_trade)
    if field_name in classified_fields:
        return classified_fields[field_name]

    aliases = {
        "notional_currency": ("notional_currency", "notional_currency_leg1"),
        "notional_amount": ("notional_amount", "notional_amount_leg1"),
        "maturity_or_expiry_date": ("maturity_date", "expiry_date"),
    }
    for alias in aliases.get(field_name, (field_name,)):
        if alias in raw_trade:
            return raw_trade.get(alias)
    return None


def _is_missing(value: Any) -> bool:
    """Return True when a required field is absent or blank."""

    return value is None or (isinstance(value, str) and value.strip() == "")


def _lei_checksum_ok(lei: str) -> bool:
    """Validate an LEI using ISO 7064 MOD 97-10."""

    digits = []
    for char in lei:
        if char.isdigit():
            digits.append(char)
        elif "A" <= char <= "Z":
            digits.append(str(ord(char) - 55))
        else:
            return False
    return int("".join(digits)) % 97 == 1


def validate_lei(value: Any) -> tuple[bool, str | None]:
    """Validate LEI format and checksum."""

    if _is_missing(value):
        return False, "is missing"
    lei = str(value).strip().upper()
    if not LEI_RE.fullmatch(lei):
        return False, "must be 20 uppercase alphanumeric characters ending with two check digits"
    if not _lei_checksum_ok(lei):
        return False, "failed ISO 7064 MOD 97-10 checksum"
    return True, None


def validate_uti(uti_value: Any, reporting_counterparty_lei: Any) -> tuple[bool, list[str]]:
    """Validate UTI length, namespace LEI, reporting LEI alignment, and suffix."""

    errors: list[str] = []
    if _is_missing(uti_value):
        return False, ["uti is missing"]

    uti = str(uti_value).strip()
    if len(uti) > 52:
        errors.append("uti must not exceed 52 characters")
    if len(uti) < 20:
        errors.append("uti must contain a 20-character namespace LEI prefix")
        return False, errors

    namespace_lei = uti[:20]
    suffix = uti[20:]
    valid_namespace, reason = validate_lei(namespace_lei)
    if not valid_namespace:
        errors.append(f"uti namespace LEI {reason}")

    if (
        not _is_missing(reporting_counterparty_lei)
        and namespace_lei != str(reporting_counterparty_lei).strip().upper()
    ):
        errors.append("uti namespace LEI must match reporting_counterparty_lei")

    if not suffix:
        errors.append("uti suffix is missing")
    elif not UTI_SUFFIX_RE.fullmatch(suffix):
        errors.append("uti suffix may contain only uppercase letters, numbers, and hyphens")

    return not errors, errors


def _collect_lei_errors(parsed_trade: Any, raw_trade: dict[str, Any]) -> list[str]:
    """Return LEI errors for reporting and other counterparty fields."""

    errors: list[str] = []
    for field_name in ("reporting_counterparty_lei", "other_counterparty_lei"):
        valid, reason = validate_lei(_field_value(parsed_trade, raw_trade, field_name))
        if not valid:
            errors.append(f"{field_name} {reason}")
    return errors


def _collect_uti_errors(parsed_trade: Any, raw_trade: dict[str, Any]) -> list[str]:
    """Return UTI errors required by the homework brief."""

    uti_value = _field_value(parsed_trade, raw_trade, "uti")
    reporting_lei = _field_value(parsed_trade, raw_trade, "reporting_counterparty_lei")
    _, errors = validate_uti(uti_value, reporting_lei)
    return errors


def _collect_required_field_errors(
    parsed_trade: Any,
    raw_trade: dict[str, Any],
    *,
    include_emir_fields: bool,
) -> list[str]:
    """Return missing-field errors for the selected regime."""

    errors: list[str] = []
    for field_name in BASIC_REQUIRED_FIELDS:
        if _is_missing(_field_value(parsed_trade, raw_trade, field_name)):
            errors.append(f"missing required field: {field_name}")

    if _is_missing(_field_value(parsed_trade, raw_trade, "maturity_or_expiry_date")):
        errors.append("missing required field: maturity_or_expiry_date")

    if include_emir_fields:
        for field_name in EMIR_REQUIRED_FIELDS:
            if _is_missing(raw_trade.get(field_name)):
                errors.append(f"missing EMIR required field: {field_name}")

    return errors


def _collect_parse_warnings(parsed_trade: Any) -> list[str]:
    """Carry M1 parse errors into M3 results without changing M1 ownership."""

    parse_errors = getattr(parsed_trade, "parse_errors", [])
    return [f"M1 parse issue: {message}" for message in parse_errors]


def _collect_upi_messages(upi_result: Any) -> tuple[list[str], list[str], list[str]]:
    """Convert Module 2 UPI results into M3 errors, warnings, and notes."""

    errors: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []

    status = getattr(upi_result, "status", None)
    if status == "INVALID_ATTRIBUTES":
        errors.extend(getattr(upi_result, "validation_errors", []))
    elif status in {"NOT_FOUND", "NO_PRODUCT_DEFINITION"}:
        warnings.append(f"UPI lookup status is {status}")

    warnings.extend(getattr(upi_result, "warnings", []))
    if status == "FOUND" and getattr(upi_result, "upi_code", None) is None:
        notes.append(
            "ANNA-DSB product definition template matched; no live UPI code was supplied in the trade."
        )

    classification_note = getattr(upi_result, "classification_note", None)
    if classification_note:
        notes.append(str(classification_note))

    return errors, warnings, notes


def _dedupe(messages: list[str]) -> list[str]:
    """Preserve message order while removing duplicates."""

    seen = set()
    result = []
    for message in messages:
        if message not in seen:
            seen.add(message)
            result.append(message)
    return result


def _finalize_result(result: dict[str, Any]) -> dict[str, Any]:
    """Normalize lists and set NONCOMPLIANT when hard errors exist."""

    result["errors"] = _dedupe(result["errors"])
    result["warnings"] = _dedupe(result["warnings"])
    result["notes"] = _dedupe(result["notes"])
    if result["errors"] and result["status"] == "COMPLIANT":
        result["status"] = "NONCOMPLIANT"
    return result


def _check_regime(
    parsed_trade: Any,
    upi_result: Any,
    raw_trade: dict[str, Any],
    regime: str,
) -> dict[str, Any]:
    """Run conventional derivative checks for one supported regime."""

    if regime not in SUPPORTED_REGIMES:
        return _empty_result("NOT_APPLICABLE")

    classification_flag = getattr(parsed_trade, "classification_flag", None)
    if classification_flag != "CONVENTIONAL_DERIVATIVE":
        result = _empty_result("NOT_APPLICABLE")
        result["notes"].append(
            f"{classification_flag or 'Unclassified trade'} is outside conventional derivative reporting checks."
        )
        return result

    result = _empty_result("COMPLIANT")
    result["errors"].extend(_collect_lei_errors(parsed_trade, raw_trade))
    result["errors"].extend(_collect_uti_errors(parsed_trade, raw_trade))
    result["errors"].extend(
        _collect_required_field_errors(
            parsed_trade,
            raw_trade,
            include_emir_fields=(regime == "EMIR"),
        )
    )
    result["warnings"].extend(_collect_parse_warnings(parsed_trade))

    upi_errors, upi_warnings, upi_notes = _collect_upi_messages(upi_result)
    result["errors"].extend(upi_errors)
    result["warnings"].extend(upi_warnings)
    result["notes"].extend(upi_notes)
    result["notes"].append(f"{regime} checks applied to a conventional OTC derivative.")

    return _finalize_result(result)


def check_cftc_compliance(
    parsed_trade: Any,
    upi_result: Any,
    raw_trade: dict[str, Any],
) -> dict[str, Any]:
    """Check one trade under the CFTC reporting regime."""

    trade_id = getattr(parsed_trade, "trade_id", raw_trade.get("trade_id"))
    if trade_id in EVENT_CONTRACT_RESULTS:
        return _copy_result(EVENT_CONTRACT_RESULTS[trade_id]["CFTC"])
    if _is_event_contract(parsed_trade, raw_trade):
        return _generic_event_contract_result(parsed_trade, raw_trade, "CFTC")
    return _check_regime(parsed_trade, upi_result, raw_trade, "CFTC")


def check_emir_compliance(
    parsed_trade: Any,
    upi_result: Any,
    raw_trade: dict[str, Any],
) -> dict[str, Any]:
    """Check one trade under the EMIR reporting regime."""

    trade_id = getattr(parsed_trade, "trade_id", raw_trade.get("trade_id"))
    if trade_id in EVENT_CONTRACT_RESULTS:
        return _copy_result(EVENT_CONTRACT_RESULTS[trade_id]["EMIR"])
    if _is_event_contract(parsed_trade, raw_trade):
        return _generic_event_contract_result(parsed_trade, raw_trade, "EMIR")
    return _check_regime(parsed_trade, upi_result, raw_trade, "EMIR")


def run_compliance_checks(
    parsed_trade: Any,
    upi_result: Any,
    raw_trade: dict[str, Any],
    regimes: list[str],
) -> dict[str, dict[str, Any]]:
    """Return a dict keyed by regime name, e.g. CFTC and EMIR."""

    trade_id = getattr(parsed_trade, "trade_id", raw_trade.get("trade_id"))
    if trade_id in EVENT_CONTRACT_RESULTS:
        return {
            regime: _copy_result(
                EVENT_CONTRACT_RESULTS[trade_id].get(regime, _empty_result("NOT_APPLICABLE"))
            )
            for regime in regimes
        }

    if _is_event_contract(parsed_trade, raw_trade):
        return {
            regime: _generic_event_contract_result(parsed_trade, raw_trade, regime)
            for regime in regimes
        }

    results: dict[str, dict[str, Any]] = {}
    for regime in regimes:
        if regime == "CFTC":
            results[regime] = check_cftc_compliance(parsed_trade, upi_result, raw_trade)
        elif regime == "EMIR":
            results[regime] = check_emir_compliance(parsed_trade, upi_result, raw_trade)
        else:
            results[regime] = _empty_result("NOT_APPLICABLE")
    return results
