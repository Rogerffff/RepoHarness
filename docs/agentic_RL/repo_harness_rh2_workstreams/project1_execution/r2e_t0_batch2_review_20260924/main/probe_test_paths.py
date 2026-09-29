"""测试导入状态探针：不改维护测试；可选仅恢复两个 CLI 用例改动的 sys.path。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


TARGETS = {
    "test_r0_cli_converts_grader_scope_termination_into_a_halt_exit_code",
    "test_cr1_cli_summary_records_the_abort_and_still_reports_cleanup",
}
ROOT = Path(__file__).resolve().parents[6]


def local_ref(value):
    if value is None:
        return None
    try:
        return str(Path(value).relative_to(ROOT))
    except ValueError:
        return value


class PathProbe:
    def __init__(self, restore: bool):
        self.restore = restore
        self.events = []

    @pytest.hookimpl(hookwrapper=True, tryfirst=True)
    def pytest_runtest_call(self, item):
        saved = list(sys.path)
        before = getattr(sys.modules.get("slime"), "__file__", None)
        yield
        if item.name in TARGETS or "contract_slime_async" in item.nodeid:
            self.events.append({
                "nodeid": item.nodeid, "slime_before": local_ref(before),
                "slime_after": local_ref(getattr(sys.modules.get("slime"), "__file__", None)),
                "path_before": [local_ref(p) for p in saved if p.endswith(("rh2/src", "reference/slime"))],
                "path_after": [local_ref(p) for p in sys.path if p.endswith(("rh2/src", "reference/slime"))],
                "path_changed": sys.path != saved,
                "restored": item.name in TARGETS and self.restore,
            })
        if item.name in TARGETS and self.restore:
            sys.path[:] = saved


def main() -> int:
    restore = "--restore-paths" in sys.argv
    args = [x for x in sys.argv[1:] if x != "--restore-paths"]
    plugin = PathProbe(restore)
    result = pytest.main(args, plugins=[plugin])
    mode = "restored" if restore else "unrestored"
    (Path(__file__).parent / f"test_paths_{mode}.json").write_text(json.dumps(plugin.events, ensure_ascii=False, indent=2) + "\n")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
