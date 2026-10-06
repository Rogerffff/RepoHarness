# conan-io__conan-13403 修订版 v3 聚焦复核

2026-09-30 / 聚焦复核者（Claude 子代理，不继承作者与首轮复核者的上下文）。对象：`revised_test_v3.patch`（sha256 `6719883b…6151`）。依据：首轮复核 [review.md](review.md) 的阻断 1、2 与非阻断建议，结论页 [result.md](result.md) §4 的 v3 小节与 §6。

**总判断：部分同意。阻断项 2 项。** 两项都在 v3 的同一段失败断言里（第 104–116 行），改写这一段即可同时解决，改法已在私有对照中验证。

- **同意的部分**：
  - 首轮两项阻断针对的具体问题已解决：记录器按真实 `ConanFile.run` 处理 `ignore_errors` 和不存在的 `cwd`，`w_ignore_errors` 为 0；失败断言不再匹配文案，`rv_wrap` 为 1；
  - 新增的“从非 build 目录发起调用、调用后回到原目录”有公开依据，没有误拒；
  - 作者 v3 的 29 份正式账本与结论页、`failure_reasons.txt` 逐项一致。
- **还不能按 §5 验收的两处**：
  1. **失败断言过松。** 设了失败之后，记录器让每一次执行都失败，不论在哪个目录。v3 只检查“有异常传出”，看不到“换个目录重跑”。
     - 反例：`w3_fallback_on_fail`、`w3_fallback_code`，在所选目录失败后改到 source 目录重跑。两者在 v3 下得 1。
     - 用真实 `ConanFile.run` 复现：在题面场景里（build 目录的 configure.ac 有错，source 目录的正常），它们都不报错，并且改在 source 目录执行。
  2. **失败断言过严，这是 v3 新引入的。** 新条件“原异常在 `__cause__`／`__context__` 链中，或实现拿到过失败码”没有公开依据。
     - 反例：`r3_deferred_raise`、`r3_restore_then_raise`，都是先恢复目录，再在 `except` 块之外抛出含原错误信息的新异常。两者 v2 下为 1，v3 下为 0；真实运行时行为与 gold 相同。
     - 在 41 个候选上，这个条件没有拦下任何错误候选。
- **修法**：私有草案 [`v3_fix`](../../../../../../../rh2/experiments/category3_cloud_20260929/conan13403/review_v3/tests/v3_fix.patch)。失败场景改为从 root 发起，并断言三件事：
  - 抛出异常，不限类型与文案；
  - 失败的命令只在所选目录执行了一次；
  - 调用者目录已恢复。

  同时删掉异常链条件。41 个候选分别以 root 和 UID 54322 运行，结果符合预期（§5）。

## 1. 核对范围与证据层级

- **材料**：
  - v3 补丁的 sha256 为 `6719883b…6151`，与 `materials_revised_v3.json` 的 `revised_patch_sha256`、29 份 `audit_*/materials.json` 中 test_patch 的摘要一致（脚本核对）；
  - gold 为 `5b3a40f0…fd10`，原 test_patch 为 `e6811f47…d433`。
- **镜像**：`c3keep/conan13403:src`，image ID `sha256:dffa4bbc…`，RepoDigest `…@sha256:6c7a9b7d…71da84`；`/testbed` 位于提交 `55163679`。
- **私有对照**（不是正式评分）：
  - 运行环境：一次性断网容器（`docker run --rm --network none`），默认以 root 运行。v3 及三个私有变体又以评分 UID 54322（`setpriv`）各跑了一遍。
  - 每个“候选 × 测试版本”组合的步骤：先 `git checkout -- . && git clean -fd`、`rm -rf /path`；再依次套候选补丁和测试补丁；然后运行 `pytest -n0 -rA -p no:cacheprovider conans/test/unittests/tools/gnu/autotools_test.py`。
  - 判分：F2P `test_source_folder_works` 为 PASSED 记 1，否则记 0；P2P 为空。
  - 规模：root 下 41 个候选 × 6 个测试版本，共 246 次。6 个版本是原测试、v2、v3，以及三个私有变体：
    - `v3_nochain`：只删掉异常链条件；
    - `v3_fix`：阻断项的修法；
    - `v3_fix_plus`：`v3_fix` 再加非阻断建议 1。

    UID 54322 下跑了 v3 与三个私有变体，共 164 次，结果与 root 逐项相同。
  - 稳定性：gold+v3、gold+`v3_fix_plus` 各连跑 5 次，全部通过；gnu 单测整个目录，两种身份下都是 78 passed。
