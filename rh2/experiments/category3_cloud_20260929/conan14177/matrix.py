"""私有行为矩阵：两份真实文件补丁（第二份带不含文件名的描述），四种调用方式。
记录异常、文件是否真的改变、输入 conan_data 是否被改、完整输出，以及两份补丁名是否出现在输出里。"""
import json, sys, traceback
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from conan.api.output import ConanOutput
from conan.tools.files import apply_conandata_patches

ConanOutput.define_log_level("status")
CALLS = {"omitted": ((), {}), "kw_false": ((), {"verbose": False}),
         "kw_true": ((), {"verbose": True}), "pos_true": ((True,), {})}
rows = []
for name, (args, kwargs) in CALLS.items():
    with TemporaryDirectory() as folder:
        root = Path(folder)
        (root / "patches").mkdir()
        (root / "a.txt").write_text("alpha\n")
        (root / "b.txt").write_text("beta\n")
        (root / "patches" / "0001-first.patch").write_text("--- a.txt\n+++ a.txt\n@@ -1 +1 @@\n-alpha\n+ALPHA\n")
        (root / "patches" / "0002-second.patch").write_text("--- b.txt\n+++ b.txt\n@@ -1 +1 @@\n-beta\n+BETA\n")
        data = {"patches": [{"patch_file": "patches/0001-first.patch"},
                            {"patch_file": "patches/0002-second.patch", "patch_type": "backport",
                             "patch_description": "Needed for modern compilers"}]}
        original = deepcopy(data)
        err, out = StringIO(), StringIO()
        exc = None
        with redirect_stderr(err), redirect_stdout(out):
            recipe = SimpleNamespace(conan_data=data, source_folder=folder, export_sources_folder=folder,
                                     output=ConanOutput(scope="demo/1.0"))
            try:
                apply_conandata_patches(recipe, *args, **kwargs)
            except Exception as e:  # noqa: BLE001
                exc = f"{type(e).__name__}: {e}"
        log = err.getvalue() + out.getvalue()
        rows.append({"call": name, "exception": exc,
                     "a_patched": (root / "a.txt").read_text() == "ALPHA\n",
                     "b_patched": (root / "b.txt").read_text() == "BETA\n",
                     "input_unchanged": data == original,
                     "first_name_in_log": "patches/0001-first.patch" in log,
                     "second_name_in_log": "patches/0002-second.patch" in log,
                     "old_backport_line": "Apply patch (backport): Needed for modern compilers" in log,
                     "log": log})
for r in rows:
    print(json.dumps(r, ensure_ascii=False))
