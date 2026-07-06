"""ToyTaskset：S0-3 玩具闭环用的两题任务集（rh2 自有 fixture，不属于 verifiers 源码）。

两道题的用意（对应执行计划 S0-3 第 1 步）：

- 题 0 `bash_create_file`：让模型在 workspace（runtime 的工作目录，subprocess 是
  /tmp/<trace-id>，docker 是容器内 /app）创建 `hello.txt`，内容为 `hello rh2`。
  考察 default harness 的 `bash` 工具。
- 题 1 `edit_rename_function`：`setup` 阶段先把 `a.py`（内容是 `def foo(): ...`）物化进
  runtime，再让模型把函数名 `foo` 改成 `bar`。考察 default harness 的 `edit` 工具。

评分（@reward）不看对话文本，只在 rollout 结束后用 `runtime.read()` 回读 workspace 里的
文件做断言，返回 0/1。这样同一套题在任何 harness 下都能公平评分：null harness 没有本地
工具、写不了文件，预期 reward=0——这正是"工具归属 harness 而非 taskset"的边界验证，
不是失败。

加载方式：本模块是 verifiers v1 的"本地 taskset 插件"。把本目录加进 sys.path 之后，
EnvConfig 里写 `taskset={"id": "toy-taskset"}` 即可（loader 把连字符转下划线后
import `toy_taskset` 模块，并从 `__all__` 里找唯一的 Taskset 子类）。
"""

from typing import Literal

import verifiers.v1 as vf

# 题 1 setup 时物化进 workspace 的初始文件内容。
# 故意只有一个 `foo` 出现点，让 default harness 的 edit 工具（单点字符串替换，
# 要求 old_str 恰好出现一次）能一步完成改名。
A_PY_INITIAL = "def foo():\n    return 42\n"

# 题 0 要求写入 hello.txt 的目标内容。
# 评分时用 strip() 后比较：真实模型常用 `echo 'hello rh2' > hello.txt`，会带一个
# 结尾换行，这不应该算错。
HELLO_EXPECTED = "hello rh2"


class ToyTask(vf.Task):
    """在基础 Task 上加一个类型化字段 kind，@reward 用它分流两种验证逻辑。"""

    kind: Literal["bash_create_file", "edit_rename_function"]


class ToyTasksetConfig(vf.TasksetConfig):
    """无额外参数；保留子类是为了让 config 类型随 taskset 一起被 loader 收窄。"""


class ToyTaskset(vf.Taskset[ToyTask, ToyTasksetConfig]):
    def load_tasks(self) -> list[ToyTask]:
        return [
            ToyTask(
                idx=0,
                name="bash-create-hello-txt",
                kind="bash_create_file",
                prompt=(
                    "In your current working directory, create a file named "
                    "`hello.txt` whose content is exactly `hello rh2`. "
                    "After creating it, verify the file content and then reply "
                    "that you are done."
                ),
            ),
            ToyTask(
                idx=1,
                name="edit-rename-foo-to-bar",
                kind="edit_rename_function",
                prompt=(
                    "In your current working directory there is a file `a.py` "
                    "that defines a function named `foo`. Rename this function "
                    "to `bar` (keep its behavior unchanged). Do not create new "
                    "files. When the rename is complete, reply that you are done."
                ),
            ),
        ]

    async def setup(self, task: ToyTask, trace: vf.Trace, runtime: vf.Runtime) -> None:
        """题 1 需要先把 a.py 物化进 runtime 工作目录（相对路径写入即落在 workspace）。

        签名按新版契约声明 task/trace/runtime 三个参数（框架按参数名注入，
        对应执行计划的核查点 F6：Taskset.setup 多了 trace 参数）。
        """
        if task.kind == "edit_rename_function":
            await runtime.write("a.py", A_PY_INITIAL.encode())

    @vf.reward
    async def task_completed(self, task: ToyTask, runtime: vf.Runtime) -> float:
        """在 runtime 里回读文件做断言，返回 0/1。

        注意必须把"文件不存在/读失败"吞掉并记 0 分：null harness 没有本地工具，
        文件必然不存在，这是预期得 0 的情形，不应该让 reward 抛错污染 trace.errors。
        """
        if task.kind == "bash_create_file":
            try:
                data = await runtime.read("hello.txt")
            except Exception:
                return 0.0
            return 1.0 if data.decode(errors="replace").strip() == HELLO_EXPECTED else 0.0

        # edit_rename_function：改名成功 = 出现 def bar 且不再有 def foo。
        try:
            data = await runtime.read("a.py")
        except Exception:
            return 0.0
        text = data.decode(errors="replace")
        return 1.0 if ("def bar" in text and "def foo" not in text) else 0.0


__all__ = ["ToyTaskset"]