- **真实语义对照**（私有）：
  - 脚本 `real_run_demo.py` 调用真实的 `ConanFile.run`（经 `conan_run` 起子进程），并在 PATH 前放一个假的 `autoreconf` 脚本：当前目录的 configure.ac 含 `BROKEN` 时以 1 退出，否则以 0 退出。
  - 对 17 个候选，在 5 种失败场景下记录三件事：是否报错、假 autoreconf 实际在哪些目录执行、调用后的当前目录。
  - 用途：证明“错误候选”的判断来自候选本身的行为，而不是记录器造成的。
  - 另核对了真实 `ConanFile.run` 的两点：不存在的 `cwd` 在 `ignore_errors` 为 False 或 True 时都抛 `ConanException`；失败命令在 `ignore_errors=True` 时返回退出码，默认时抛 `Error N while executing`。
- **没有跑正式评分**（`replay_grade.py`、`replay_with_install_recipe.py`）。正式账本是读取归档后核对的，见 §2.3。
- **文件位置**：脚本、候选、私有测试变体与结果都在 [`review_v3/`](../../../../../../../rh2/experiments/category3_cloud_20260929/conan13403/review_v3/)，清单见 §8。

## 2. 首轮两项阻断的核对

### 2.1 阻断 1（记录器不理会 `ignore_errors`）：已解决

- **真实语义**（镜像源码）：
  - `ConanFile.run` 的签名是 `run(command, stdout=None, cwd=None, ignore_errors=False, env="", quiet=False, shell=True, scope="build")`（`conans/model/conan_file.py:284`）。命令返回非零且没有设 `ignore_errors` 时，抛 `ConanException("Error %d while executing")`；否则返回退出码（302–305 行）。
  - `conan_run`（`conans/util/runners.py:35-62`）会把 `Popen(..., cwd=cwd)` 抛出的任何异常包成 `ConanException("Error while running cmd\nError: …")`。这发生在检查 `ignore_errors` 之前。
- **v3 记录器**（第 25–36 行）：
  - `cwd` 不存在时，在记录之前就抛 `ConanException`，与 `ignore_errors` 无关；
  - 设了 `run_error` 时，`ignore_errors=True` 返回 1，否则抛出 `run_error`。

  这两点都与真实行为一致。
- **结果**：
  - `w_ignore_errors` 在 v3 下为 0，正式账本与私有对照都停在第 108 行 `DID NOT RAISE`；
  - 真实语义对照中，它在 5 个失败场景里都静默返回，确实吞掉了错误。
- **剩余差别**（不影响任何已知候选，不阻断）：
  - 记录器只接受前 4 个位置参数，其余必须用关键字传；真实签名允许按位置传 `env` 等参数；
  - `cwd=""` 被当作没有给出，真实的 `Popen` 会报错。

### 2.2 阻断 2（失败断言锁定文案）：`rv_wrap` 已放行，但替换条件引入了同类的新约束

- v3 去掉了 `match=`，`rv_wrap` 在 v3 下为 1（正式账本与私有对照一致）。
- 替换上来的条件（第 110–115 行）要求满足其一：原异常出现在 `__cause__`／`__context__` 链中；或者实现曾以 `ignore_errors=True` 拿到失败码。
- 这个条件实际上只拒绝一种写法，原因如下：
  - Python 在 `except` 块里抛出新异常时，会自动设置 `__context__`；
  - `raise … from None` 也保留 `__context__`，只是不显示。`r3_fromnone` 在 v3 下为 1，可以证明这一点；
  - 因此，唯一过不了的写法是**在 `except` 块之外**抛出新异常。
- 这正是 `r3_deferred_raise` 和 `r3_restore_then_raise` 的写法：v3 下为 0，停在第 115 行 `assert (False or 0)`；v2 下为 1。见 §5 阻断 2。

### 2.3 作者 v3 正式账本：29 份全部一致

