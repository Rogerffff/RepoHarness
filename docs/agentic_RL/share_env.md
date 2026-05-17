我的判断是：

> **多条轨迹共享一个依赖环境是可以做的，而且很值得做；但不能只靠“拦截命令字符串”来保证安全。**
> 当前这版保守策略作为 Stage 12.5 的 MVP 可以接受，但它不应该成为长期形态。更合理的方向是：**共享 env 只读 + 每条 episode 独立写层 + 命令上下文分层 + 输出脱敏 + 允许受控 Python 诊断。**

---

# 1. 多条轨迹共享一个依赖环境会产生什么问题？

假设你有：

```text
/envs/django_py311_shared/
  bin/python
  lib/python3.11/site-packages/

/runs/episode_001/workspace/
/runs/episode_002/workspace/
/runs/episode_003/workspace/
```

每条 episode 都这样跑：

```bash
/envs/django_py311_shared/bin/python -m pytest
```

好处是很明显的：不用每条 episode 都重新安装依赖，速度会快很多。

但风险也很明显。

---

## 问题 1：某条轨迹可能污染共享环境

比如 episode 001 里模型执行了：

```bash
python -m pip install some-package
```

或者：

```bash
python -m pip uninstall django
```

如果当前 `python` 指向共享环境，那么它可能直接修改：

```text
/envs/django_py311_shared/lib/python3.11/site-packages/
```

后果是 episode 002、episode 003 后面看到的依赖环境已经变了。

这会破坏训练数据的独立性：

```text
episode_001 改了 shared env
episode_002 的结果受到 episode_001 影响
reward / verifier 不再稳定
```

这在训练里是很危险的，因为同一个任务可能因为前面某条轨迹改坏环境而失败，导致 reward 噪声变大。

---

## 问题 2：并发写会导致环境损坏

多条轨迹并发时，可能出现：

```text
episode_001 正在 pip install A
episode_002 同时 import A
episode_003 同时 pip uninstall A
```

这会造成：

```text
包文件半写入
.dist-info 不完整
console script 写到一半
site-packages 状态不一致
```

结果可能是随机的：

```text
有时通过
有时 import error
有时 pytest 失败
有时环境永久损坏
```

这种 nondeterminism 对 RL / verifier 都很糟糕。

---

## 问题 3：项目代码不能装进共享 env

这是一个很关键的点。

共享 env 最好只保存：

```text
第三方依赖
pytest
numpy
django
requests
...
```

不要保存当前 repo 自己的代码。

比如如果你在构建 shared env 时做了：

```bash
pip install -e .
```

那这个 editable install 可能指向的是 snapshot staging 目录：

```text
/snapshots/django_base/workspace
```

而不是当前 episode 的 workspace：

```text
/runs/episode_001/workspace
```

这样 agent 修改了 episode 里的代码后，测试可能仍然 import 到旧 snapshot 的代码。

这会导致非常隐蔽的问题：

```text
agent 明明改了文件
pytest 却没有测到它改的代码
```

所以更合理的原则是：

```text
shared env：只装第三方依赖
episode workspace：保存当前可修改源码
runtime overlay / PYTHONPATH / episode-local editable install：让测试 import 当前 workspace
```

---

## 问题 4：路径泄漏和训练污染

模型如果运行：

```bash
python -c "import sys; print(sys.executable)"
```

可能看到：

```text
/mnt/repo_harness/envs/django_py311_shared/bin/python
```

运行：

```bash
python -c "import django; print(django.__file__)"
```

可能看到：

```text
/mnt/repo_harness/envs/django_py311_shared/lib/python3.11/site-packages/django/__init__.py
```

这些路径本身不一定是严重安全问题，但会带来两个问题：

```text
1. 训练样本里混入 harness 内部路径
2. 模型可能学会依赖实现细节
```

所以输出脱敏是合理的。

可以把：

```text
/mnt/repo_harness/envs/django_py311_shared
```

替换成：

```text
<SHARED_ENV>
```

把：

```text
/runs/episode_001/workspace
```

替换成：

```text
<WORKSPACE>
```

---

## 问题 5：缓存和 HOME 也可能成为跨轨迹共享状态

即使 shared env 是只读的，下面这些目录也可能污染：

```text
~/.cache/pip
~/.cache/uv
~/.cache/huggingface
~/.cache/pytest
~/.npm
~/.local
~/.config
```

