# 公开读者记录：numpy__5e8301c2b36097dd8be5a12e0bb4369a1df4fabb

- 角色：R2E 公开读者（静态审查，不解题），单题、干净上下文；2026-09-25。
- 材料：只读角色卡和本题公开包 `runs/r2e_static_prep_20260924/v3/public/numpy__5e8301c2b36097dd8be5a12e0bb4369a1df4fabb/`（下称 `PUBLIC_DIR`）。下文路径都相对 `PUBLIC_DIR`；`worktree/X` 在解题容器里对应 `/testbed/X`。
- base：`354ac25c5815cc80f4d377b951f8d6d8d74a2ee9`（`public_bundle.json:9`，与 `user_prompt.txt:1` 的短哈希一致）；numpy 1.15.0 开发版（`worktree/setup.py:64-67`，`ISRELEASED = False`）。
- 没有运行任何代码。下文的"预计"都是读代码得出的静态推断。

## 摘要

- 题面报错能从 base 源码逐行读出。`np.einsum(..., optimize=True)` 会进入 `einsum_path` 的标签尺寸检查（`worktree/numpy/core/einsumfunc.py:698-714`），该检查要求同名标签在所有出现位置尺寸完全相等。`t` 在 `p` 中是 10、在 `q` 中是 1，于是抛出题面引用的原句。
- 不优化路径（`optimize=False`，即 C 实现 `c_einsum`）不检查跨操作数的尺寸，尺寸 1 交给 nditer 广播，因此可以当作期望结果的参照（静态推断，未运行）。
- 主要的范围不确定性：题面只给了一个不会走 BLAS 分支的例子。如果被求和的标签在一侧尺寸为 1，而这一步收缩选中了 `tensordot`（`einsumfunc.py:1105-1128`），`tensordot` 要求尺寸严格相等（`worktree/numpy/core/numeric.py:1276-1289`）。只放宽上述检查的实现在这类输入上会改报 `ValueError: shape-mismatch for sum`。题面描述段落泛指"singleton dimensions"，隐藏测试是否覆盖这类输入未知。

## 1. 需求表

| 编号 | 需求 | 类别 | 依据 |
|---|---|---|---|
| R1 | `np.einsum('ti,ti->i', np.ones((10, 2)), np.ones((1, 2)), optimize=True)` 不再报错，返回形状 `(2,)` 的数组 | 明示 | `user_prompt.txt:10-21` |
| R2 | 返回值等于不优化路径的结果；题面的全 1 输入应得 `[10., 10.]` | 可推知（题面只写形状，没写数值） | 不优化路径直接调 `c_einsum`（`einsumfunc.py:1065-1066`）。C 实现只在同一操作数内的重复标签上核对尺寸（`worktree/numpy/core/src/multiarray/einsum.c.src:2229-2236`）；跨操作数的对应关系由 `prepare_op_axes` 写成 `op_axes`（`einsum.c.src:2283-2328`），交给 `NpyIter_AdvancedNew`，输入操作数没有 `NPY_ITER_NO_BROADCAST`（`einsum.c.src:2863-2885`），所以尺寸 1 会被广播。公开测试也以 `optimize=False` 作对照（`worktree/numpy/core/tests/test_einsum.py:568-608`、`683-696`） |
| R3 | 与尺寸 1 出现的先后无关（`q` 在前、`p` 在后同样应接受） | 可推知 | 检查以先见到的尺寸为准（`einsumfunc.py:708-714`）；交换顺序后 base 同样报 `operand 1` |
| R4 | `optimize` 的其它取值同样适用：`True`、`'greedy'`、`'optimal'`、`(名称, 内存上限)`、显式 `['einsum_path', ...]`；base 下不传 `optimize` 也等于 `True` | 可推知 | 这些形式都会先经过同一检查（`einsumfunc.py:660-683`、`689-714`）；默认值是 `kwargs.pop('optimize', True)`（`einsumfunc.py:1062`） |
| R5 | 更一般的单例维广播也应与 `optimize=False` 一致：(a) 被求和的标签一侧为 1，且这一步走 `tensordot`；(b) 三个及以上操作数，经过中间收缩 | 仍有多种合理解释 | 题面描述段落是泛指（`user_prompt.txt:7`），但例子不属于 (a)(b)。(a) 的失败点在 `einsumfunc.py:772`（`_can_dot` 决定）、`1105-1128`（调用 `tensordot`）和 `numeric.py:1276-1289`（尺寸严格相等） |
| R6 | 公开函数 `np.einsum_path` 对同样输入是否也应返回路径而不报错；如果返回，代价估算用哪个尺寸 | 仍有多种合理解释 | `einsum` 通过 `einsum_path(..., einsum_call=True)` 实现（`einsumfunc.py:1088-1089`）；题面只提 `einsum` |
| K1 | 真正不兼容的尺寸（两边都不为 1 且不相等）仍报 `ValueError` | 可推知（保留旧行为） | 现有检查的用意（`einsumfunc.py:698-714`）；C 路径同样拒绝；公开测试要求同一操作数内 `'ii'` 配 `(2, 3)` 在 `optimize=True/False` 下都报 `ValueError`（`test_einsum.py:82-86`） |
| K2 | `optimize=False`（`c_einsum`）的行为不变 | 可推知 | 题面不涉及 C 路径，而它本来就能处理尺寸 1 |
| K3 | 现有公开测试保持通过，包括 `TestEinSumPath` 对具体路径的断言 | 可推知 | `test_einsum.py:776-900`；这些用例的维度都不为 1（`test_einsum.py:10-14`），只改变尺寸 1 情形的实现不应影响它们 |
| — | 报错文本、`einsum_path` 打印的报告内容 | 无约定 | 题面只引用了 bug 情形下的旧消息 |