- **脚本核对**：[`audit_ledgers.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/conan13403/review_v3/audit_ledgers.py) 逐份核对了以下各项，29 份全部符合：
  - reward 与结论页 §4 v3 表一致；
  - F2P 为 1/1 或 0/1，P2P 总数为 0；
  - `apply_ok`，参考缺席为 0，安装末命令 RC 为 0，测试 RC 与 reward 对应，清理成功；
  - grader 后缀为 `+c3-conan13403-autoreconf-folder-v3`；
  - UID 为 54322，网络为 `deny_all`；
  - 归档评测日志的 sha256 与账本记录一致；
  - 候选补丁的 sha256 与实验目录中的文件一致（gold 为 `5b3a40f0…`）；
  - `audit_*/materials.json` 中 test_patch 的摘要为 `6719883b…`；
  - 日志中的失败位置与 `failure_reasons.txt`、结论页的“失败位置”列一致。
- **人工核对**：另外逐份看了 11 份评测日志的 pytest 段：gold、noop、`rv_wrap`、`rv_retcode`、`rv_check`、`w_ignore_errors`、`swallow_run`、`nofinally`、`w_restore_build`、`fallback`、`w_mkdir`。失败行显示的源码分别是第 116 行 `assert real(os.getcwd()) == real(build)`、第 101 行 `… == real(root)`、第 92 行 `with pytest.raises(Exception):` 等，确实是 v3 的测试文件。
- **交叉核对**：
  - 29 个候选的私有对照结果与正式账本逐项相同；
  - `rerun_0930/evidence_manifest.json` 登记为已归档的 253 个文件，哈希全部一致；
  - `rerun_0930` 中原材料与 v2 的 `failure_reasons.txt`，也与我的私有对照一致。唯一差别是 `w_mkdir` 在原测试下：root 为 1，UID 54322 为 0（无权创建 `/path`），与首轮复核的记录相同。
- **一处表述提示**（不影响结论）：`failure_reasons.txt` 记的是日志里第一条 `E` 行，遇到异常链时它不是最终失败的那条断言。例如 `rerun_0930/formal_revised_v2` 的 `rv_wrap` 记为第 30 行 `ConanException: autoreconf failed`，实际失败在第 94 行的文案不匹配。结论页写的“失败在文案匹配处”是对的。

## 3. v3 新增或放宽断言的依据与过严检查

| 断言（v3 行号） | 公开依据 | 过严？ | 过松？ |
| --- | --- | --- | --- |
| 记录器处理 `ignore_errors` 与不存在的 `cwd`（25–36） | `ConanFile.run` 的签名与实现；`conan_run` | 否：没有合理候选因记录器失败 | 否 |
| 失败时 `pytest.raises(Exception)`，不匹配文案（108） | 公开要求 5“命令失败时照常报错” | 否 | **是**：不看命令在哪里执行，放过 `w3_fallback_*`（阻断 1） |
| 原异常在异常链中，或拿到过失败码（110–115） | 无。这是 Python 的异常链接机制，不是公开行为 | **是**：拒绝 `r3_deferred_raise`、`r3_restore_then_raise`（阻断 2） | 这一条本身不拦任何错误候选（见下文 `v3_nochain` 对照） |
| 从 root 发起调用，调用后回到 root（97–102） | `chdir` 的 docstring 写明“temporary change”；base 的 `with chdir(...)` 会恢复调用者原来的目录，不论它在哪里；题面作者自己就在外层 `with chdir(self, self.build_folder)` 里调用过 | 否：14 个合理候选都通过这一段 | 只覆盖成功路径，`w3_fail_restore_build` 得 1（非阻断 2） |
| 失败后当前目录恢复为 build 目录（116） | base `chdir` 的 finally | 否 | 同上：失败场景从 build 目录发起，分不清“回到原目录”和“切到 build 目录” |

- **异常链条件不起保护作用。** 失败的调用（第 109 行）与第 76 行成功的调用参数相同、调用者目录也相同，只差 `run_error`，所以此时传出的任何异常都是由这次失败触发的。这一条也区分不了“与失败相关”和“与失败无关”的异常：
  - 它接受 `w3_code_unrelated` 抛出的 `TypeError`：本意只是打警告，拼接 int 时出错；因为拿到过失败码，所以通过；
  - 它却拒绝 `r3_deferred_raise`，而后者的异常信息里带着原错误。

  私有对照 `v3_nochain` 只删掉这一条。与 v3 相比，只有这两个合理候选由 0 变 1；26 个错误或边界候选的结果全部不变。
- **沿用原测试的约束，不是 v3 新增。** 每次调用恰好执行一次，命令文本精确为 `autoreconf -bar foo`。因此在 shell 里写 `cd X && autoreconf` 的实现会被拒；原测试同样拒绝它，依据是 base 组合命令的方式和原测试的命令断言。

## 4. 本轮构造的候选与私有结果

候选只替换 `Autotools.autoreconf` 的方法体，由 [`make_candidates.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/conan13403/review_v3/make_candidates.py) 生成，补丁在 `review_v3/cands/`。下表是私有对照结果，1 表示 F2P 通过；root 与 UID 54322 的结果相同（原测试与 v2 只在 root 下跑过）。

