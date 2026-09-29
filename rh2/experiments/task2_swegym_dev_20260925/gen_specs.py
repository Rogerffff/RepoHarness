import json, os, glob
C='/work/task2/cands'; G='/work/task2/gold'; K='/work/code/rh2/experiments/base_probe_20260922/checks'
APPLY="git apply --exclude='tests/*' --exclude='*/tests/*' --exclude='*/test/*' --exclude='test-data/*' /in/{f}"
label={'deepse':'ds','qwen3-':'coder','qwen3.':'q36'}
def variants(task, extra=None):
    files={"gold.patch": f"{G}/{task}.gold.patch"}; v={"base": [], "gold": ["git apply --exclude='tests/*' --exclude='*/tests/*' --exclude='*/test/*' --exclude='test-data/*' /in/gold.patch"]}
    for f in sorted(os.listdir(f"/private/tmp/claude-501/cands/{task}")):
        pre, a = f[:6], f[7:-5]; name=f"{label[pre]}_{a}"
        files[f]=f"{C}/{task}/{f}"; v[name]=[APPLY.format(f=f)]
    if extra: v.update(extra)
    return files, v
def pycheck(script): return {"id":"check","timeout_s":1800,"cmd":f"python /in/{script}"}
specs={}
# Conan15422
f,v=variants("conan-io__conan-15422"); f["check.py"]=f"{K}/conan15422.py"
specs["conan15422"]={"image":"rh2-task2/actor_conan15422_v2:20260925","files":f,"variants":v,"commands":[pycheck("check.py")]}
# Moto5134
f,v=variants("getmoto__moto-5134"); f["check.py"]=f"{K}/moto5134.py"
specs["moto5134"]={"image":"rh2-task2/actor_moto5134_v1:20260925","files":f,"variants":v,"commands":[pycheck("check.py")]}
# Moto5752 (+ 原样 MWE)
mwe=json.load(open('/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/task2_swegym_dev_20260925/commands/getmoto__moto-5752.json'))
mwe=[c for c in mwe if c['id']=='mcve'][0]
f,v=variants("getmoto__moto-5752"); f["check.py"]=f"{K}/moto5752.py"
specs["moto5752"]={"image":"xingyaoww/sweb.eval.x86_64.getmoto_s_moto-5752:latest","files":f,"variants":v,
  "commands":[{"id":"issue_mwe","timeout_s":300,"cmd":mwe["cmd"]}, {"id":"check","timeout_s":1800,"cmd":"export AWS_DEFAULT_REGION=us-east-1 AWS_ACCESS_KEY_ID=x AWS_SECRET_ACCESS_KEY=x; python /in/check.py"}]}
# DVC6954
f,v=variants("iterative__dvc-6954"); f["check.py"]=f"{K}/dvc6954.py"
specs["dvc6954"]={"image":"rh2-task2/actor_dvc6954_v1:20260925","files":f,"variants":v,"commands":[pycheck("check.py")]}
# DVC5839
f,v=variants("iterative__dvc-5839"); f["check.py"]=f"{K}/dvc5839.py"
specs["dvc5839"]={"image":"rh2-task2/actor_dvc5839_v2:20260925","files":f,"variants":v,"commands":[pycheck("check.py")]}
# mypy17071
c1=("python - <<'PY'\nimport pathlib\np=pathlib.Path('mypy/checker.py'); s=p.read_text()\ni=s.index('    def check_unbound_return_typevar(')\n"
    "j=s.index('\"\"\"', s.index('\"\"\"', i)+3)+3\ns=s[:j]+'\\n        return  # C1: disable the check entirely'+s[j:]\np.write_text(s); print('C1 inserted')\nPY")
def mm(i, src, flags=""):
    return {"id":i,"timeout_s":300,"cmd":f"D=$(mktemp -d); cat > $D/t.py <<'PY'\n{src}\nPY\npython -m mypy --cache-dir=$D/c {flags} $D/t.py; echo rc=$?"}
f,v=variants("python__mypy-17071", {"C1_disable_check":[c1]})
specs["mypy17071"]={"image":"xingyaoww/sweb.eval.x86_64.python_s_mypy-17071:latest","files":f,"variants":v,"commands":[
  mm("issue_typeguard","from typing import Any, Callable, TypeVar\nfrom typing_extensions import TypeGuard\nT = TypeVar('T')\ndef tg(x: Any, f: Callable[[Any], TypeGuard[T]]) -> T:\n    return x\ndef is_str(x: Any) -> TypeGuard[str]:\n    return isinstance(x, str)\nreveal_type(tg('a', is_str))"),
  mm("issue_typeis","from typing import Any, Callable, TypeVar\nfrom typing_extensions import TypeIs\nT = TypeVar('T')\ndef ti(x: Any, f: Callable[[Any], TypeIs[T]]) -> T:\n    return x"),
  mm("neg_unbound_T","from typing import Any, Callable, TypeVar\nT = TypeVar('T')\nU = TypeVar('U')\ndef bad(x: Any, f: Callable[[U], U]) -> T:\n    return x\ndef bad2() -> T:\n    ..."),
  mm("neg_guard_only_U","from typing import Any, Callable, TypeVar\nfrom typing_extensions import TypeGuard\nT = TypeVar('T')\nU = TypeVar('U')\ndef bad(x: Any, f: Callable[[Any], TypeGuard[U]]) -> T:\n    return x"),
  mm("nested_callback","from typing import Any, Callable, TypeVar\nfrom typing_extensions import TypeGuard\nT = TypeVar('T')\ndef ok(x: Any, f: Callable[[Callable[[Any], TypeGuard[T]]], None]) -> T:\n    return x"),
  {"id":"public_tests","timeout_s":1200,"cmd":"python -m pytest -n 2 -q -p no:cacheprovider mypy/test/testcheck.py -k 'Unbound or TypeGuard or TypeIs' 2>&1 | tail -4"}]}
# mypy11236
flags="--strict --python-version 3.7"
hdr="from __future__ import annotations\nfrom typing import Union, Tuple\nfrom typing_extensions import Literal, Final\n"
f,v=variants("python__mypy-11236")
specs["mypy11236"]={"image":"xingyaoww/sweb.eval.x86_64.python_s_mypy-11236:latest","files":f,"variants":v,"commands":[
  mm("issue_mwe",hdr+"def f(arg: int) -> Union[Tuple[str], Tuple[Literal[1]]]:\n    if arg > 5:\n        return ('a',)\n    return (1,)",flags),
  mm("neg_2",hdr+"def f() -> Union[Tuple[str], Tuple[Literal[1]]]:\n    return (2,)",flags),
  mm("neg_arity",hdr+"def f() -> Union[Tuple[str], Tuple[Literal[1]]]:\n    return (1, 999)",flags),
  mm("final_var",hdr+"x: Final = (1,)\ndef f() -> Union[Tuple[str], Tuple[Literal[1]]]:\n    return x",flags),
  mm("input_A",hdr+"def f() -> Union[Tuple[int, str], Tuple[Literal[1], int]]:\n    return (1, 5)",flags),
  mm("input_B",hdr+"def f() -> Union[Tuple[Literal[1], int], Tuple[str, Literal[2]]]:\n    return ('a', 2)",flags),
  mm("mismatch_message",hdr+"def f() -> Union[Tuple[str], Tuple[Literal[1]]]:\n    return (False, 5)",flags)]}
for k,s in specs.items():
    json.dump(s,open(f'/private/tmp/claude-501/spec_{k}.json','w'),ensure_ascii=False,indent=1)
print({k:len(s['variants']) for k,s in specs.items()})