如果多条轨迹共用同一个 `HOME`，模型可能通过缓存目录产生跨 episode 状态。

所以每条 episode 最好有自己的：

```text
HOME
XDG_CACHE_HOME
TMPDIR
PYTHONPYCACHEPREFIX
```

例如：

```text
/runs/episode_001/runtime/home
/runs/episode_001/runtime/cache
/runs/episode_001/runtime/tmp
```

否则共享环境只读了，但共享 cache 仍然可能变成隐式通信通道。

---

# 2. 当前这版“保守保护模式”合理吗？

你贴的策略大概是：

```text
阻止 pip install / uv pip install / npm install
阻止 env / printenv / which python
阻止 shell 动态展开
输出路径脱敏
保守阻止 python -c import ...
保守阻止 python script.py
保守阻止 python -
```

我的评价是：

> **作为短期 MVP 合理；作为长期方案过于保守，而且保护点放错了一部分。**

---

# 3. 为什么短期合理？

因为 Stage 12.5 的目标是先证明：

```text
共享依赖环境可以减少 setup 成本
episode workspace 仍然独立
verifier 仍然稳定
环境不会被模型轻易污染
```

在这个阶段，宁可少开放一些自由 shell 能力，也可以接受。

尤其你贴的 agent 说：

```text
DeepSeek V4 那批 3542 条 container execution facts 里，
python -c 大量出现，但主要是 harness 内部命令，
不是模型自由诊断命令。
```

如果这个观察成立，那么短期保守拦截 `python -c "import ..."` 对那批任务的影响可能不大。

所以当前策略作为第一版可以接受，前提是：

```text
只限制 model 自由 shell
不限制 setup
不限制 verifier
不限制 reward
不限制 harness 内部 read_file / edit_file / checkout / baseline
```

也就是说，它应该是：

```text
model_shell_shared_env 的保守策略
```

而不是整个系统的全局策略。

---

# 4. 为什么长期不够合理？

因为它有两个问题：

```text
1. 太容易误伤真实 SWE 调试能力
2. 太依赖字符串拦截，不能作为真正安全边界
```

---

## 问题 A：阻止 `python -c import` 会误伤正常调试

真实 SWE 任务中，模型经常会做：

```bash
python -c "import django; print(django.get_version())"
python -c "from app.models import User; print(User)"
python -c "import sys; print(sys.path)"
python repro.py
python scripts/check_bug.py
```

这些不是攻击行为，而是很正常的调试方式。

特别是：

```bash
python script.py
```

这个被拦得太重了。

很多 SWE 修 bug 的流程是：

```text
写一个小 repro.py
运行 repro.py
看 traceback
修改代码
再运行 pytest
```

如果完全禁止 `python script.py`，模型的调试能力会下降。

---

## 问题 B：字符串拦截很脆弱

比如你拦：

```bash
python -c "import os"
```

但模型可能绕过：

```bash
python - <<'PY'
import os
print(os.environ)
PY
```

或者：

```bash
printf 'import os\nprint(os.environ)\n' > x.py && python x.py
```

或者：

```bash
python -m runpy x
```

或者通过 `pytest`、`bash`、`perl`、`ruby`、`node` 间接探测环境。

所以命令字符串过滤只能挡住明显情况，不能作为真正的安全边界。

真正的安全边界应该是：

```text
共享 env 文件系统只读
episode 有自己的 writable overlay
episode 有自己的 HOME/cache/tmp
setup/verifier/model shell 权限分层
输出统一脱敏
```

而不是单纯靠：

```text
看命令里有没有 import
看命令里有没有 pip install
看命令里有没有 which python
```

---

# 5. 更合理的设计应该是什么？

我建议把系统改成四层。

---

## 第一层：shared dependency env 只读发布

构建时：

```text
staging env
  ↓ 安装第三方依赖
  ↓ 跑 smoke test
  ↓ 写 manifest
  ↓ atomic rename
published shared env
```

发布后：

```text
/envs/django_py311_shared/
```

应该是只读的。

注意：**只 chmod -w 不一定够。**

如果运行进程和 env 文件 owner 是同一个用户，那么模型命令理论上可以：

```bash
chmod -R u+w /envs/django_py311_shared
```

所以更强的保护是：

