# MH6822 Homework 2 Compliance Engine

This repository implements the main pipeline for the OTC derivatives reporting
and classification-frontier homework: trade parsing, ANNA-DSB template lookup,
and a stable adapter for the Module 3 compliance checker.

## Repository Structure

| Path | Purpose |
| --- | --- |
| `trades.json` | Root copy of the provided 28-trade portfolio for the assignment command. |
| `data/trades.json` | Working copy of the provided portfolio. |
| `data/additional_trades.json` | Wong Chun Chak's five additional synthetic trades. |
| `data/product_definitions/` | Copy of the ANNA-DSB Product Definitions repository used by Module 2. |
| `src/module1_parser.py` | Module 1 parser and instrument classifier. |
| `src/module2_upi_lookup.py` | Module 2 product-template lookup and codeset validation. |
| `src/module3_compliance.py` | Module 3 CFTC/EMIR compliance checks contributed by Zhang Yihan. |
| `src/report_writer.py` | Combines M1, M2, and M3 outputs into report rows. |
| `outputs/compliance_report.json` | Generated end-to-end report. |
| `interfaces.md` | Shared field names, enums, and function contracts. |

## Installation

```bash
pip install -r requirements.txt
```

The current Huang Runan modules use only the Python standard library, but the
requirements file includes the expected libraries for Zhang Yihan and Ke Yuxin.

## Data Setup

The ANNA-DSB product definitions are already present in `data/product_definitions`.
If another teammate checks out a copy without that folder, run:

```bash
git clone https://github.com/ANNA-DSB/Product-Definitions.git data/product_definitions
```

## Run the Engine

Both assignment-style and data-folder commands are supported:

```bash
python run_compliance_check.py --input trades.json --regimes CFTC,EMIR
```

```bash
python run_compliance_check.py --input data/trades.json --regimes CFTC,EMIR
```

The generated file is:

```text
outputs/compliance_report.json
```

## Generate the Dashboard

```bash
python dashboard/dashboard.py
```

or, equivalently:

```bash
python dashboard/dashboard.py --input outputs/compliance_report.json
```

The generated dashboard is:

```text
dashboard/dashboard.html
```

Optional arguments:

```bash
python run_compliance_check.py \
  --input data/trades.json \
  --additional data/additional_trades.json \
  --regimes CFTC,EMIR \
  --output outputs/compliance_report.json
```

## Current Integration Notes

- Module 1 parses every provided trade without crashing.
- T026, T027, and T028 are classified as `NOVEL_INSTRUMENT_NO_TAXONOMY`.
- Module 2 returns `NO_PRODUCT_DEFINITION` for event contracts.
- LIBOR reference rates are warnings, not hard errors.
- XAU passes currency validation through the ANNA-DSB `ISOCurrencyCode` codeset.
- Module 3 now includes LEI, UTI, required-field, CFTC, EMIR, and event-contract checks.
- Wong Chun Chak's additional trades T029-T033 are included automatically when
  `data/additional_trades.json` is present.

## Team Members

| Name | Matriculation Number |
| --- | --- |
| Huang Runan | G2505368A |
| Zhang Yihan | G2506177A |
| Wong Chun Chak | G2505639K |
| Ke Yuxin | G2505405B |

## Team Contributions

- Huang Runan: Module 1, Module 2, main pipeline, interface contract, README, and report integration.
- Zhang Yihan: Module 3 compliance rules, LEI validation, UTI validation, CFTC and EMIR checks.
- Wong Chun Chak: Module 4 written analysis, additional trades, expected error documentation, and written report integration.
- Ke Yuxin: Bonus dashboard reading `outputs/compliance_report.json` and support for written report integration.

## Presentation Link

Recording: https://drive.google.com/file/d/1fL-mIGZe3XFOqaIiUTGqyPSwSyWv1Njn/view?usp=sharing
