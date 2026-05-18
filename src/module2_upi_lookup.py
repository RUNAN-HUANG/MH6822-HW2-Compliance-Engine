"""Module 2: ANNA-DSB UPI template lookup and lightweight codeset validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import re
from typing import Any

from .module1_parser import ParsedTrade


PRODUCT_DEFINITIONS_ROOT = (
    Path(__file__).resolve().parents[1] / "data" / "product_definitions"
)
UPI_ROOT = PRODUCT_DEFINITIONS_ROOT / "PROD" / "OTC-Products" / "UPI"
CODESET_ROOT = PRODUCT_DEFINITIONS_ROOT / "PROD" / "OTC-Products" / "codesets"

ASSET_CLASS_DIRECTORY = {
    "FX": "Foreign_Exchange",
    "Foreign_Exchange": "Foreign_Exchange",
    "Rates": "Rates",
    "Credit": "Credit",
    "Equity": "Equity",
    "Commodities": "Commodities",
}

USE_CASE_ALIASES = {
    ("Rates", "Swap", "CrossCurrency"): "Cross_Currency_Fixed_Float",
    ("Rates", "Swap", "OIS"): "Fixed_Float_OIS",
    ("Rates", "Swap", "Inflation"): "Inflation_Swap",
    ("Rates", "Cap_Floor", "Cap"): "CapFloor",
    ("Rates", "Option", "Cap"): "CapFloor",
    ("FX", "Forward", "Deliverable"): "Forward",
    ("FX", "Option", "Vanilla"): "Vanilla_Option",
    ("FX", "Option", "Barrier"): "Barrier_Option",
    ("FX", "Swap", "Standard"): "FX_Swap",
    ("Equity", "Option", "SingleName_Put"): "Single_Name",
    ("Equity", "Swap", "TotalReturn_SingleIndex"): "Total_Return_Swap_Single_Index",
    ("Equity", "Swap", "Variance"): "Parameter_Return_Variance_Single_Index",
    ("Equity", "Forward", "SingleName"): "Price_Return_Basic_Performance_Single_Name",
    ("Commodities", "Swap", "SingleName"): "Single_Index",
    ("Commodities", "Option", "SingleName"): "Single_Index",
}

INSTRUMENT_TYPE_ALIASES = {
    ("Rates", "Cap_Floor"): "Option",
}

CODESET_CACHE: dict[str, dict[str, Any]] = {}


@dataclass
class UpiLookupResult:
    """Normalized Module 2 output for one parsed trade."""

    trade_id: str
    status: str
    matched_template: str | None
    upi_code: str | None
    classification_note: str | None
    validation_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    template_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the UPI lookup result."""

        return asdict(self)


def _normalize_token(value: str | None) -> str:
    """Normalize tokens for filename matching while keeping semantic words."""

    if value is None:
        return ""
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")


def _canonical_parts(
    asset_class: str | None, instrument_type: str | None, use_case: str | None
) -> tuple[str | None, str | None, str | None]:
    """Map homework trade labels onto ANNA-DSB directory and filename labels."""

    if asset_class is None or instrument_type is None or use_case is None:
        return asset_class, instrument_type, use_case

    directory_asset_class = ASSET_CLASS_DIRECTORY.get(asset_class, asset_class)
    canonical_instrument = INSTRUMENT_TYPE_ALIASES.get(
        (asset_class, instrument_type), instrument_type
    )
    canonical_use_case = USE_CASE_ALIASES.get(
        (asset_class, instrument_type, use_case), use_case
    )

    return (
        _normalize_token(directory_asset_class),
        _normalize_token(canonical_instrument),
        _normalize_token(canonical_use_case),
    )


def _read_json(path: Path) -> dict[str, Any]:
    """Read a UTF-8 JSON file."""

    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _template_name_from_path(path: Path) -> str:
    """Convert a template path to the shared template name format."""

    parts = path.name.split(".")
    if parts[0] == "Request":
        parts = parts[1:]
    try:
        upi_index = parts.index("UPI")
        parts = parts[:upi_index]
    except ValueError:
        parts = parts[:3]
    if parts[0] == "Foreign_Exchange":
        parts[0] = "FX"
    return ".".join(parts[:3])