| 候选 | 性质 | 写法 | 原测试 | v2 | v3 | `v3_fix` | `v3_fix_plus` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `r3_fromnone` | 合理 | `try/except` 把 `ConanException` 转成 `RuntimeError`，用 `raise … from None` 抛出 | 1 | 1 | 1 | 1 | 1 |
| `r3_calledprocess` | 合理 | 先校验目录，不存在就抛 `FileNotFoundError`；`run(cwd=, ignore_errors=True)`，返回码非零时抛 `subprocess.CalledProcessError` | 0 | 1 | 1 | 1 | 1 |
| `r3_validate_conf` | 合理 | 先检查目录里有 `configure.ac` 或 `configure.in`，再 `with chdir(self._conanfile, folder)` | 0 | 1 | 1 | 1 | 1 |
| `r3_deferred_raise` | 合理 | 失败时先记下异常，离开 `chdir` 后抛出含原信息的新 `ConanException` | 1 | 1 | **0** | 1 | 1 |
| `r3_restore_then_raise` | 合理 | 手写 `os.chdir`，在 `finally` 恢复目录后再抛出含原信息的新异常 | 0 | 1 | **0** | 1 | 1 |
| `w3_fallback_on_fail` | 错误 | 在所选目录失败时打警告，改到 source 目录重跑（异常写法） | 1 | 1 | **1** | 0 | 0 |
| `w3_fallback_code` | 错误 | 同上，返回码写法：拿到失败码后改到 source 目录重跑，仍失败才报错 | 0 | 1 | **1** | 0 | 0 |
| `w3_check_only_selected` | 错误（只在部分路径检查） | `ignore_errors=True`，只在指定了目录时检查返回码，缺省调用的失败被吞 | 0 | 1 | **1** | 1 | 0 |
| `w3_abs_swallow` | 错误（只在部分路径检查） | 绝对目录（题面的 build 目录）只返回退出码，不报错 | 1 | 1 | **1** | 1 | 0 |
| `w3_fail_restore_build` | 错误（边缘路径） | 成功时回到原目录，失败时切到 `build_folder` | 0 | 1 | **1** | 0 | 0 |
| `w3_code_unrelated` | 边界（可接受） | 拿到失败码后本意只打警告，拼接 int 时触发 `TypeError` | 1 | 1 | 1 | 1 | 1 |
| `w3_code_norestore` | 错误 | 返回码写法，失败时先抛出、没有回到原目录 | 0 | 0 | 0 | 0 | 0 |

作者与首轮复核者的 29 个版本也在同一批私有对照里：
- 原测试、v2、v3 下的结果都与正式账本一致（唯一差别是 `w_mkdir` 在原测试下的 root／UID 54322 差异，见 §2.3）；
- 在 `v3_nochain`、`v3_fix`、`v3_fix_plus` 下：
  - gold 与 8 个合理候选为 1；
  - noop 与 19 个错误或边界候选为 0，其中 `w_ignore_errors`、`swallow_run` 停在失败断言。

汇总如下（14 个合理候选含 gold；26 个错误或边界候选中，`w3_code_unrelated` 属于可接受的边界，不计入“放过”）：

| 测试版本 | 被误拒的合理候选 | 得 1 的错误或边界候选 |
| --- | --- | --- |
| 原测试 | `conanfile_chdir`、`runcwd`、`oschdir`、`rv_check`、`rv_kw`、`r3_calledprocess`、`r3_validate_conf`、`r3_restore_then_raise` | 13 个 |
| v2 | `rv_wrap` | `w_ignore_errors`、`w_restore_build`、`w_restore_build_ctx`，以及本轮的 5 个 |
| **v3** | `r3_deferred_raise`、`r3_restore_then_raise` | `w3_fallback_on_fail`、`w3_fallback_code`、`w3_check_only_selected`、`w3_abs_swallow`、`w3_fail_restore_build` |
| `v3_nochain` | 无 | 同 v3 |
| `v3_fix` | 无 | `w3_check_only_selected`、`w3_abs_swallow` |
| `v3_fix_plus` | 无 | 无 |

