"""Command-line entry point for the MH6822 homework 2 compliance engine."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.module1_parser import load_trades, parse_all_trades
from src.module2_upi_lookup import lookup_all_upi
from src.module3_compliance import run_compliance_checks
from src.report_writer import build_report_record


DEFAULT_OUTPUT = Path("outputs") / "compliance_report.json"


def _resolve_input_path(path: str) -> Path:
    """Resolve the input path while supporting the assignment's root command."""

    candidate = Path(path)
    if candidate.exists():
        return candidate

    data_candidate = Path("data") / path
    if data_candidate.exists():
        return data_candidate

    raise FileNotFoundError(f"Could not find input file: {path}")


def _load_additional_trades(path: Path | None) -> list[dict[str, Any]]:
    """Load optional additional trades; a missing file simply means none yet."""

    if path is None or not path.exists():
        return []
    return load_trades(path)


def _parse_regimes(value: str) -> list[str]:
    """Parse a comma-separated regime list from the command line."""

    regimes = [item.strip().upper() for item in value.split(",") if item.strip()]
    if not regimes:
        raise ValueError("At least one regime must be provided")
    return regimes


def run_pipeline(
    input_path: Path,
    regimes: list[str],
    output_path: Path = DEFAULT_OUTPUT,
    additional_path: Path | None = Path("data") / "additional_trades.json",
) -> list[dict[str, Any]]:
    """Run M1 -> M2 -> M3 and write the combined JSON report."""

    provided_raw_trades = load_trades(input_path)
    additional_raw_trades = _load_additional_trades(additional_path)

    parsed_trades = parse_all_trades(provided_raw_trades, source="provided")
    parsed_trades.extend(parse_all_trades(additional_raw_trades, source="additional"))

    upi_results = lookup_all_upi(parsed_trades)

    report_rows: list[dict[str, Any]] = []
    for parsed_trade, upi_result in zip(parsed_trades, upi_results, strict=True):
        regime_results = run_compliance_checks(
            parsed_trade=parsed_trade,
            upi_result=upi_result,
            raw_trade=parsed_trade.raw_trade,
            regimes=regimes,
        )
        report_rows.append(build_report_record(parsed_trade, upi_result, regime_results))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report_rows, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    return report_rows


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Run the MH6822 OTC derivatives compliance engine."
    )
    parser.add_argument(
        "--input",
        default="data/trades.json",
        help="Path to trades.json. The command also accepts --input trades.json.",
    )
    parser.add_argument(
        "--additional",
        default="data/additional_trades.json",
        help="Optional path to additional_trades.json.",
    )
    parser.add_argument(
        "--regimes",
        default="CFTC,EMIR",
        help="Comma-separated regimes to check, e.g. CFTC,EMIR.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Path for the generated compliance report JSON.",
    )
    return parser.parse_args()


def main() -> None:
    """CLI wrapper used by the assignment run command."""

    args = parse_args()
    input_path = _resolve_input_path(args.input)
    additional_path = Path(args.additional) if args.additional else None
    regimes = _parse_regimes(args.regimes)
    output_path = Path(args.output)

    report_rows = run_pipeline(
        input_path=input_path,
        regimes=regimes,
        output_path=output_path,
        additional_path=additional_path,
    )
    print(f"Wrote {len(report_rows)} trade records to {output_path}")


if __name__ == "__main__":
    main()

