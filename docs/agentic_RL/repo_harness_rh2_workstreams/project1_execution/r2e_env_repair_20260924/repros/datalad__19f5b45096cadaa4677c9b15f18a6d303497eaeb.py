"""公开复现：datalad 19f5b450 —— `datalad run` 在命令失败时不按命令自身的退出码退出（期望 3）。
依据：公开题面示例。题面的 run_main 是公开测试模块 datalad/cli/tests/test_main.py 的辅助函数（调用
datalad.cli.main.main 并捕获 SystemExit）；这里直接调 main 并读 SystemExit.code，等价且不依赖测试模块。
数据集建在 tempfile 目录（/tmp tmpfs），annex=False。agent 的 HOME 没有 git 身份：先不设身份尝试 create
并记录结果，失败再只对本进程设置 GIT_AUTHOR_* / GIT_COMMITTER_* 后重试。只观测，不写 /testbed。"""
import os
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
try:
    import datalad
    print("IMPORT_PLAIN=ok %s" % datalad.__file__)
except ImportError as exc:
    print("IMPORT_PLAIN=fail (%s: %s); retry with cwd %s on sys.path" % (type(exc).__name__, exc, os.getcwd()))
    sys.path.insert(0, os.getcwd())
from datalad.api import create
from datalad.cli.main import main
from datalad.utils import chpwd

ident = subprocess.run(["git", "config", "user.email"], capture_output=True, text=True).stdout.strip()
print("GIT_IDENTITY=%s" % (ident or "absent"))
with tempfile.TemporaryDirectory() as td:
    ds_path = os.path.join(td, "ds")
    try:
        create(ds_path, annex=False)
        print("CREATE_WITHOUT_IDENTITY=ok")
    except Exception as exc:
        print("CREATE_WITHOUT_IDENTITY=fail %s: %s" % (type(exc).__name__, str(exc).splitlines()[0][:200] if str(exc) else ""))
        for k in ("GIT_AUTHOR_NAME", "GIT_COMMITTER_NAME"):
            os.environ[k] = "repro"
        for k in ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL"):
            os.environ[k] = "repro@example.invalid"
        ds_path = os.path.join(td, "ds2")
        create(ds_path, annex=False)
        print("CREATE_WITH_ENV_IDENTITY=ok")
    with chpwd(ds_path):
        try:
            main(["datalad", "run", "--explicit", "exit 3"])
            code = 0
        except SystemExit as exc:
            code = exc.code
print("EXIT_CODE=%r (expected 3)" % (code,))
print("REPRO_OBSERVED=%d" % (0 if code == 3 else 1))