**真实语义对照**（真实 `ConanFile.run` 加假 `autoreconf`，调用者在 build 目录）：

| 候选 | build 目录有错（题面场景） | 相对子目录有错 | 缺省调用、source 有错 | 从 root 调用、build 有错之后的当前目录 |
| --- | --- | --- | --- | --- |
| gold | 抛 `ConanException`，只在 build 执行 | 抛出，只在 subfolder 执行 | 抛出 | root |
| `r3_deferred_raise` | 抛 `ConanException`（信息含原错误），只在 build 执行 | 同 gold | 同 gold | root |
| `w_ignore_errors`（参照） | **不报错** | **不报错** | **不报错** | root |
| `w3_fallback_on_fail`、`w3_fallback_code` | **不报错**（只打警告），先在 build、再在 source 执行 | **不报错**，先在 subfolder、再在 source 执行 | 抛出 | root |
| `w3_check_only_selected` | 抛出 | 抛出 | **不报错** | root |
| `w3_abs_swallow` | **不报错** | 抛出 | 抛出 | root |
| `w3_fail_restore_build` | 抛出 | 抛出 | 抛出 | **build** |
| `w3_code_unrelated` | 抛 `TypeError` | 抛 `TypeError` | 抛 `TypeError` | root |

`argsfirst`、`runcwd`、`rv_wrap`、`rv_retcode`、`r3_fromnone`、`r3_calledprocess`、`r3_restore_then_raise` 的行为与 gold 相同，只是异常类型或信息不同。机器上没有 autoreconf（退出码 127）时，除吞错候选外都会报错。

## 5. 阻断项

### 阻断 1：失败断言只检查“有异常传出”，放过“失败后改到别的目录重跑”

- **当前行为**：v3 第 107 行设了 `run_error` 之后，记录器让此后的每一次执行都失败，不论在哪个目录。第 108–116 行只检查“抛出了异常”和“目录已恢复”，不检查失败调用期间命令在哪些目录执行、执行了几次。
- **反例**：`w3_fallback_on_fail`、`w3_fallback_code`。它们在所选目录失败后打警告，改到 source 目录重跑。
  - 私有对照：v3 下为 1（root 与 UID 54322 相同），v2 下也为 1。
  - 真实对照：题面场景里（build 目录的 configure.ac 有错，source 目录的正常），两者都不报错，autoreconf 先在 build、再在 source 执行；相对子目录有错时，同样静默改到 source 执行。只有两个目录都失败时它们才报错，而这正是记录器模拟的情形。
- **违反的公开要求**：结论页 §1 第 1 条（在指定目录执行）和第 5 条（命令失败时照常报错）。
  - 在题面场景里，它退回 source 目录执行，正是题面要解决的问题。
  - 它与作者的 `fallback`（目录不存在时静默改在 source 执行）同类，只是触发条件从“目录不存在”换成了“命令失败”。v3 专门为 `fallback` 加了断言，却没有覆盖这个触发条件。
- **规则依据**：§5“已知相关的错误候选仍为 0”；§4 第 4 步。修复成本约一行，依据沿用已有断言，所以即使按 review-standards §10.5 的比例原则，也应在本轮修掉。
- **修法**：
  - 失败的调用之后，断言 `conanfile.runs[before:] == [(real(subfolder), 'autoreconf -bar foo')]`，即失败的命令只在所选目录执行了一次。依据与成功调用的第 84 行相同：原测试断言的是单条命令文本，base 也只执行一次。
  - 如果作者认为“恰好一次”过严，可以放宽为“至少执行一次，且全部在所选目录”，同样能拦下这两个反例（这是推导，没有单独运行）。
- **修后预期**（`v3_fix` 已验证）：
  - `w3_fallback_on_fail`、`w3_fallback_code` 为 0，停在这条新断言，日志中多出一次在 source 目录的执行；
  - gold 与另外 13 个合理候选仍为 1。

### 阻断 2：v3 新增的“异常链或失败码”条件没有公开依据，误拒合理实现

