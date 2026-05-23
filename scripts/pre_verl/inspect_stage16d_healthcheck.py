#!/usr/bin/env python
"""Inspect Stage 16D official verifier healthcheck evidence artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from repo_harness.evaluation.stage16d_healthcheck import inspect_stage16d_healthcheck


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--assert-contract-complete", action="store_true")
    parser.add_argument("--assert-official-healthcheck-complete", action="store_true")
    args = parser.parse_args()

    print(
        inspect_stage16d_healthcheck(
            args.evidence,
            assert_contract_complete=args.assert_contract_complete,
            assert_official_healthcheck_complete=args.assert_official_healthcheck_complete,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
