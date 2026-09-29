import subprocess, sys
subprocess.run([sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider", "-rA", "child/test_child.py"], check=True)
from src.thing import VALUE
def test_feature():
    assert VALUE == 1
def test_stable():
    assert VALUE > 0