## 2. 合理实现范围

- 修改位置：失败点都在纯 Python 文件 `worktree/numpy/core/einsumfunc.py`。C 路径本来就支持尺寸 1 广播，不需要改 C。
- 下面几类思路在数值上等价。只要结果与 `optimize=False` 一致，都应接受：
  1. 放宽 `einsum_path` 的尺寸检查，接受"1 对 N"（任意顺序），在尺寸字典里记录非 1 的尺寸用于代价估算；另外，当被求和的标签在两侧尺寸不一致时，这一步不走 `tensordot`，改交 `c_einsum`。
  2. 在路径计算前预处理操作数：对与其它操作数尺寸不一致（1 对 N）的带标签轴，去掉（squeeze）或显式展开（如 `np.broadcast_to`），让后续各步（包括 `tensordot`）看到一致的尺寸。
  3. 在 `tensordot` 分支内部，先把两侧的被求和轴广播到一致尺寸再调用。
  4. 在 `einsum` 中检测到单例维广播时整体退回 `c_einsum`。这能满足 R1-R4；`einsum_path` 本身（R6）是否仍报错取决于具体写法，题面没有约定。
- 未约定、应允许不同的地方：报错文本（包括是否带上尺寸）；尺寸字典记哪个值；中间结果的标签顺序（`einsumfunc.py:778-779` 按尺寸排序）；选出的收缩路径；`einsum_path` 打印的 FLOP 数和 "Largest intermediate"。
- 边界：
  - 把 `optimize` 的默认值改成 `False` 修不了显式 `optimize=True`，还会违背 1.14.0 发布说明写明的默认优化行为（`worktree/doc/release/1.14.0-notes.rst:453-458`）。
  - 无条件绕过优化（任何输入都退回 `c_einsum`）数值上能过，但会让 `optimize` 失去作用，背离文档说明的用途（`einsumfunc.py:865-869`、`930-937`）。我认为这不算合理实现。
- 我没有推测标准答案，也不判断隐藏测试覆盖了 R5、R6 的哪些部分。

## 3. 题面质量与初态线索

### 3.1 三类题面质量观察

1. **题面是否给出或强烈暗示修法：没有。** 示例是失败的调用，不是修好的实现。"handle the singleton dimension by broadcasting"（`user_prompt.txt:21`）只说明了语义。定位很直接：报错文本对应 `einsumfunc.py:710-711`。不过这句在源码里拆成两行（`"...does "` / `"not match previous terms."`），整句 grep 搜不到，搜 `Size of label` 可以找到。题面没有提示 `tensordot` 分支的问题。
2. **报错能否从 base 源码读出：能，逐行对得上。** 调用链如下：
   - `einsum` 取 `optimize=True`（`einsumfunc.py:1062`），调用 `einsum_path`（`1088-1089`）。
   - `einsum_path` 把 `True` 映射成 `'greedy'`（`660-662`），解析得到 `input_list = ['ti', 'ti']`（`689-693`）。
   - 第 0 个操作数记下 `t=10`；第 1 个操作数的 `t=1` 与之不等，抛出 `"Size of label 't' for operand 1 does not match previous terms."`（`706-712`）。这与 `user_prompt.txt:26` 一字不差。
