#!/usr/bin/env python3
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from automation.pipeline import run_pipeline  # noqa: E402


def main() -> int:
    report_path = run_pipeline()
    print(f"Pipeline completed. Report generated: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
