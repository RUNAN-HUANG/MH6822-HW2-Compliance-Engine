# Module 2 Test Notes

Run:

```bash
python run_compliance_check.py --input data/trades.json --regimes CFTC,EMIR
```

Expected UPI lookup checks:

| Trade | Expected result |
| --- | --- |
| T001 | `FOUND`, `Rates.Swap.Fixed_Float` |
| T005 | `FOUND`, LIBOR warning only |
| T007 | `FOUND`, XAU accepted as valid currency |
| T009 | `INVALID_ATTRIBUTES`, invalid currency |
| T026 | `NO_PRODUCT_DEFINITION` |
| T027 | `NO_PRODUCT_DEFINITION` |
| T028 | `NO_PRODUCT_DEFINITION` |