- **当前行为**：第 110–115 行要求原异常出现在 `__cause__`／`__context__` 链中，或者实现拿到过失败码。
- **反例**：
  - `r3_deferred_raise`：失败时先记下异常，离开 `chdir` 后抛出 `ConanException("autoreconf failed in '…': <原信息>")`；
  - `r3_restore_then_raise`：手写 `os.chdir`，在 `finally` 恢复目录后，再抛出含原信息的新异常。

  两者 v2 下为 1，v3 下为 0，停在第 115 行。在真实对照的 5 个失败场景里，两者的行为都与 gold 相同：抛 `ConanException`，信息中包含原错误；只在所选目录执行一次；调用者目录已恢复。
- **规则依据**：
  - T1 与 R-b：这是没有公开依据的实现细节；
  - §5“不新增误拒”；
  - 结论页自己写明“明确不锁定……异常文案”。

  这个问题由 v3 的修复本身引入，按 review-standards §10.5 第 6 条，属于仍可阻断的一类。这种写法比 `raise … from e` 少见，但“先清理、再报错”是常见写法。§3 已说明这一条不起保护作用，删掉它不损失任何拦截能力。
- **修法**：删掉第 110–115 行（`chain` 循环和相应的 `assert`），`pytest.raises(Exception)` 不再需要 `as raised`；记录器的 `failed_codes_returned` 随之不再使用，可以一并删掉。
- **修后预期**（`v3_nochain`、`v3_fix` 已验证）：两个反例为 1，其余结果不变。

### 合并修法与整体预期

