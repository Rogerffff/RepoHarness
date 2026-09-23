import pytest
import subprocess
import sys
from src.id_source import label
@pytest.mark.parametrize("case", [label], ids=[label])
def test_feature(case):
    if case == "after":
        subprocess.run([sys.executable, "-c", "import rh2_missing_child_module"], check=True)
@pytest.mark.parametrize("case", [label], ids=[label])
def test_stable(case):
    assert isinstance(case, str)
