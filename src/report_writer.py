"""Report assembly helpers for the end-to-end compliance engine."""

from __future__ import annotations

from typing import Any

from .module1_parser import ParsedTrade
from .module2_upi_lookup import UpiLookupResult


def build_report_record(
    parsed_trade: ParsedTrade,
    upi_result: UpiLookupResult,
    regime_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Combine M1, M2, and M3 outputs into one report row."""

    return {
        "trade_id": parsed_trade.trade_id,
        "source": parsed_trade.source,
        "asset_class": parsed_trade.asset_class,
        "instrument_type": parsed_trade.instrument_type,
        "use_case": parsed_trade.use_case,
        "classification_flag": parsed_trade.classification_flag,
        "parse_status": parsed_trade.parse_status,
        "parse_errors": parsed_trade.parse_errors,
        "matched_template": upi_result.matched_template,
        "upi_status": upi_result.status,
        "upi_code": upi_result.upi_code,
        "upi_errors": upi_result.validation_errors,
        "upi_warnings": upi_result.warnings,
        "classification_note": upi_result.classification_note,
        "classified_fields": parsed_trade.classified_fields,
        "regime_results": regime_results,
    }

