#!/usr/bin/env python3
import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from automation.pipeline import run_pipeline  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Playa rental market automation pipeline")
    parser.add_argument(
        "--mode",
        choices=["sample", "live", "hybrid"],
        default="sample",
        help="Data source mode to run",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report_path = run_pipeline(mode=args.mode)
    print(f"Pipeline completed in mode={args.mode}. Report generated: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
