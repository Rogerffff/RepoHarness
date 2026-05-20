#!/usr/bin/env python
"""Build Stage 15.1 local acceptance evidence."""

from __future__ import annotations

import argparse
from pathlib import Path

from repo_harness_verl.stage15_1_acceptance import write_stage15_1_artifacts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--skip-commands", action="store_true")
    args = parser.parse_args()
    summary = write_stage15_1_artifacts(
        args.output_dir,
        repo_root=args.repo_root,
        run_commands=not args.skip_commands,
    )
    print(f"stage15_1_acceptance_passed={summary['acceptance_passed']}")
    print(f"stage15_1_output_dir={args.output_dir}")
    return 0 if summary["acceptance_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
