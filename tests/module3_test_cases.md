# Module 3 Compliance Test Cases

These cases cover the final `run_compliance_checks(parsed_trade, upi_result, raw_trade, regimes)` interface and the CFTC/EMIR rules owned by Zhang Yihan.

## Interface Contract

- `run_compliance_checks()` returns a dictionary keyed by requested regime name.
- Each regime result contains `status`, `errors`, `warnings`, and `notes`.
- `errors`, `warnings`, and `notes` are always lists, even when empty.
- Only these statuses are used: `COMPLIANT`, `NONCOMPLIANT`, `CONDITIONAL`, `NOT_APPLICABLE`.
- Unknown regimes return `NOT_APPLICABLE` without changing the CFTC/EMIR result shape.

## LEI Validation

| Case | Input | Expected Result |
| --- | --- | --- |
| Valid reporting and other counterparty LEIs | T013 | No LEI errors. |
| Invalid LEI format | T004 `other_counterparty_lei = MISSING_LEI` | Error on `other_counterparty_lei`. |
| Missing LEI | A synthetic/additional trade with either LEI missing | Error naming the missing LEI field. |
| Checksum failure | Any 20-character LEI with invalid MOD 97-10 check digits | Error saying checksum failed. |

## UTI Validation

| Case | Input | Expected Result |
| --- | --- | --- |
| Valid UTI | T001 | No UTI errors. |
| Missing UTI | T006 | Error `uti is missing`. |
| Namespace LEI mismatch | Synthetic trade where UTI first 20 chars differ from `reporting_counterparty_lei` | Error that namespace LEI must match reporting LEI. |
| Invalid namespace LEI | Synthetic trade where UTI starts with a bad 20-character LEI | Error on UTI namespace LEI. |
| Lowercase or invalid suffix | Synthetic trade with lowercase suffix after the first 20 chars | Error that suffix may contain only uppercase letters, numbers, and hyphens. |
| Length above 52 characters | Synthetic trade with a 53+ character UTI | Error that UTI must not exceed 52 characters. |

## CFTC And EMIR Required Fields

| Case | Input | Expected Result |
| --- | --- | --- |
| Complete conventional OTC trade for CFTC | T017 | CFTC can be `COMPLIANT` when LEI, UTI, basic fields, and M2 checks pass. |
| M1 parse issue preserved | T013 or T021 | Parse issue appears in `warnings`. |
| Missing basic required field | T006 missing UTI | CFTC and EMIR become `NONCOMPLIANT`. |
| Missing maturity/expiry date | Synthetic conventional trade without both fields | CFTC and EMIR error on `maturity_or_expiry_date`. |
| EMIR collateral fields present with zero values | T001/T008/T010 | Zero margin values are accepted and not treated as missing. |
| EMIR collateral fields absent or null | T003/T017 | EMIR includes missing-field errors; CFTC does not require those fields. |

## UPI Handling

| Case | Input | Expected Result |
| --- | --- | --- |
| `upi_status == FOUND` and `upi_code is null` | Most provided conventional trades | Note only; not a hard error. |
| `upi_status == INVALID_ATTRIBUTES` | T009 invalid currency through M2 | Validation errors are copied into M3 `errors`. |
| `upi_status == NOT_FOUND` or `NO_PRODUCT_DEFINITION` | Unsupported template or event product | Warning, unless the event-contract override applies. |
| M2 warnings | T005 LIBOR warning | Warning copied into both CFTC and EMIR results. |

## Event Contract Outcomes

| Trade | CFTC | EMIR | Notes |
| --- | --- | --- | --- |
| T026 | `CONDITIONAL` | `NOT_APPLICABLE` | Kalshi DCM event contract; CFTC classification is conditional, EMIR is outside scope. |
| T027 | `NOT_APPLICABLE` | `NOT_APPLICABLE` | Polymarket/offshore scenario is outside this reporting chain. |
| T028 | `CONDITIONAL` | `NOT_APPLICABLE` | Regulatory event contract; CFTC conditional, no current EMIR product classification. |
| T033 or any additional EventContract on `CFTC_REGULATED_DCM` | `CONDITIONAL` | `NOT_APPLICABLE` | Additional event-contract variant; CFTC conditional when platform type is CFTC-regulated DCM, EMIR outside scope. |

## Suggested Manual Acceptance Command

```bash
python run_compliance_check.py --input trades.json --regimes CFTC,EMIR
```

Expected acceptance checks:

- The command writes 33 records to `outputs/compliance_report.json` when `data/additional_trades.json` contains T029-T033.
- Every record has both `CFTC` and `EMIR` under `regime_results`.
- T026, T027, and T028 match the fixed status table above.
- Additional EventContract records such as T033 return CFTC `CONDITIONAL` and EMIR `NOT_APPLICABLE` when `platform_type == CFTC_REGULATED_DCM`.
- Invalid LEI/UTI/required-field cases appear in `errors`.
- M1 parse issues and M2 non-hard UPI messages are preserved in `warnings` or `notes`.