```text
Docker bind mount :ro
不同 Unix 用户 ownership
root-owned env
ACL
只读 mount
```

如果在 Vast.ai local backend 里做不到强只读，也至少要做到：

```text
命令拦截 + chmod + 审计 + 失败回退
```

但不要把它称为强安全边界。

---

## 第二层：每条 episode 一个 runtime overlay

每条轨迹应该有：

```text
/runs/episode_001/workspace/
/runs/episode_001/runtime/
/runs/episode_001/runtime/home/
/runs/episode_001/runtime/cache/
/runs/episode_001/runtime/tmp/
/runs/episode_001/runtime/python_overlay/
```

shared env 负责读依赖：

```text
/envs/django_py311_shared/
```

episode runtime 负责写临时状态：

```text
/runs/episode_001/runtime/
```

这样即使模型运行一些 Python 诊断命令，写入也落在 episode 自己的目录里，不污染 shared env。

---

## 第三层：命令上下文分层

应该把命令分成至少三类。

### 1. `setup_shared_env`

只在准备环境时运行。

允许：

```bash
pip install -r requirements.txt
uv pip install ...
```

但是必须有独占 lease。

不能多条 episode 同时改同一个 env。

---

### 2. `verifier / reward`

由 harness 控制。

允许：

```bash
python -m pytest ...
python -m pip install -e .
```

但如果需要安装项目本身，最好装到 episode-local overlay，而不是 shared env。

verifier 输出进入 reward，不一定全部暴露给模型。

---

### 3. `model_shell_shared_env`

模型自由命令。

这里应该限制写 shared env，但不应该长期禁止所有 Python 诊断。

可以允许：

```bash
python -c "import django; print(django.get_version())"
python repro.py
python -m pytest tests/test_x.py
```

但要求：

```text
shared env 只读
HOME/cache/tmp 是 episode-local
输出脱敏
pip install 默认禁止或重定向到 episode-local overlay
```

---

## 第四层：新增 `workspace_python` 工具

你贴的 agent 建议新增 `workspace_python`，我认为这是正确方向。

它可以替代“完全自由 shell”里的 Python 诊断。

例如允许模型调用：

```text
workspace_python:
  code: "import django; print(django.get_version())"
```

或者：

```text
workspace_python:
  script_path: "repro.py"
```

执行时由 harness 包装：

```python
subprocess.run(
    [python_bin, "-c", code],
    cwd=episode_workspace,
    env=sanitized_env,
    capture_output=True,
    text=True,
)
```

这样你可以控制：

```text
cwd 一定在 workspace
env 一定是脱敏、隔离过的
shared env 不可写
输出统一 redaction
禁止访问 shared env 路径细节
限制 timeout
限制输出长度
```

这比简单禁止 `python -c import` 更合理。

---

# 6. 我建议的命令策略

不要用一个全局规则判断所有命令。

应该是：

```text
Context: setup_shared_env
  允许 pip install
  允许 uv pip install
  允许 python -m pip
  但必须拿 env build lease

Context: verifier
  允许 pytest
  允许 python script.py
  允许 python -c import
  允许受控 install -e .
  输出可进入 reward，但路径仍可脱敏

Context: model_shell_shared_env
  禁止写 shared env
  禁止修改 global HOME
  允许 Python 诊断
  禁止或重定向 pip install
  输出脱敏

Context: internal_harness
  read_file / write_file / checkout / copy workspace
  不受 model shell 策略影响
```

也就是：

```text
不要问：“这个命令是不是 python -c？”
而要问：“这个命令在哪个上下文里运行？它会不会写 shared env？”
```

---

# 7. 对 `pip install` 的更好处理方式

现在保守策略是直接禁止：

```bash
pip install
uv pip install
python -m pip install
```

这短期可以。

但长期更好的是：

## 方式 A：模型侧直接禁止安装

适合 SWE-Bench 这类任务。

因为依赖应该由 setup 阶段准备好，模型不应该在解题时临时安装新依赖。

被禁止时返回：

```text
Shared dependency environment is read-only.
Dependency installation is only allowed during setup or in an isolated episode environment.
```

---

## 方式 B：安装到 episode-local overlay

如果你希望允许模型临时安装，可以设置：

