# Module 1 Test Notes

Run:

```bash
python run_compliance_check.py --input data/trades.json --regimes CFTC,EMIR
```

Expected parser checks:

| Trade | Expected result |
| --- | --- |
| T001 | `SUCCESS`, `CONVENTIONAL_DERIVATIVE` |
| T013 | `PARTIAL`, invalid `execution_timestamp` warning |
| T021 | `PARTIAL`, invalid `maturity_date` warning |
| T026 | `SUCCESS`, `NOVEL_INSTRUMENT_NO_TAXONOMY` |
| T027 | `SUCCESS`, `NOVEL_INSTRUMENT_NO_TAXONOMY` |
| T028 | `SUCCESS`, `NOVEL_INSTRUMENT_NO_TAXONOMY` |

