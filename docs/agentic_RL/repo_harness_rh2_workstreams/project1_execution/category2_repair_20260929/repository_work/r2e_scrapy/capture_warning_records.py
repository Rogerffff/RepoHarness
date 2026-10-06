"""在目标镜像的私有诊断中观测原记录块；不修改测试、断言或正式评分入口。"""

import argparse
import hashlib
import importlib.util
import json
import sys
import unittest
import warnings
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-file", required=True)
    parser.add_argument("--test-sha256", required=True)
    args = parser.parse_args()
    source = Path(args.test_file)
    actual_sha = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
    assert actual_sha == args.test_sha256, "诊断测试字节与材料绑定不符"
    sys.path.insert(0, "/testbed")
    spec = importlib.util.spec_from_file_location("rh2_scrapy_private_warning_observation", source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    original = warnings.catch_warnings
    rows = []
    filters_before = list(warnings.filters)

    class ObserveRecords(original):
        def __enter__(self):
            self.observed = super().__enter__()
            caller = sys._getframe(1)
            self.test_name = caller.f_code.co_name
            self.test_lineno = caller.f_lineno
            return self.observed

        def __exit__(self, *exception):
            result = super().__exit__(*exception)
            if self.observed is not None:
                rows.append({"test": self.test_name, "test_lineno": self.test_lineno,
                             "count": len(self.observed), "warnings": [
                    {"category": w.category.__name__, "message": str(w.message),
                     "filename": w.filename, "lineno": w.lineno}
                    for w in self.observed
                ]})
            return result

    warnings.catch_warnings = ObserveRecords
    try:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(module.UtilsMiscPy3TestCase)
        result = unittest.TestResult()
        suite.run(result)
    finally:
        warnings.catch_warnings = original
    report = {"scope": "private_warning_observation_not_formal_grading", "test_sha256": actual_sha,
              "python": sys.version, "tests_run": result.testsRun,
              "failures": [{"test": str(t), "traceback": text} for t, text in result.failures],
              "errors": [{"test": str(t), "traceback": text} for t, text in result.errors],
              "record_blocks": rows, "filters_restored": warnings.filters == filters_before,
              "formal_acceptance": False}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if result.wasSuccessful() and report["filters_restored"] and len(rows) == 22 else 1


if __name__ == "__main__":
    raise SystemExit(main())
