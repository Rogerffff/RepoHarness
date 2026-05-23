#!/usr/bin/env python
"""Build Stage 16D official verifier healthcheck evidence artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from repo_harness.evaluation.stage16d_healthcheck import build_stage16d_healthcheck_artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--gold-results", type=Path)
    parser.add_argument("--noop-results", type=Path)
    parser.add_argument("--proxy-results", type=Path)
    parser.add_argument("--stage16d0-commit", default="69da8353")
    parser.add_argument("--stage16c-commit", default="4711573c")
    args = parser.parse_args()

    result = build_stage16d_healthcheck_artifacts(
        seed_manifest_path=args.seed_manifest,
        output_dir=args.output_dir,
        gold_results_path=args.gold_results,
        noop_results_path=args.noop_results,
        proxy_results_path=args.proxy_results,
        stage16d0_commit=args.stage16d0_commit,
        stage16c_commit=args.stage16c_commit,
    )
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