3. **示例在 base 接口下是否说得通：说得通。** `optimize=True` 是有文档的参数（`einsumfunc.py:865-869`）。有两处值得留意，但都不妨碍开发：
   - 题面说问题出现在使用 `optimize=True` 参数时。实际上 base 的默认值就是 `True`（`einsumfunc.py:1062`、文档 `869`、发布说明 `1.14.0-notes.rst:453-458`），不传 `optimize` 也会触发。但同一个 docstring 的签名行写的是 `optimize=False`（`einsumfunc.py:823-824`）。这是 base 原有的文档矛盾，可能让解题者误以为默认调用不受影响。
   - 题面说广播本应能处理单例维，而 `einsum` 的 docstring 写着 `einsum` 默认不允许广播、要用省略号开启（`einsumfunc.py:902-907`）。那段说的是未标注的额外维度；带标签的尺寸 1 维在 C 实现里确实会被 nditer 广播（见 R2 的依据）。所以期望行为的依据是"与不优化路径一致"，不是文档承诺。题面的期望方向写得明确，不构成歧义，但读了文档的解题者可能会犹豫。
- 补充：题面示例用全 1 输入，数值上区分力弱。例如完全忽略 `q` 的错误实现也会得到 `[10., 10.]`。第 4 节的 C4 改用随机数并与 `optimize=False` 比较。

### 3.2 `public_hints` 分类（`public_bundle.json:15`）

- **题目需求**：修复仓库里的 issue；找到根因，修改非测试源码。
- **给解题者的操作指令**：不修改仓库测试文件；测试只跑窄范围；在 `/testbed` 下用 `python -m pytest`；只用已安装的包；完成后简短总结并停止调用工具。
- **环境事实声明**：仓库在 `/testbed`，bash 已在该目录；`/testbed/.venv` 是 Python 环境，`python` 和测试工具都指向它；不联网；可能没有 `pip`；另有一组测试负责评判。
- **对合法解法的影响**：没有实质限制。修复落在非测试源码 `einsumfunc.py`，不需要新依赖。"另有一组测试负责评判"与 `worktree/run_tests.sh:1` 指向的 `r2e_tests` 一致（该目录不在工作树里）。提示把题面称作"a real GitHub issue"，但 R2E 题面是自动生成的；这只是元信息，不影响解题。`environment_brief.md:13` 说包没有装进 venv、裸 `pytest` 收集会失败，与提示要求使用 `python -m pytest` 一致。

### 3.3 初态、定位入口与缺失信息

- **初态**：`worktree_manifest.json` 的 `initial_diff.bytes = 0`，说明镜像初态相对 base 没有改动任何跟踪文件。未跟踪文件有两个：`run_tests.sh`（已包含，内容为 `... -m pytest -rA r2e_tests`）和 `install.sh`（列在 `untracked_missing`，内容不可见）。两者都不影响题意。
- **复现与调查入口**：足够。题面示例可以直接运行；调用链集中在 `einsumfunc.py` 一个文件里；`optimize=False` 可以当现成的参照答案。
- **真正会阻碍开发的缺失信息**：没有。需要解题者自己判断的是范围，即 R5、R6（`tensordot` 分支、多操作数、`einsum_path` 本身）。这会影响隐藏测试的结果，但不妨碍开发；读 `_can_dot` 和 `tensordot` 属于正常读代码。

## 4. 开发需求表

