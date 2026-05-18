# Expected Errors for Additional Trades

This file documents the expected validation outcomes for the five additional synthetic trades submitted by Wong Chun Chak. The five trades are real-world-inspired synthetic test cases and are not real transaction records.

The revised version cleans up the LEIs in T029 and T032 so that they remain clean control trades. It also cleans T031's LEI and UTI fields so that the intended error is isolated to EMIR collateral and margin reporting.

## Summary Table

| Trade | Real-world inspiration | Product | Intentional error? | Purpose | Expected final result |
| --- | --- | --- | --- | --- | --- |
| T029 | UK LDI / gilt crisis | Long-duration rates swap | No | Clean control trade | CFTC/EMIR COMPLIANT |
| T030 | Archegos TRS exposure | Equity total return swap | Yes | UTI namespace mismatch | CFTC/EMIR NONCOMPLIANT under final M3 |
| T031 | LME Nickel crisis | OTC nickel commodity swap | Yes | Missing/null EMIR collateral and margin fields | EMIR NONCOMPLIANT under final M3 |
| T032 | FX swap reporting failures | Short-dated FX swap | No | Clean high-volume FX product test | CFTC/EMIR COMPLIANT |
| T033 | Kalshi / FOMC event contract | Monetary-policy event contract | No, but classification frontier | New EventContract variant | CFTC CONDITIONAL, EMIR NOT_APPLICABLE under final M3 |

---

## T029 - LDI-style long-duration rates swap

Purpose:
- Test clean ingestion of an additional conventional derivative.
- Provide a long-duration rates hedge inspired by the UK LDI crisis narrative.
- Act as a clean control trade.

Expected:
- M1: CONVENTIONAL_DERIVATIVE
- M2: FOUND
- CFTC: COMPLIANT
- EMIR: COMPLIANT

Clean-data note:
- Both LEIs are checksum-valid.
- UTI namespace matches the reporting counterparty LEI.
- EMIR collateral and margin fields are present.
- The trade is implemented using USD-SOFR-COMPOUND to avoid accidental reference-rate codeset failure.

---

## T030 - Archegos-inspired equity total return swap with UTI namespace mismatch

Purpose:
- Test Module 3 UTI validation.
- The product, LEIs, currency fields, and margin fields are intended to be clean.
- The only intentional error is the UTI namespace mismatch.

Intentional error:
- reporting_counterparty_lei = VGRQXHF3J8VDLUA7XE92
- uti begins with 5493001KJTIIGC8Y1R12
- The UTI namespace does not match the reporting counterparty LEI.

Expected under final Module 3:
- CFTC: NONCOMPLIANT
- EMIR: NONCOMPLIANT
- Error should mention UTI namespace mismatch.

Current adapter note:
- The temporary Module 3 adapter may not catch this yet.
- Zhang Yihan's final M3 should implement this validation.

---

## T031 - LME Nickel-inspired commodity swap with missing EMIR margin fields

Purpose:
- Test jurisdiction-specific EMIR reporting logic.
- The trade should be a conventional commodity derivative.
- LEIs and UTI are intentionally clean so the failure is isolated to EMIR collateral/margin reporting.

Intentional errors:
- collateral_portfolio_code is omitted.
- initial_margin_posted is null.
- variation_margin_posted is null.

Expected under final Module 3:
- CFTC: COMPLIANT, assuming all common CFTC fields pass.
- EMIR: NONCOMPLIANT.
- Errors should mention:
  - missing collateral_portfolio_code
  - null initial_margin_posted
  - null variation_margin_posted

Important:
- A value of 0 is valid if explicitly reported.
- A null value is not valid for EMIR margin fields.
- This test case is designed so that LEI and UTI validation do not obscure the EMIR-specific failure.

Current adapter note:
- The temporary Module 3 adapter may not catch these errors yet.
- Zhang Yihan's final M3 should implement this validation.

---

## T032 - Short-dated FX swap

Purpose:
- Add clean FX swap coverage.
- Represent a high-volume product class that has historically created reporting failures.
- Act as a second clean control trade.

Expected:
- M1: CONVENTIONAL_DERIVATIVE
- M2: FOUND
- CFTC: COMPLIANT
- EMIR: COMPLIANT

Clean-data note:
- Both LEIs are checksum-valid.
- UTI namespace matches the reporting counterparty LEI.
- EMIR collateral and margin fields are present.
- This trade is intentionally clean. It is designed to check pipeline coverage, not to create a false failure.

---

## T033 - FOMC monetary-policy event contract

Purpose:
- Add a new event-contract variant beyond T026-T028.
- Test whether the engine treats monetary-policy event contracts as a taxonomy frontier.

Expected:
- M1: NOVEL_INSTRUMENT_NO_TAXONOMY
- M2: NO_PRODUCT_DEFINITION
- CFTC: CONDITIONAL if platform_type == CFTC_REGULATED_DCM
- EMIR: NOT_APPLICABLE

Clean-data note:
- LEIs are checksum-valid.
- UTI namespace matches the reporting counterparty LEI.
- UPI remains null because the instrument has no current ANNA-DSB product definition.
- The expected issue is classification/taxonomy treatment, not ordinary identifier failure.

Why this matters:
- T033 should not be treated as an ordinary malformed derivative.
- The expected issue is a taxonomy gap: the current ANNA-DSB UPI taxonomy does not contain a normal product definition for this event-contract variant.
- Final M3 should extend event-contract logic to additional EventContract records such as T033, not only hard-code T026-T028.

Current adapter note:
- The temporary Module 3 adapter may only hard-code T026-T028.
- Zhang Yihan's final M3 should implement generic EventContract handling.