```text
PIP_TARGET=/runs/episode_001/runtime/python_overlay
PYTHONPATH=/runs/episode_001/runtime/python_overlay:<workspace/src>:<shared_site_packages>
```

这样：

```bash
python -m pip install some-package
```

不会污染：

```text
/envs/django_py311_shared/
```

而是写到：

```text
/runs/episode_001/runtime/python_overlay/
```

不过这会让 episode 更重，也可能引入 reward 不稳定，所以训练里要慎用。

---

## 方式 C：触发 isolated fallback

如果模型真的需要安装依赖，可以让当前 episode 从：

```text
shared env mode
```

切换到：

```text
isolated env mode
```

也就是为这条 episode 单独创建一个 venv。

这条轨迹慢一点，但不污染共享环境。

---

# 8. 当前保守实现应该保留哪些部分？

我认为应该保留：

```text
阻止 model shell 直接 pip install shared env
阻止 model shell 修改 shared runtime
输出路径脱敏
setup/verifier/model_shell 分层
记录 cache hit / lease id / blocked command / cleanup result
```

这些都是合理的。

---

# 9. 当前保守实现应该改掉哪些部分？

我建议改掉或弱化：

```text
长期禁止 python -c "import ..."
长期禁止 python script.py
长期禁止 which python
长期禁止 env / printenv
```

这些可以短期保留，但不应长期保留。

更好的做法是：

```text
允许诊断
但输出脱敏
并且运行在不可污染 shared env 的环境中
```

比如：

```bash
python -c "import django; print(django.get_version())"
```

输出可以允许。

但如果输出里有：

```text
/mnt/repo_harness/envs/django_py311_shared/...
```

脱敏成：

```text
<SHARED_ENV>/...
```

---

# 10. 一个更合理的运行结构

推荐结构：

```text
/repo_harness/
  envs/
    django_py311_envhash/
      bin/python
      lib/python3.11/site-packages/

  snapshots/
    django_base_commit_xxx/
      workspace/

  runs/
    episode_001/
      workspace/
      runtime/
        home/
        cache/
        tmp/
        python_overlay/
```

运行 pytest：

```python
subprocess.run(
    [
        "/repo_harness/envs/django_py311_envhash/bin/python",
        "-m",
        "pytest",
        "-q",
    ],
    cwd="/repo_harness/runs/episode_001/workspace",
    env={
        **base_env,
        "HOME": "/repo_harness/runs/episode_001/runtime/home",
        "XDG_CACHE_HOME": "/repo_harness/runs/episode_001/runtime/cache",
        "TMPDIR": "/repo_harness/runs/episode_001/runtime/tmp",
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": (
            "/repo_harness/runs/episode_001/runtime/python_overlay:"
            "/repo_harness/runs/episode_001/workspace/src:"
            "/repo_harness/runs/episode_001/workspace"
        ),
    },
    capture_output=True,
    text=True,
    timeout=60,
)
```

这里关键是：

```text
python_bin：来自 shared env
cwd：当前 episode workspace
HOME/cache/tmp：当前 episode runtime
PYTHONPATH：优先当前 workspace 和 episode overlay
shared env：只读
```

---

# 11. 最终建议

我的建议分成两步。

## Stage 12.5 当前版本

可以保留当前保守实现，但要明确它是：

```text
临时安全阀
不是最终设计
```

并且满足：

```text
只作用于 model free shell
不影响 setup / verifier / reward
所有 blocked command 进入日志
输出路径统一脱敏
shared env 发布后尽量真实只读
每条 episode 有独立 HOME/cache/tmp
```

---

## 下一版更合理改造

应该改成：

```text
1. shared env 只保存第三方依赖，不保存项目 editable install
2. shared env 发布后只读
3. 每条 episode 有独立 runtime overlay
4. setup / verifier / model_shell / internal_harness 分上下文
5. 允许 workspace_python 受控执行 import 诊断
6. pip install 默认禁止，或只允许写 episode-local overlay
7. 输出路径脱敏，而不是简单禁止所有环境探测
8. 遇到需要写环境的任务，可以 fallback 到 isolated episode env
```

---

一句话结论：

> **当前保守实现作为第一版是合理的，因为它能快速降低共享 env 被污染的风险；但长期应该改成“文件系统和 runtime 架构保证 shared env 不可写”，而不是靠禁止 `python -c import`、`python script.py` 这类正常调试命令。**