def find_product_template(
    asset_class: str | None, instrument_type: str | None, use_case: str | None
) -> dict[str, Any] | None:
    """Search the ANNA-DSB product definition library for a matching template."""

    canonical_asset, canonical_instrument, canonical_use_case = _canonical_parts(
        asset_class, instrument_type, use_case
    )
    if not canonical_asset or not canonical_instrument or not canonical_use_case:
        return None

    asset_dir = UPI_ROOT / canonical_asset
    if not asset_dir.exists():
        return None

    exact_name = f"{canonical_asset}.{canonical_instrument}.{canonical_use_case}.UPI.V1.json"
    exact_path = asset_dir / exact_name
    if exact_path.exists():
        template = _read_json(exact_path)
        template["_template_path"] = str(exact_path)
        template["_matched_template"] = _template_name_from_path(exact_path)
        return template

    # Fall back to matching all semantic tokens in the filename. Prefer record
    # templates over request templates and the lowest version number for stability.
    required_tokens = [canonical_asset, canonical_instrument, canonical_use_case]
    candidates: list[Path] = []
    for path in asset_dir.glob("*.json"):
        if path.name.startswith("Request."):
            continue
        normalized_name = _normalize_token(path.stem).lower()
        if all(token.lower() in normalized_name for token in required_tokens):
            candidates.append(path)

    if not candidates:
        return None

    chosen = sorted(candidates, key=lambda p: (p.name.count(".V"), p.name))[0]
    template = _read_json(chosen)
    template["_template_path"] = str(chosen)
    template["_matched_template"] = _template_name_from_path(chosen)
    return template


def load_codeset(codeset_name: str) -> dict[str, Any]:
    """Load and cache an ANNA-DSB codeset file."""

    if codeset_name not in CODESET_CACHE:
        CODESET_CACHE[codeset_name] = _read_json(CODESET_ROOT / f"{codeset_name}.json")
    return CODESET_CACHE[codeset_name]


def _codeset_values(codeset_name: str) -> set[str]:
    """Return the enum values from a codeset file."""

    payload = load_codeset(codeset_name)
    return set(payload.get("enum", []))


def _codeset_name_from_ref(ref: str | None) -> str | None:
    """Extract a local codeset name from a JSON schema $ref value."""

    if not ref:
        return None
    return Path(ref).stem


def _template_attribute_schema(template: dict[str, Any], attribute: str) -> dict[str, Any] | None:
    """Return the schema block for a named template attribute, if present."""

    return (
        template.get("properties", {})
        .get("Attributes", {})
        .get("properties", {})
        .get(attribute)
    )


def _validate_codeset_value(
    value: Any,
    codeset_name: str,
    field_name: str,
    errors: list[str],
    warnings: list[str],
    *,
    allow_libor_warning: bool = False,
) -> None:
    """Validate a single value against a codeset enum and add clear messages."""

    if value is None:
        return

    text_value = str(value)
    if allow_libor_warning and "LIBOR" in text_value.upper():
        warnings.append(
            f"{field_name}={text_value!r} contains LIBOR; treated as legacy warning, not a hard error"
        )
        return

    if text_value not in _codeset_values(codeset_name):
        errors.append(f"{field_name}={text_value!r} is not in codeset {codeset_name}")


def _validate_enum_value(
    value: Any, allowed: list[Any], field_name: str, errors: list[str]
) -> None:
    """Validate a value against an inline enum."""

    if value is None:
        return
    if value not in allowed:
        errors.append(f"{field_name}={value!r} is not one of {allowed}")


def _currency_fields(raw_trade: dict[str, Any]) -> list[tuple[str, Any]]:
    """Return all currency-like fields available on a raw trade."""

    fields = [
        "notional_currency",
        "notional_currency_leg1",
        "notional_currency_leg2",
        "settlement_currency",
    ]
    pairs = [(field, raw_trade.get(field)) for field in fields if raw_trade.get(field) is not None]

    pair = raw_trade.get("underlying_currency_pair")
    if isinstance(pair, str) and "/" in pair:
        base, quote = pair.split("/", 1)
        pairs.extend(
            [
                ("underlying_currency_pair.base", base),
                ("underlying_currency_pair.quote", quote),
            ]
        )

    return pairs


def _rate_fields(raw_trade: dict[str, Any]) -> list[tuple[str, Any]]:
    """Return all interest-rate fields available on a raw trade."""

    fields = ["reference_rate", "reference_rate_leg1", "reference_rate_leg2"]
    return [(field, raw_trade.get(field)) for field in fields if raw_trade.get(field) is not None]


def _codeset_for_rate_field(template: dict[str, Any], field_name: str) -> str:
    """Return the template-specific codeset used by a raw reference-rate field."""

    template_attribute_names = {
        "reference_rate": ("ReferenceRate", "UnderlierID"),
        "reference_rate_leg1": ("ReferenceRate", "FirstLegReferenceRate", "UnderlierID"),
        "reference_rate_leg2": (
            "OtherLegReferenceRate",
            "SecondLegReferenceRate",
            "OtherUnderlierID",
        ),
    }

    for attribute_name in template_attribute_names.get(field_name, ()):
        schema = _template_attribute_schema(template, attribute_name)
        codeset_name = _codeset_name_from_ref(schema.get("$ref") if schema else None)
        if codeset_name:
            return codeset_name

    return "FpmlRatesReferenceRate"


