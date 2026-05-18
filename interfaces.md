# MH6822 Homework 2 Interface Contract

This document is the shared contract between Module 1, Module 2, Module 3,
the report writer, and the optional dashboard. Keep field names and enum values
stable so teammates can work independently.

## Module Ownership

| Area | Owner | Files |
| --- | --- | --- |
| Module 1 parser | Huang Runan | `src/module1_parser.py` |
| Module 2 UPI lookup | Huang Runan | `src/module2_upi_lookup.py` |
| Main pipeline and report shape | Huang Runan | `run_compliance_check.py`, `src/report_writer.py` |
| Module 3 compliance rules | Zhang Yihan | `src/module3_compliance.py` |
| Additional trades and expected errors | Wong Chun Chak | `data/additional_trades.json`, `expected_errors.md` |
| Dashboard | Ke Yuxin | `dashboard/` reading `outputs/compliance_report.json` |

## Status Enums

| Area | Allowed values |
| --- | --- |
| `classification_flag` | `CONVENTIONAL_DERIVATIVE`, `NOVEL_INSTRUMENT_NO_TAXONOMY`, `CLASSIFICATION_AMBIGUOUS` |
| `parse_status` | `SUCCESS`, `PARTIAL`, `FAILED` |
| `upi_status` | `FOUND`, `NOT_FOUND`, `INVALID_ATTRIBUTES`, `NO_PRODUCT_DEFINITION` |
| `regime_results[*].status` | `COMPLIANT`, `NONCOMPLIANT`, `CONDITIONAL`, `NOT_APPLICABLE` |
| `source` | `provided`, `additional` |
| message lists | `errors`, `warnings`, `notes` are always arrays |

## Module 1 Output

`parse_trade(raw_trade)` returns a `ParsedTrade` object with this JSON shape:

```json
{
  "trade_id": "T001",
  "source": "provided",
  "parse_status": "SUCCESS",
  "asset_class": "Rates",
  "instrument_type": "Swap",
  "use_case": "Fixed_Float",
  "classification_flag": "CONVENTIONAL_DERIVATIVE",
  "parse_errors": [],
  "classified_fields": {
    "reporting_counterparty_lei": "5493001KJTIIGC8Y1R12",
    "other_counterparty_lei": "2138002TXD6KSZ3V5X27",
    "uti": "5493001KJTIIGC8Y1R1220241219TRD00001",
    "upi": null,
    "execution_timestamp": "2024-12-19T09:35:00Z",
    "effective_date": "2024-12-21",
    "maturity_date": "2029-12-21",
    "settlement_date": null,
    "notional_currency": "USD",
    "notional_amount": 50000000,
    "cleared": true,
    "action_type": "NEW",
    "platform": "SEF",
    "platform_type": null
  }
}
```

Parsing rules:

- All input rows must produce one output row.
- Invalid timestamps and dates go into `parse_errors`; the program must not crash.
- T026, T027, and T028 must be `NOVEL_INSTRUMENT_NO_TAXONOMY`.
- Conventional asset classes are `Rates`, `Credit`, `FX`, `Equity`, and `Commodities`.

## Module 2 Output

`lookup_upi(parsed_trade)` returns a `UpiLookupResult` object with this JSON shape:

```json
{
  "trade_id": "T001",
  "status": "FOUND",
  "matched_template": "Rates.Swap.Fixed_Float",
  "upi_code": null,
  "classification_note": null,
  "validation_errors": [],
  "warnings": [],
  "template_path": "data/product_definitions/PROD/OTC-Products/UPI/Rates/Rates.Swap.Fixed_Float.UPI.V1.json"
}
```

Notes:

- The ANNA-DSB GitHub files are product definition schemas. They identify the
  matching template but do not assign a live UPI code to this homework trade.
  Therefore `upi_code` is the trade-supplied UPI when present, otherwise `null`.
- LIBOR reference rates are warnings, not hard validation errors.
- XAU is valid because it appears in `ISOCurrencyCode.json`.
- Event contracts return `NO_PRODUCT_DEFINITION` with an explanatory note.

## Module 3 Function Contract

Zhang Yihan should keep this function signature so the main pipeline does not need
to change:

```python
def run_compliance_checks(parsed_trade, upi_result, raw_trade, regimes):
    """Return a dict keyed by regime name."""
```

Expected output:

```json
{
  "CFTC": {
    "status": "COMPLIANT",
    "errors": [],
    "warnings": [],
    "notes": []
  },
  "EMIR": {
    "status": "COMPLIANT",
    "errors": [],
    "warnings": [],
    "notes": []
  }
}
```

Required T026-T028 asymmetry:

| Trade | CFTC | EMIR |
| --- | --- | --- |
| T026 | `CONDITIONAL` | `NOT_APPLICABLE` |
| T027 | `NOT_APPLICABLE` | `NOT_APPLICABLE` |
| T028 | `CONDITIONAL` | `NOT_APPLICABLE` |

## Final Report Row

`outputs/compliance_report.json` is an array of rows:

```json
{
  "trade_id": "T001",
  "source": "provided",
  "asset_class": "Rates",
  "instrument_type": "Swap",
  "use_case": "Fixed_Float",
  "classification_flag": "CONVENTIONAL_DERIVATIVE",
  "parse_status": "SUCCESS",
  "parse_errors": [],
  "matched_template": "Rates.Swap.Fixed_Float",
  "upi_status": "FOUND",
  "upi_code": null,
  "upi_errors": [],
  "upi_warnings": [],
  "classification_note": null,
  "classified_fields": {},
  "regime_results": {
    "CFTC": {"status": "COMPLIANT", "errors": [], "warnings": [], "notes": []},
    "EMIR": {"status": "COMPLIANT", "errors": [], "warnings": [], "notes": []}
  }
}
```

Dashboard code should read only `outputs/compliance_report.json` or
`outputs/sample_compliance_report.json` and should not import or modify core
engine modules.
