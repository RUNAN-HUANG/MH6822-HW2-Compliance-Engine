"""Module 1: trade parsing and instrument classification.

This module intentionally avoids raising exceptions for malformed trade rows.
Every input row should produce a ParsedTrade object so downstream modules can
show a complete compliance picture instead of silently dropping bad data.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any


CONVENTIONAL_ASSET_CLASSES = {
    "Rates",
    "Credit",
    "FX",
    "Foreign_Exchange",
    "Equity",
    "Commodities",
}

NOVEL_ASSET_CLASSES = {
    "EventContract",
    "PredictionMarket",
    "PredictionContract",
}

ISO_8601_UTC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)


@dataclass
class ParsedTrade:
    """Normalized Module 1 output for one raw trade record."""

    trade_id: str
    parse_status: str
    asset_class: str | None
    instrument_type: str | None
    use_case: str | None
    classification_flag: str
    parse_errors: list[str] = field(default_factory=list)
    classified_fields: dict[str, Any] = field(default_factory=dict)
    raw_trade: dict[str, Any] = field(default_factory=dict, repr=False)
    source: str = "provided"

    def to_dict(self, include_raw: bool = False) -> dict[str, Any]:
        """Return a JSON-serializable representation of this parsed trade."""

        data = asdict(self)
        if not include_raw:
            data.pop("raw_trade", None)
        return data


def load_trades(path: str | Path) -> list[dict[str, Any]]:
    """Load a JSON list of trade dictionaries from disk."""

    input_path = Path(path)
    with input_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, list):
        raise ValueError(f"{input_path} must contain a JSON array of trades")

    return payload


def classify_instrument(trade: dict[str, Any]) -> str:
    """Determine the regulatory taxonomy classification flag for a trade."""

    trade_id = trade.get("trade_id")
    asset_class = trade.get("asset_class")

    if trade_id in {"T026", "T027", "T028"}:
        return "NOVEL_INSTRUMENT_NO_TAXONOMY"
    if asset_class in NOVEL_ASSET_CLASSES:
        return "NOVEL_INSTRUMENT_NO_TAXONOMY"
    if asset_class in CONVENTIONAL_ASSET_CLASSES:
        return "CONVENTIONAL_DERIVATIVE"

    return "CLASSIFICATION_AMBIGUOUS"


def is_valid_utc_timestamp(value: Any) -> bool:
    """Return True when value is an ISO 8601 UTC timestamp ending in Z."""

    if not isinstance(value, str) or not ISO_8601_UTC_RE.match(value):
        return False

    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def is_valid_date(value: Any) -> bool:
    """Return True when value is a real calendar date in YYYY-MM-DD format."""

    if not isinstance(value, str):
        return False

    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _first_present(trade: dict[str, Any], names: list[str]) -> Any:
    """Return the first non-null value from a list of possible raw field names."""

    for name in names:
        value = trade.get(name)
        if value is not None:
            return value
    return None


def _extract_classified_fields(trade: dict[str, Any]) -> dict[str, Any]:
    """Collect fields commonly needed by UPI lookup, M3 checks, and dashboarding."""

    return {
        "reporting_counterparty_lei": trade.get("reporting_counterparty_lei"),
        "other_counterparty_lei": trade.get("other_counterparty_lei"),
        "uti": trade.get("uti"),
        "upi": trade.get("upi"),
        "execution_timestamp": trade.get("execution_timestamp"),
        "effective_date": trade.get("effective_date"),
        "maturity_date": trade.get("maturity_date"),
        "settlement_date": trade.get("settlement_date"),
        "notional_currency": _first_present(
            trade, ["notional_currency", "notional_currency_leg1"]
        ),
        "notional_amount": _first_present(
            trade, ["notional_amount", "notional_amount_leg1"]
        ),
        "cleared": trade.get("cleared"),
        "action_type": trade.get("action_type"),
        "platform": trade.get("platform"),
        "platform_type": trade.get("platform_type"),
    }


def parse_trade(trade: dict[str, Any], source: str = "provided") -> ParsedTrade:
    """Parse a single raw trade dict into the shared Module 1 format."""

    if not isinstance(trade, dict):
        return ParsedTrade(
            trade_id="UNKNOWN",
            parse_status="FAILED",
            asset_class=None,
            instrument_type=None,
            use_case=None,
            classification_flag="CLASSIFICATION_AMBIGUOUS",
            parse_errors=["raw trade is not a JSON object"],
            classified_fields={},
            raw_trade={},
            source=source,
        )

    errors: list[str] = []
    trade_id = trade.get("trade_id")
    asset_class = trade.get("asset_class")
    instrument_type = trade.get("instrument_type")
    use_case = trade.get("use_case")

    if not trade_id:
        errors.append("missing required field: trade_id")
        trade_id = "UNKNOWN"
    if asset_class is None:
        errors.append("missing required field: asset_class")
    if instrument_type is None:
        errors.append("missing required field: instrument_type")
    if use_case is None:
        errors.append("missing required field: use_case")

    classification_flag = classify_instrument(trade)
    if classification_flag == "CLASSIFICATION_AMBIGUOUS":
        errors.append(
            f"cannot classify asset_class={asset_class!r}, "
            f"instrument_type={instrument_type!r}, use_case={use_case!r}"
        )

    if not is_valid_utc_timestamp(trade.get("execution_timestamp")):
        errors.append("execution_timestamp must be ISO 8601 UTC, e.g. 2025-01-01T09:00:00Z")

    for date_field in ("effective_date", "maturity_date"):
        value = trade.get(date_field)
        if value is not None and not is_valid_date(value):
            errors.append(f"{date_field} must be a valid YYYY-MM-DD date")

    # Event contracts use settlement_date instead of effective/maturity dates.
    if classification_flag == "NOVEL_INSTRUMENT_NO_TAXONOMY":
        settlement_date = trade.get("settlement_date")
        if settlement_date is not None and not is_valid_date(settlement_date):
            errors.append("settlement_date must be a valid YYYY-MM-DD date")

    parse_status = "SUCCESS"
    if errors:
        parse_status = "FAILED" if not asset_class or not instrument_type or not use_case else "PARTIAL"

    return ParsedTrade(
        trade_id=str(trade_id),
        parse_status=parse_status,
        asset_class=asset_class,
        instrument_type=instrument_type,
        use_case=use_case,
        classification_flag=classification_flag,
        parse_errors=errors,
        classified_fields=_extract_classified_fields(trade),
        raw_trade=trade,
        source=source,
    )


def parse_all_trades(
    trades: list[dict[str, Any]], source: str = "provided"
) -> list[ParsedTrade]:
    """Parse a list of trades while preserving the input order."""

    return [parse_trade(trade, source=source) for trade in trades]