| 操作 / 资产 / 服务 | 公开依据 | `environment_brief.md` 支持到哪一层 | 缺口 | 最小命令 |
|---|---|---|---|---|
| 导入 numpy（源码树加上就地编译的扩展） | `INSTALL.rst.txt:60-62`（`build_ext --inplace`）；`.gitignore:42,111` 忽略 `*.so` 和 `numpy/version.py`，所以工作树里没有 | 写明了解释器（`/testbed/.venv/bin/python`，3.7.9），以及 `/testbed` 必须在 `sys.path` 上（第 10、13 行），暗示容器里已就地编译 | 静态材料无法确认 `.so` 和 `numpy/version.py` 在容器里存在 | C1 |
| 复现原 bug（公开 API） | `user_prompt.txt:10-27`；`einsumfunc.py:706-712` | 足够（纯 Python 调用，不需要网络） | 无 | C2 |
| 参照语义（`optimize=False`，即 `c_einsum`） | `einsumfunc.py:1065-1066`；`einsum.c.src` 见 R2 | 足够 | "C 路径能广播"来自读代码，未运行 | C3 |
| 修改 `numpy/core/einsumfunc.py` | 纯 Python 文件；从源码树导入，改完即生效 | 解题身份 agent（uid 54321）可写 `/testbed`（第 12 行） | 无 | — |
| 范围检查（广播 × BLAS 分支 × 多操作数） | `einsumfunc.py:266-372`、`772`、`1105-1128`；`numeric.py:1276-1289` | 足够（数组都很小，2 CPU / 4 GiB 够用） | 题面没有约定 R5 是否在范围内 | C4 |
| 公开测试 `numpy/core/tests/test_einsum.py` | `pytest.ini`；`numpy/conftest.py:11` 导入已编译的 `numpy.core.multiarray_tests` | 写明要用 `python -m pytest`（第 13 行） | pytest 版本未知；venv 里有没有 `pytest-env` 插件也未知（`pytest.ini` 有 `env =` 键，缺插件时一般只出配置警告） | C5 |
| 修改 C 并重新编译 | `INSTALL.rst.txt:60-62` | 没有提到编译器；`install.sh` 不在工作树里 | 编译工具链未知；本题不需要改 C | 不建议照跑 |
| 隐藏测试 | `worktree/run_tests.sh:1` 指向 `r2e_tests` | — | 解题者看不到，属于正常情况 | — |
| 网络 / pip | `public_hints`；`environment_brief.md:11` | 明确没有 | 本题不需要 | — |

所有命令都在 `/testbed` 下原样运行。

**C1 环境探针（建议，未执行）**

```bash
cd /testbed && python -c "import sys, numpy; print(sys.version.split()[0], numpy.__version__, numpy.__file__)"
```

预计输出 `3.7.9 1.15.0.dev0+… /testbed/numpy/__init__.py`（版本串的具体格式未核），修复前后相同。

**C2 主复现，经公开 API，区分修复前后（建议，未执行）**

```bash
cd /testbed && python -c "import numpy as np; p = np.ones((10, 2)); q = np.ones((1, 2)); r = np.einsum('ti,ti->i', p, q, optimize=True); print(r, r.shape)"
```

- 修复前：traceback 最后一行为 `ValueError: Size of label 't' for operand 1 does not match previous terms.`，由 `numpy/core/einsumfunc.py` 的 `einsum_path` 抛出。
- 修复后：`[10. 10.] (2,)`。

**C3 参照，修复前后都应成功（建议，未执行）**

```bash
cd /testbed && python -c "import numpy as np; print(np.einsum('ti,ti->i', np.ones((10, 2)), np.ones((1, 2)), optimize=False))"
```

预计修复前后都输出 `[10. 10.]`。如果 base 下这条也报错，说明我对 C 路径的判断不成立，R2 的参照需要重新核对。

**C4 扩展一致性检查（建议，未执行）**

一次跑完所有情况；每种情况单独捕获异常，不会中途退出。

```bash
cd /testbed && python - <<'EOF'
import numpy as np
np.random.seed(0)
cases = [
    ('ti,ti->i',     [(10, 2), (1, 2)]),          # 1 题面示例
    ('ti,ti->i',     [(1, 2), (10, 2)]),          # 2 交换操作数顺序
    ('ij,jk->ik',    [(2, 3), (1, 4)]),           # 3 被求和的 j 一侧为 1，这一步会选 tensordot
    ('ij,jk,kl->il', [(2, 3), (1, 4), (4, 5)]),   # 4 三个操作数，经过中间收缩
]
for sub, shapes in cases:
    ops = [np.random.rand(*s) for s in shapes]
    try:
        ref = np.einsum(sub, *ops, optimize=False)
    except Exception as e:
        print('REF-ERR', sub, shapes, type(e).__name__, e)
        continue
    for opt in (True, 'greedy', 'optimal'):
        try:
            res = np.einsum(sub, *ops, optimize=opt)
            print('OK ' if np.allclose(res, ref) else 'BAD', sub, shapes, opt, res.shape)
        except Exception as e:
            print('ERR', sub, shapes, opt, type(e).__name__, e)
# 5 真正不兼容的尺寸：修复前后都应报 ValueError
for opt in (False, True):
    try:
        np.einsum('ti,ti->i', np.ones((10, 2)), np.ones((3, 2)), optimize=opt)
        print('NO-ERROR', opt)
    except ValueError as e:
        print('ValueError', opt, e)
EOF
```

预计结果（静态推演）：

