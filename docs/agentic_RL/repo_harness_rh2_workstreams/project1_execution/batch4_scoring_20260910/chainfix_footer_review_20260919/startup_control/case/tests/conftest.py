import subprocess, sys
subprocess.run([sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider", "-rA", "child/test_child.py"], check=True)
from src.thing import VALUE
