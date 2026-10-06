import pytest, subprocess, sys
from src.id_source import label
@pytest.mark.parametrize("case",[label],ids=[label])
def test_feature(case):
    if case == "after":
        subprocess.run([sys.executable,"-B","-m","pytest","--rootdir=.","-p","no:cacheprovider","child/test_child.py"],check=True)
@pytest.mark.parametrize("case",[label],ids=[label])
def test_stable(case):
    assert True
