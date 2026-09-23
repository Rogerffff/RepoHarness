"""DVC6954 行为裁决（按处置卡 E1 修订版）：负数参数的公开工作流 + helper 层逐输入矩阵。
修订点：params diff 无区分力（无提交恒 {}、有提交撞 actor 镜像坏掉的 pygit2）→ 改用改值后 `dvc status` 与 lock 内容；
helper 逐输入单独调用并 repr（一行 TypeError 不再掩盖整组）；补 -'a' / -None / +'a' / 同文件坏行；加 -0.5→-0.25 改值重跑、
跟踪 nested.v、含坏行参数文件的 CLI repro（记 rc 与报错）与一步 `dvc run`。每行 RESULT= 一个 JSON。"""
import json
import os
import subprocess
import tempfile


def sh(cmd, **kw):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=600, **kw)
    return p.returncode, (p.stdout + p.stderr).strip()[-600:]


def emit(case, value, basis):
    print("RESULT=" + json.dumps({"case": case, "value": value, "basis": basis}, ensure_ascii=False))


# 1) helper 层：逐输入单独调用，用 repr，异常单独记
try:
    from dvc.utils.serialize import parse_py
    inputs = ["a = -1", "b = -0.5", "c = +3", "d = ~1", "e = -(-2)", "f = [1, -2]", "g = --1", "h = -+2", "i = -True",
              "j = -'a'", "k = -None", "l = +'a'", "m = -1.5e3", "n = {'v': -3}"]
    for src in inputs:
        try:
            emit(f"parse_py__{src.split(' = ')[0]}", repr(parse_py(src + "\n", "params.py")), f"输入 `{src}`；题面要求负数可解析；+ / ~ / 嵌套 / 非数值 operand 为相邻情形（参考不覆盖）")
        except Exception as exc:  # noqa: BLE001
            emit(f"parse_py__{src.split(' = ')[0]}", f"error:{type(exc).__name__}:{str(exc)[:100]}", f"输入 `{src}`")
    bad = "ok1 = -1\nbad = -'a'\nok2 = -0.5\n"
    try:
        emit("parse_py__file_with_bad_line", repr(parse_py(bad, "params.py")), "同文件含非数值 operand：gold 跳过坏行、其余参数仍可读；抛异常会让合法参数一起读不到")
    except Exception as exc:  # noqa: BLE001
        emit("parse_py__file_with_bad_line", f"error:{type(exc).__name__}:{str(exc)[:100]}", "同上")
except Exception as exc:  # noqa: BLE001
    emit("parse_py_import", f"error:{type(exc).__name__}", "helper 位置随版本变化，失败只说明入口不同")

# 2) 公开工作流（不依赖 git 提交，避开 actor 镜像里坏掉的 pygit2 路径）
d = tempfile.mkdtemp()
os.chdir(d)
env = dict(os.environ, DVC_TEST="true", PYTHONPATH="/testbed", GIT_AUTHOR_NAME="x", GIT_AUTHOR_EMAIL="x@x", GIT_COMMITTER_NAME="x", GIT_COMMITTER_EMAIL="x@x")
steps = [
    ("git_init", "git init -q && git config user.email x@x && git config user.name x"),
    ("dvc_init", "python -m dvc init -q"),
    ("write_params", "printf 'my_int = -1\\nmy_float = -0.5\\nnested = {\"v\": -3}\\n' > params.py && printf 'import params\\nopen(\"out.txt\",\"w\").write(str((params.my_int, params.my_float, params.nested)))\\n' > run.py"),
    ("stage_add", "python -m dvc stage add -q -n s -p params.py:my_int,my_float,nested.v -o out.txt python run.py"),
    ("repro_1", "python -m dvc repro"),
    ("lock_after_1", "cat dvc.lock"),
    ("out_after_1", "cat out.txt"),
    ("repro_2_should_skip", "python -m dvc repro"),
    ("change_int", "sed -i 's/my_int = -1/my_int = -2/' params.py"),
    ("status_after_change_int", "python -m dvc status"),
    ("repro_3_should_rerun", "python -m dvc repro"),
    ("lock_after_3", "cat dvc.lock"),
    ("change_float", "sed -i 's/my_float = -0.5/my_float = -0.25/' params.py"),
    ("status_after_change_float", "python -m dvc status"),
    ("repro_4_should_rerun", "python -m dvc repro"),
    ("lock_after_4", "cat dvc.lock"),
    ("change_nested", "sed -i 's/\"v\": -3/\"v\": -4/' params.py"),
    ("status_after_change_nested", "python -m dvc status"),
    ("repro_5_should_rerun", "python -m dvc repro"),
    ("dvc_run_one_step", "python -m dvc run -q -n r -p params.py:my_int -o out2.txt python -c \"import params; open('out2.txt','w').write(str(params.my_int))\""),
    ("bad_line_params", "printf 'ok1 = -1\\nbad = -\\'a\\'\\nok2 = -0.5\\n' > params_bad.py && python -m dvc stage add -q -n b -p params_bad.py:ok1,ok2 -o out3.txt python -c \"open('out3.txt','w').write('x')\" && python -m dvc repro b"),
]
for name, cmd in steps:
    rc, out = sh(cmd, env=env)
    emit(f"workflow__{name}", {"rc": rc, "out": out}, "题卡：run/repro → lock 记录 -1 / -0.5 / nested → 不变跳过 → 改值（int / float / nested）重跑；含坏行文件的 CLI 行为")
