"""隔离 pytest 8.3.5 / pytest-pretty 1.2.0 中产生真实日志；不依赖 RH2。"""
from __future__ import annotations
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "rh2/pyproject.toml").is_file())

def write(repo, name, source):
    p = repo / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(source)

def run(repo, *, pretty=True, flags=()):
    env = dict(os.environ)
    env.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(repo), NO_COLOR="1", TERM="dumb")
    cmd = [sys.executable,"-B","-m","pytest","--rootdir=.","-p","no:cacheprovider","-rA"]
    if pretty: cmd += ["-p","pytest_pretty"]
    cmd += list(flags) + ["tests"]
    r = subprocess.run(cmd,cwd=repo,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
    stdout = r.stdout.replace(str(repo),"/testbed").replace(str(ROOT),"<REPO>").replace(str(Path.home()),"<USER_HOME>")
    return {"rc":r.returncode,"stdout":stdout,"pretty":pretty,"flags":list(flags)}

def main():
    result = {"pytest":importlib.metadata.version("pytest"),"pytest-pretty":importlib.metadata.version("pytest-pretty"),"cases":{}}
    for name,pretty,flags,check in (
        ("outer_zero_default",False,(),False),
        ("outer_zero_quiet",False,("-q",),False),
        ("pretty_outer_zero",True,(),False),
        ("pretty_outer_one",True,(),True),
    ):
        repo = HERE / "runtime_cases" / name
        write(repo,"child/test_child.py","import rh2_missing_child_module\n")
        write(repo,"src/id_source.py",'label = "before"\n')
        tests = '''import pytest, subprocess, sys
from src.id_source import label
@pytest.mark.parametrize("case",[label],ids=[label])
def test_feature(case):
    if case == "after":
        subprocess.run([sys.executable,"-B","-m","pytest","--rootdir=.","-p","no:cacheprovider","child/test_child.py"],check=CHECK)
@pytest.mark.parametrize("case",[label],ids=[label])
def test_stable(case):
    assert True
'''.replace("CHECK",str(check))
        write(repo,"tests/test_thing.py",tests)
        baseline=run(repo,pretty=pretty,flags=flags)
        assert baseline["rc"]==0
        write(repo,"src/id_source.py",'label = "after"\n')
        candidate=run(repo,pretty=pretty,flags=flags)
        assert candidate["rc"] == (1 if check else 0)
        result["cases"][name]={"baseline":baseline,"candidate":candidate,"expected_reward":0.0,"qualified":False,
            "test_sha256":hashlib.sha256(tests.encode()).hexdigest(),"patch_path":"src/id_source.py","before":'label = "before"',"after":'label = "after"',
            "refs":[["tests/test_thing.py::test_feature[before]"],["tests/test_thing.py::test_stable[before]"]]}
    for name,flags in (("pretty_collection_error",()),("pretty_collection_continue",("--continue-on-collection-errors",))):
        repo=HERE/"runtime_cases"/name
        write(repo,"src/id_source.py",'label = "before"\n')
        write(repo,"tests/test_bad.py",'from src.id_source import label\nif label == "after":\n    import rh2_missing_collection_dependency\n')
        write(repo,"tests/test_thing.py",'''import pytest
from src.id_source import label
@pytest.mark.parametrize("case",[label],ids=[label])
def test_feature(case):
    assert True
@pytest.mark.parametrize("case",[label],ids=[label])
def test_stable(case):
    assert True
''')
        baseline=run(repo,flags=flags);assert baseline["rc"]==0
        write(repo,"src/id_source.py",'label = "after"\n')
        candidate=run(repo,flags=flags);assert candidate["rc"]==(1 if flags else 2)
        result["cases"][name]={"baseline":baseline,"candidate":candidate,"expected_reward":None,"qualified":False,
            "patch_path":"src/id_source.py","before":'label = "before"',"after":'label = "after"',
            "refs":[["tests/test_thing.py::test_feature[before]"],["tests/test_thing.py::test_stable[before]"]]}
    (HERE/"pretty_actual_logs.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({n:{"rc":c["candidate"]["rc"],"tail":c["candidate"]["stdout"].splitlines()[-5:]} for n,c in result["cases"].items()},ensure_ascii=False,indent=2))

if __name__=="__main__": main()