把 v3 第 104–116 行替换为下面这段（即 `v3_fix`；完整文件见 [`tests/v3_fix.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/conan13403/review_v3/tests/v3_fix.py)）：

```python
        # A failing autoreconf is not hidden: an error is raised (any type and message), the
        # failing command ran once, only in the selected folder, and the current folder of the
        # caller is restored (here the caller is not in the build folder)
        conanfile.run_error = ConanException("autoreconf failed")
        os.chdir(root)
        before = len(conanfile.runs)
        with pytest.raises(Exception):
            autotools.autoreconf(build_script_folder="subfolder")
        assert conanfile.runs[before:] == [(real(subfolder), 'autoreconf -bar foo')]
        assert real(os.getcwd()) == real(root)
```

改为从 root 发起，还能顺带拦下 `w3_fail_restore_build`（见非阻断建议 2）。

`v3_fix` 的私有对照结果（41 个候选，root 与 UID 54322 相同）：
- gold 与另外 13 个合理候选为 1；
- base 为 0；
- 26 个错误或边界候选中，23 个为 0。另外 3 个得 1：`w3_check_only_selected`、`w3_abs_swallow` 见非阻断建议 1；`w3_code_unrelated` 是可接受的边界。

若连非阻断建议 1 一起采纳（`v3_fix_plus`），错误候选中只剩 `w3_code_unrelated` 得 1。采纳后仍需作者重新生成补丁，把本轮 12 个候选并入候选集，按 §5 重跑正式诊断评分。

**stop condition**：修订版的正式诊断评分满足以下三条后，本复核不再阻断。“还能想出别的反例”不构成继续阻断的理由。
- gold 与另外 13 个合理候选为 1，其中包括本轮的 5 个；
- noop 与错误候选为 0，其中阻断 1、2 的反例停在对应断言；
- 如果不采纳非阻断建议 1，`w3_check_only_selected`、`w3_abs_swallow` 登记为 T3；`w3_code_unrelated` 不计入。

**根因与熔断口径**：两项阻断在同一段断言里，根因相同。
- 这一段检查的是“以什么方式报错”（v2 查文案，v3 查异常链），而不是“命令在哪里执行、失败有没有如实报出”；
- 记录器的“此后每次都失败”模型，使得“有异常传出”不等于“所选目录的失败被如实报告”。

替代写法只检查行为，已经验证过，改动也不超出同一个测试函数。阻断 2 属于“修复本身引入的新问题”，是否按协作协议 §5 的修复循环熔断处理，由负责人决定。

## 6. 非阻断建议

1. **把失败场景扩到缺省目录与绝对 build 目录**（`v3_fix_plus`，在 `v3_fix` 基础上多约 6 行，对三种调用各断言一次）。
   - `w3_check_only_selected`（缺省调用的失败被吞）和 `w3_abs_swallow`（题面 build 目录的失败被吞）在 v3 与 `v3_fix` 下为 1，在 `v3_fix_plus` 下为 0。真实对照中，两者确实在相应路径上静默。
   - 这两种写法需要“按路径分别处理错误”，比阻断 1 的反例更刻意，按 §4 第 4 步的边缘情形登记为 T3 也可以。不过加上这部分没有带来新的误拒，14 个合理候选全部通过。
2. **`w3_fail_restore_build`**（失败时切到 `build_folder`）：失败场景从 build 目录发起时无法识别，v3 下为 1。
   - 影响范围是边缘路径（T3）：必须同时满足命令失败、调用者不在 build 目录、调用者捕获异常后继续执行。
   - 阻断 1 的修法把失败场景改为从 root 发起，顺带拦下了它（`v3_fix` 下为 0）。
3. **结论页同步**：
   - §4 依据表中“失败断言”一行，以及“明确不锁定”清单：改为“只要求报错，不限异常类型、文案和异常链”；
   - 候选集补入本轮 12 个候选；
   - §7 记录器差别补一句：设了 `run_error` 后，记录器让每次执行都失败，所以失败场景必须同时检查执行目录与执行次数。
4. **`failure_reasons.txt` 的抽取方式**：改为取最后一段回溯中的 `E` 行，或者另记失败断言所在的测试行号（原因见 §2.3）。
5. **把 `w3_code_unrelated` 登记为已知边界**：失败时它仍会中断构建（`TypeError`），只是信息有误导性。测试按设计不锁文案，不需要处理。

## 7. 未查

- 真实 GNU 工具链端到端：镜像里没有 autoreconf、autoconf、automake。真实语义对照用的是假 `autoreconf` 脚本，只验证目录、退出码和报错路径。
- `v3_fix`、`v3_fix_plus` 的正式诊断评分：按要求没有跑正式评分，需要作者重新生成补丁后按 §5 运行。
- 原测试与 v2 在 UID 54322 下的私有对照：只在 root 下跑过；v3 及三个变体在两种身份下都跑了。
- 作者 `matrix.py`、`semantic_v*` 私有矩阵输出的逐文件核对。
- `rerun_0930/formal`、`formal_revised_v2` 的账本：只读了 `failure_reasons.txt`，并与私有对照交叉核对，没有逐份做 §2.3 的字段核对。
- actor 开发条件、位置参数用法在生态中的常用程度、跨题关系：与首轮复核相同，都未查。
- Codex 复核。

## 8. 文件

目录：`rh2/experiments/category3_cloud_20260929/conan13403/review_v3/`

| 文件 | 用途 |
| --- | --- |
| `make_candidates.py` | 生成本轮 12 个候选补丁（`cands/`）与 3 个私有测试变体（`tests/`，`.py` 与 `.patch`） |
| `run_matrix.sh` | 私有对照驱动，在容器内运行；支持 `RUNAS=54322` |
| `real_run_demo.py` | 真实 `ConanFile.run` 加假 `autoreconf` 的语义对照 |
| `audit_ledgers.py` | 逐份核对作者 v3 正式账本、归档日志与结论页 |
| `summarize.py` | 汇总私有对照表，并比较 root 与 UID 54322 |
| `results/private_root.tsv` | 246 行，sha256 `f8da707e…` |
| `results/private_uid54322.tsv` | 164 行，sha256 `48d46601…` |
| `results/real_run_demo.jsonl` | 17 个候选，sha256 `d07ce11b…` |
| `results/logs/` | 15 份关键组合的 pytest 日志（阻断反例、修后结果等） |

候选与测试变体补丁的 sha256（前 8 位）：

| 补丁 | sha256 | 补丁 | sha256 |
| --- | --- | --- | --- |
| `r3_fromnone` | `64fa4676` | `w3_fallback_on_fail` | `fda91f24` |
| `r3_calledprocess` | `a47e121a` | `w3_fallback_code` | `9c590b6d` |
| `r3_validate_conf` | `8f470241` | `w3_check_only_selected` | `4e3c8f86` |
| `r3_deferred_raise` | `c4019764` | `w3_abs_swallow` | `998f1257` |
| `r3_restore_then_raise` | `4861da08` | `w3_fail_restore_build` | `a7de35c8` |
| `tests/v3_nochain.patch` | `1e5c1513` | `w3_code_unrelated` | `7cd399ce` |
| `tests/v3_fix.patch` | `e94665c1` | `w3_code_norestore` | `935a1cda` |
| `tests/v3_fix_plus.patch` | `2d5541f3` | | |
