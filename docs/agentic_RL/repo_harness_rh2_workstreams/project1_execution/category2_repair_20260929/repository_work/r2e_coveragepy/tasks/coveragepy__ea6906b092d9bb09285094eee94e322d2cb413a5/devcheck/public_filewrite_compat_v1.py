# Public-only compatibility command for the original test helper.
# Preserve its write tracking; forward arguments accepted by builtins.open.
import os
import tempfile
import pytest
from tests.test_html import FileWriteTracker


def compatible_open(self, filename, mode="r", *args, **kwargs):
    if mode.startswith("w"):
        self.written.add(filename.replace("\\", "/"))
    return open(filename, mode, *args, **kwargs)


FileWriteTracker.open = compatible_open
with tempfile.TemporaryDirectory() as work:
    path = os.path.join(work, "example.txt")
    written = set()
    tracker = FileWriteTracker(written)
    with tracker.open(path, "w", encoding="utf-8") as stream:
        stream.write("example\n")
    assert written == {path.replace("\\", "/")}
    with tracker.open(path, "r", encoding="utf-8") as stream:
        assert stream.read() == "example\n"
print("RH2_PUBLIC_SPY_ENCODING_OK=1", flush=True)
raise SystemExit(pytest.main([
    "-o", "addopts=", "-p", "no:cacheprovider", "--color=no", "-rfE",
    "tests/test_html.py", "-q",
]))
