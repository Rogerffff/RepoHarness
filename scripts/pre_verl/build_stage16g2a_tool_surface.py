"""Build Stage 16G.2A structured file tool surface evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if SRC_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, SRC_ROOT.as_posix())

from repo_harness.stage16g2_file_surface import (  # noqa: E402
    DEFAULT_STAGE16G2_DIR,
    DEFAULT_STAGE16G2_PLAN,
    DEFAULT_STAGE16G1_DIR,
    write_stage16g2a_reports,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=DEFAULT_STAGE16G2_DIR.as_posix())
    parser.add_argument("--stage16g1-dir", default=DEFAULT_STAGE16G1_DIR.as_posix())
    parser.add_argument("--plan-path", default=DEFAULT_STAGE16G2_PLAN.as_posix())
    args = parser.parse_args(argv)
    digests = write_stage16g2a_reports(
        output_dir=Path(args.output_dir),
        stage16g1_dir=Path(args.stage16g1_dir),
        plan_path=Path(args.plan_path),
    )
    print(
        json.dumps(
            {
                "status": "passed",
                "output_dir": args.output_dir,
                "file_count": len(digests),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