def validate_attributes(
    parsed_trade: ParsedTrade | dict[str, Any], template: dict[str, Any]
) -> tuple[list[str], list[str]]:
    """Validate trade attributes against relevant template constraints."""

    raw_trade = (
        parsed_trade.raw_trade
        if isinstance(parsed_trade, ParsedTrade)
        else parsed_trade.get("raw_trade", parsed_trade)
    )
    errors: list[str] = []
    warnings: list[str] = []

    # Currency validation is always useful for conventional products, and the
    # DSB ISOCurrencyCode codeset explicitly includes XAU for gold.
    for field_name, value in _currency_fields(raw_trade):
        _validate_codeset_value(value, "ISOCurrencyCode", field_name, errors, warnings)

    for field_name, value in _rate_fields(raw_trade):
        _validate_codeset_value(
            value,
            _codeset_for_rate_field(template, field_name),
            field_name,
            errors,
            warnings,
            allow_libor_warning=True,
        )

    debt_schema = _template_attribute_schema(template, "DebtSeniority")
    if debt_schema:
        _validate_enum_value(
            raw_trade.get("debt_seniority"),
            debt_schema.get("enum", []),
            "debt_seniority",
            errors,
        )

    for field_name in (
        "reference_rate_term_value",
        "reference_rate_term_leg1_value",
        "reference_rate_term_leg2_value",
    ):
        value = raw_trade.get(field_name)
        if value is None:
            continue
        if not isinstance(value, int):
            errors.append(f"{field_name} must be an integer")
        elif value == 0 or value < -999 or value > 999:
            errors.append(f"{field_name}={value!r} must be between -999 and 999 and not zero")

    term_unit_schema = _template_attribute_schema(template, "ReferenceRateTermUnit")
    allowed_term_units = term_unit_schema.get("enum", []) if term_unit_schema else [
        "DAYS",
        "WEEK",
        "MNTH",
        "YEAR",
    ]
    for field_name in (
        "reference_rate_term_unit",
        "reference_rate_term_leg1_unit",
        "reference_rate_term_leg2_unit",
    ):
        value = raw_trade.get(field_name)
        if value is not None:
            _validate_enum_value(value, allowed_term_units, field_name, errors)

    delivery_schema = _template_attribute_schema(template, "DeliveryType")
    if delivery_schema and raw_trade.get("delivery_type") is not None:
        _validate_enum_value(
            raw_trade.get("delivery_type"),
            delivery_schema.get("enum", []),
            "delivery_type",
            errors,
        )

    return errors, warnings


def _novel_classification_note(parsed_trade: ParsedTrade) -> str:
    """Create the structured no-definition note required for event contracts."""

    return (
        f"Instrument type {parsed_trade.instrument_type!r} under asset class "
        f"{parsed_trade.asset_class!r} has no product definition in the ANNA-DSB "
        "UPI library. This reflects the current regulatory classification of "
        "prediction and event contracts as outside the OTC derivatives taxonomy "
        "in most jurisdictions. Refer to Module 4 for classification analysis."
    )


def lookup_upi(parsed_trade: ParsedTrade) -> UpiLookupResult:
    """Run the complete UPI lookup flow for a parsed trade."""

    if parsed_trade.classification_flag == "NOVEL_INSTRUMENT_NO_TAXONOMY":
        return UpiLookupResult(
            trade_id=parsed_trade.trade_id,
            status="NO_PRODUCT_DEFINITION",
            matched_template=None,
            upi_code=None,
            classification_note=_novel_classification_note(parsed_trade),
        )

    if parsed_trade.classification_flag != "CONVENTIONAL_DERIVATIVE":
        return UpiLookupResult(
            trade_id=parsed_trade.trade_id,
            status="NOT_FOUND",
            matched_template=None,
            upi_code=None,
            classification_note="Trade could not be mapped to a conventional ANNA-DSB asset class.",
        )

    template = find_product_template(
        parsed_trade.asset_class, parsed_trade.instrument_type, parsed_trade.use_case
    )
    if template is None:
        return UpiLookupResult(
            trade_id=parsed_trade.trade_id,
            status="NOT_FOUND",
            matched_template=None,
            upi_code=None,
            classification_note=(
                "No matching ANNA-DSB template found for "
                f"{parsed_trade.asset_class}.{parsed_trade.instrument_type}.{parsed_trade.use_case}"
            ),
        )

    validation_errors, warnings = validate_attributes(parsed_trade, template)
    status = "INVALID_ATTRIBUTES" if validation_errors else "FOUND"

    # Product definition schemas do not contain an assigned UPI value for a
    # specific trade. Keep the trade-supplied UPI if present; otherwise return
    # None and rely on matched_template as the evidence of template selection.
    upi_code = parsed_trade.raw_trade.get("upi")

    return UpiLookupResult(
        trade_id=parsed_trade.trade_id,
        status=status,
        matched_template=template.get("_matched_template"),
        upi_code=upi_code,
        classification_note=None,
        validation_errors=validation_errors,
        warnings=warnings,
        template_path=template.get("_template_path"),
    )


def lookup_all_upi(parsed_trades: list[ParsedTrade]) -> list[UpiLookupResult]:
    """Run UPI lookup for every parsed trade."""

    return [lookup_upi(parsed_trade) for parsed_trade in parsed_trades]