| 情况 | 修复前（base） | 只放宽 `einsumfunc.py:706-712`、未动 `tensordot` 分支的实现 | 同时处理了 `tensordot` 分支的实现 |
|---|---|---|---|
| 1、2 | 各 3 行 `ERR … ValueError Size of label 't' for operand 1 does not match previous terms.` | 各 3 行 `OK … (2,)` | 各 3 行 `OK … (2,)` |
| 3 | 3 行 `ERR … ValueError Size of label 'j' for operand 1 …` | 3 行 `ERR … ValueError shape-mismatch for sum` | 3 行 `OK … (2, 4)` |
| 4 | 3 行 `ERR … ValueError Size of label 'j' for operand 1 …` | 3 行 `ERR … ValueError shape-mismatch for sum`（`greedy` 的最后一步、`optimal` 的第一步，都是 `j` 为 3 对 1 的 `tensordot`） | 3 行 `OK … (2, 5)` |
| 5 | `ValueError False …`（nditer 的广播错误，措辞未核）；`ValueError True Size of label 't' for operand 1 …` | 两行都是 `ValueError`，消息可能不同 | 同左 |

- 情况 1、2 在题面明示的范围内。情况 3、4 属于 R5，只用来看实现覆盖到哪一层，不据此判对错。
- 任何情况都不应出现 `REF-ERR`；如果出现，说明我对 C 路径的判断有误。

**C5 公开测试（建议，未执行）**

这是回归检查，不区分修复前后。

```bash
cd /testbed && python -m pytest numpy/core/tests/test_einsum.py -q
```

预计修复前后都全部通过（base 自带的测试）。现有公开测试没有覆盖"带标签的尺寸 1 跨操作数广播 + optimize"这种组合，所以修复前这条也不会失败。

## 5. 阅读范围

- **打开过的文件**：
  - 角色卡。
  - `PUBLIC_DIR` 下的 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`worktree_manifest.json`。manifest 只看了顶层键和文件清单，没有打开其中指向 `PUBLIC_DIR` 以外的 `initial_diff.source` 路径。
  - `worktree/` 下：
    - `numpy/core/einsumfunc.py`（全文）
    - `numpy/core/tests/test_einsum.py`（全文）
    - `numpy/core/__init__.py`（全文）
    - `numpy/core/src/multiarray/einsum.c.src`（1776-1935、2180-2340、2596-2925 行）
    - `numpy/core/numeric.py`（1255-1313 行，另有 grep）
    - `numpy/core/src/multiarray/multiarraymodule.c`（4340-4370 行，另有 grep）
    - `numpy/conftest.py`（前 40 行）
    - `numpy/core/tests/test_multiarray.py`（5515-5545 行）
    - `numpy/core/tests/test_numeric.py`（2725-2740 行）
    - `run_tests.sh`、`pytest.ini`（全文）
    - `setup.py`、`INSTALL.rst.txt`、`.gitignore`、`doc/release/1.12.0-notes.rst`、`doc/release/1.14.0-notes.rst`、`numpy/add_newdocs.py`、`benchmarks/`（只用 grep）
- **没查的范围**：
  - nditer 的广播实现（`nditer_*.c`）。"C 路径能广播"只是根据 `einsum.c.src` 调用 `NpyIter_AdvancedNew` 时传入的 `op_axes` 和标志推断的。
  - `einsum.c.src` 里的求和内核。
  - `numpy/linalg` 等其它调用者（grep 显示没有生产代码依赖 `einsum_path` 的尺寸检查）。
  - `install.sh`（不在公开包里）。
- **没接触的材料**：没有读任何私有材料、隐藏测试、gold 补丁、其它题的公开包或旧审查结论；没有联网，也没有查上游的后续提交。
- **可能的背景知识**：会话启动时，系统自动载入了仓库的会话说明文件（CLAUDE.md、AGENTS.md 等），里面没有本题的题解、测试或审查结论。作为语言模型，我可能对 numpy 上游历史有一般记忆；本文每条结论都附了工作树内的文件和行号，不依赖这类记忆。
- **限制**：
  - `user_prompt.txt` 只是 `render_user_prompt` 的静态渲染，不是捕获到的模型实际消息；`public_hints` 如何送达模型也没有核对。
  - `worktree/` 不是可运行的容器，缺少 `.git`、`.venv`、编译产物和 `numpy/version.py`。
  - 解释器、导入和测试能否跑通，只以 `environment_brief.md` 的描述为准。本文没有验证运行资源或开发条件。
