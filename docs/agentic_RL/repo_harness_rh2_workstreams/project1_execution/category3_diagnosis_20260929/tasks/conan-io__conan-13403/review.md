# conan-io__conan-13403 独立复核

2026-09-29 / 独立复核者（Claude 子代理，不继承作者上下文）。初判见同目录 [review_initial.md](review_initial.md)，写于读作者材料之前，之后未改。

**总判断：部分同意。** 我同意作者对原题的诊断和处置：原测试有 T1 误拒，也有 T2 漏判，属于 S1；原版只能作问题定位；gold 的位置参数回归登记为 S2；两处边界判断（参数名、相对路径以 source 为基准）成立。**但修订测试 v2 目前还不能按 §5 验收**，有两处要先修：
- 一个同类错误候选在 v2 下仍得 1：用 `run(..., ignore_errors=True)` 吞掉 autoreconf 失败；
- v2 新增了一处没有公开依据的文案约束：失败断言用了 `match="autoreconf failed"`，会误拒一个合理实现。

两处都只需改几行测试。我用草案 v3 在同一候选集上验证过修法（见 §4）。

## 1. 复核范围与证据层级

- **镜像**：`c3keep/conan13403:src`，image ID `sha256:dffa4bbc…`，RepoDigest `xingyaoww/sweb.eval.x86_64.conan-io_s_conan-13403@sha256:6c7a9b7d…71da84`，与 ingest 冻结值一致。
- **材料**：
  - gold sha256 `5b3a40f0…fd10`，原 test_patch `e6811f47…d433`，都从 ingest bundle 直接取出，与作者和历史记录一致；
  - v2 为 `revised_test_v2.patch`，sha256 `e3836c11…421c59f9`。作者 `formal_revised_v2/audit_*/materials.json` 里的 test_patch 我核过，sha256 也是这个值。
- **我的运行**：都在一次性容器里（`--rm --network none`），属于**私有对照**，不是正式评分；除特别注明外以 root 运行。
  - 命令：`pytest -n0 -rA -p no:cacheprovider conans/test/unittests/tools/gnu/autotools_test.py`。按 F2P `…::test_source_folder_works` 是否 PASSED 判分，P2P 为空。
  - 每个“候选 × 测试版本”组合都先 `git checkout -- . && git clean -fd`，再 `rm -rf /path`，然后应用补丁。
  - 每批运行都在 15 秒内结束。
- **补充检查**：
  - gold+v2 连跑 5 次，5 次 PASS；
  - gold 分别配 v2 和原测试，跑 `conans/test/unittests/tools/gnu/` 整个目录，都是 78 passed；
  - 以 uid 54322（`setpriv`）运行 gold+v2，PASS。
- **没有跑正式评分**：按要求不跑 `replay_grade.py`。作者的正式账本我读了，逐条核对见 §2。
- **我自己构造的候选**：只替换 `Autotools.autoreconf` 方法体，要点如下。完整脚本在会话的临时目录里，没有放进仓库。

| 候选 | 性质 | 与 gold 的差别 |
| --- | --- | --- |
| `rv_check` | 合理 | `args` 仍在首位；目录不存在时先抛 `ConanException("…folder '…' does not exist")`；其余同 gold |
| `rv_kw` | 合理 | 签名 `autoreconf(self, args=None, *, build_script_folder=None)`；调用 `chdir(self._conanfile, newdir=folder)` |
| `rv_wrap` | 合理（边界） | `args` 在首位；`run` 失败时 `raise ConanException("Error running autoreconf in '…'") from e`，报错时补上目录信息 |
| `w_argsdrop` | 错误：只对部分输入有效 | 指定目录时命令只剩 `autoreconf`，丢掉 toolchain 参数和用户 `args` |
| `w_twice` | 错误：依赖“只看最后一次调用” | 总是先在 source 执行一次，再在指定目录执行一次 |
| `w_mutate_src2` | 错误：改在错误的对象上 | `folders.source = build_script_folder`，再在 `source_folder` 执行。传 `None` 时会回落，所以原测试看不出来 |
| `w_ignore_errors` | 错误：吞掉错误 | 与 gold 相同，只是改成 `self._conanfile.run(command, ignore_errors=True)` |
| `w_restore_build` / `w_restore_build_ctx` | 错误：依赖调用者目录 | 结束后 `os.chdir(self._conanfile.build_folder)`，而不是回到调用者原来的目录 |
| `w_mkdir` | 边界（我不认为合理） | 目录不存在时先 `os.makedirs` |

## 2. 作者主张逐条核对

| 作者主张 | 判断 | 依据 |
| --- | --- | --- |
| 公开要求 1–5（result §1），不需要 R-f | 同意 | 题面原文点名了 `configure` 的 `build_script_folder`；base `configure()` 用 `os.path.join(source_folder, …)`；`conan/internal/api/new/autotools_lib.py:46-48` 在 `build()` 里无参调用 `autoreconf()`，我已核对 |
| “缺省改成调用者当前目录”这种读法不成立，不属 P5 | 同意 | 上面的模板依赖缺省为 source。原测试和 v2 都拒 `cwd_default` |
| 3 个合理实现被原测试误拒（T1） | **同意**，另有补充 | 作者正式账本：`conanfile_chdir`、`runcwd`、`oschdir` 都是 reward 0。我的对照结果相同，失败原因依次为 mock 首参不符、`ConanFileMock.run()` 不收 `cwd`、`FileNotFoundError: '/path/to/sources/subfolder'`。我另外发现 `rv_check`（夹具目录不存在）和 `rv_kw`（`Actual call: chdir(newdir=…)`）在原测试下也得 0。措辞上有一处要改：summary 说这 3 个实现“行为与 gold 完全一致”，但它们都把 `args` 留在首位，位置参数调用能用，而 gold 在这里报错。不影响结论 |
| `noenter` 等错误候选在原测试下得 1（T2b，S1） | **同意**，另有补充 | 作者正式账本：`noenter`、`relonly`、`buildlit`、`swallow_all` 都是 reward 1。我的对照结果相同，`swallow_run` 也得 1。我的候选里，`w_argsdrop`、`w_twice`、`w_mutate_src2`、`w_ignore_errors`、`w_restore_build_ctx` 在原测试下也都得 1 |
| `norestore`、`nofinally`、`fallback` 被原测试拒绝，只是因为夹具目录不存在 | 同意 | 我的对照中，前两者失败于 `FileNotFoundError`。`fallback` 失败是因为 `isdir('/path/to/sources/subfolder')` 为假，它回落到 source，于是 mock 断言不符；根源同样是夹具路径不存在 |
| §4 第 2 步不命中 | 同意 | 题面没有给出目录的字面值。`"subfolder"` 来自原 configure 测试，不是题面示例。build 目录这个缺口由第 4 步（`relonly`、`buildlit`）判定，归类正确 |
| G1：gold 破坏位置参数调用，判 S2 登记，不作修订依据 | **同意** | 我已实跑：gold 下 `autoreconf(['--install'])` 抛 `TypeError: join() argument must be str, bytes, or os.PathLike object, not 'list'`，base 与 `argsfirst` 正常，`args=` 关键字调用三者都正常。仓内 grep 没有位置调用。上游签名我已核对：PyPI 上 conan 2.0.3 sdist（sha256 `508f97b0…`）与 2.32.0 sdist（`59a03386…`）都是 `autoreconf(self, build_script_folder=None, args=None)`。v2 不锁参数顺序，gold 与 `argsfirst` 都得 1。生态中的使用频率未查（作者也写了未查） |
| 边界 1：参数名依据足够，`named` 得 0 不算误拒 | 同意 | 题面原文“`Autotools.configure` allows you to specify the `build_script_folder` location, but `Autotools.autoreconf` does not” |
| 边界 2：相对路径以 source 为基准，`rel_build` 得 0 不算误拒 | 同意，另有说明 | 依据是同名参数在 `configure` 上的语义（base docstring 与实现），属类比，不是题面直写。原测试已经锁了这个基准，v2 没有新增约束 |
| v2 下 18 个候选全部符合预期：gold 与 4 个合理实现为 1，noop 与 12 个错误候选为 0 | **同意这 18 个结果**，但**不同意据此验收** | 作者正式账本 18 条与 `failure_reasons.txt` 我已逐条核对；我在私有对照中复现了全部 18 个结果，失败行一致。不能验收的原因见 §3 |
| v2 各断言的依据（作者依据表） | 大部分同意，两处不同意 | “失败须抛出”这一行：依据写的是 `ConanFile.run` 默认 `ignore_errors=False`，但记录器根本不处理 `ignore_errors`，所以挡不住 `w_ignore_errors`。“明确不锁定……日志输出”：失败断言的 `match="autoreconf failed"` 实际上锁定了向上抛出的异常的文案 |
| §5 验收：“已知错误候选为 0：满足” | **不同意** | 现在已知一个同类错误候选 `w_ignore_errors` 在 v2 下得 1。见 §3 第 1 条 |
| 用途：原版只作问题定位；v2 落地后可申请训练候选 | 前半同意；后半为 conditional | 后半还需先修掉 §5 的两个阻断项，并重跑正负对照，此外还差 Codex 复核和 actor 开发条件核对 |
| 证据层级与“未查”清单 | 基本如实 | 我核对了以下各点：<br>- `evidence_manifest.json` 登记的文件中，405 个已复制，哈希全部一致；未复制的 177 个都在 `formal*/artifacts/`、`prepared/`、`private/` 下，与作者“只登记摘要”的说法相符；<br>- 正式账本中 uid 54322、`deny_all`、2 CPU、4 GiB 属实，`image_id_actual` 为 null；<br>- 镜像里确实没有 autoreconf；<br>- 作者说“18 个版本上 gnu 单测目录全部通过”，我只复验了 gold。<br>一处遗漏：§7 列了记录器与真实 `run` 的差别，但漏了 `ignore_errors` 这一项，而它正好会改变结论 |

## 3. 反例与新问题

我在私有对照中的结果如下（1 表示 F2P 通过）：

| 候选 | 原测试 | v2 | v3 草案 |
| --- | --- | --- | --- |
| base / gold | 0 / 1 | 0 / 1 | 0 / 1 |
| 合理：`argsfirst`、`conanfile_chdir`、`runcwd`、`oschdir` | 1、0、0、0 | 1、1、1、1 | 1、1、1、1 |
| 合理：`rv_check`、`rv_kw` | 0、0 | 1、1 | 1、1 |
| 合理（边界）：`rv_wrap` | 1 | **0** | 1 |
| 错误：作者的 12 个中除 `named`、`rel_build` 外的 10 个 | `noenter`、`relonly`、`buildlit`、`swallow_all`、`swallow_run` 为 1；`cwd_default`、`fallback`、`mutate_source`、`nofinally`、`norestore` 为 0 | 全 0 | 全 0 |
| 错误：`w_argsdrop`、`w_twice`、`w_mutate_src2` | 1、1、1 | 0、0、0 | 0、0、0 |
| 错误：`w_ignore_errors` | 1 | **1** | 0 |
| 错误：`w_restore_build`、`w_restore_build_ctx` | 0、1 | **1、1** | 0、0 |
| 边界：`named`、`rel_build`、`w_mkdir` | 0、0、1（以 uid 54322 运行为 0，因为无权创建 `/path`） | 0、0、0 | 0、0、0 |

1. **v2 挡不住 `ignore_errors=True`。**
   - v2 的 `_RunRecorderConanFile.run(self, command, stdout=None, cwd=None, **kwargs)` 把 `ignore_errors` 收进 `**kwargs` 后直接忽略，只要设了 `run_error` 就一律抛出。
   - 真实的 `ConanFile.run` 在 `ignore_errors=True` 时只返回退出码，不抛异常（`conans/model/conan_file.py:302`）。
   - 我用真实的 `ConanFile.run` 验证过：镜像里没有 autoreconf，命令以 127 退出。gold 抛出 `ConanException: Error 127 while executing`，`w_ignore_errors` 则静默返回 `None`。
   - 所以这个候选确实把失败藏了起来，违反作者 §1 第 5 条“命令失败时照常报错”，与作者本来要用 v2 挡住的 `swallow_run` 同类，却在原测试和 v2 下都得 1。
2. **v2 的失败断言锁了文案。**
   - `pytest.raises(Exception, match="autoreconf failed")` 要求向上抛出的异常文本里含有原始错误信息。
   - `rv_wrap` 并没有隐藏失败：它抛出带目录信息的新 `ConanException`，并用 `from e` 保留原异常。但因为文案不含 “autoreconf failed”，v2 判它 0。
   - 这是 v2 新增的误拒，原测试下它得 1。它属于 T1 所说的“精确文案没有公开依据”，也与作者列的“不锁定……日志输出”不一致。
3. **v2 只从 build 目录发起调用，分不清两种恢复行为**：“回到调用者原来的目录”和“结束后切到 build_folder”。
   - `w_restore_build`、`w_restore_build_ctx` 因此能通过 v2。
   - 公开依据是 `chdir` docstring 的 “temporary change”，以及 base 的行为。
   - 影响限于调用者不在 build 目录的情况，例如在 `source()` 里调用，或在外层 `with chdir(self, X)` 里调用。按 §4 第 4 步属边缘路径（T3/S2）。
4. **`w_mkdir` 被 v2 拒绝，但我认为可以接受。**
   - v2 要求目录不存在时不执行任何命令，这比“报错”更严。
   - 真实环境里，在新建的空目录中跑 autoreconf 会自己报错；v2 的记录器不模拟这一点，所以 `w_mkdir` 在 v2 下是 0。
   - 自动创建目录没有公开依据，还会在源码树里留下空目录，我不把它算作合理实现，因此不要求改动。
5. **原测试的漏判比作者列的更宽。** `w_argsdrop`、`w_twice`、`w_mutate_src2` 在原测试下也得 1。这进一步支持 S1，不改变处置；v2 能拦下这三个。

## 4. 阻断项（v2 验收前必须处理；不影响“原版 S1、只作问题定位”的结论）

1. **让记录器按 `ignore_errors` 的语义行事。** 签名改为 `run(self, command, stdout=None, cwd=None, ignore_errors=False, **kwargs)`；设了 `run_error` 且 `ignore_errors=True` 时返回非零值（如 1），不抛异常。依据：`ConanFile.run` 的公开签名与实现。修完后 `w_ignore_errors` 应为 0。
2. **去掉失败断言里的文案匹配。** 改为 `pytest.raises(Exception)`，再检查 `run_error` 在异常链中：沿 `__cause__`/`__context__` 能找到它即可。这样既接受原样抛出，也接受包装后抛出（`from e`，或在 `except` 块里抛出）；吞掉错误仍会被拒。修完后 `rv_wrap` 应为 1，`swallow_run`、`swallow_all` 仍为 0。

我在临时目录做了一版草案 v3：先在 v2 上做上面两处修改，再加上 §5 第 1 条非阻断建议。用它重跑了 28 个版本：base、gold、7 个合理实现、17 个错误候选（`w_mkdir` 计入错误候选）、2 个边界候选（`named`、`rel_build`）。结果是 gold 与 7 个合理实现为 1；base、17 个错误候选和 2 个边界候选都为 0；新增的几个 0 都失败在预期的断言上。v3 只是私有对照中的草案，**不是正式评分，也没有放进仓库**；采纳后需由作者重新生成补丁，并按 §5 重跑正式诊断评分。

## 5. 非阻断建议

1. 增加一次从非 build 目录发起的调用，例如先 `os.chdir(root)`，调用 `autoreconf(build_script_folder="subfolder")`，再断言当前目录仍是 `root`。这能拦下 `w_restore_build*`，成本一行，v3 草案已包含。
2. 在 result.md 里改两处措辞：
   - summary 的“行为与 gold 完全一致”改为“目录行为与 gold 一致，位置参数调用优于 gold”；
   - 依据表的“明确不锁定”清单改为与修订后的失败断言一致。
3. 可以把 `rv_check`、`rv_kw`、`rv_wrap`、`w_argsdrop`、`w_twice`、`w_mutate_src2`、`w_ignore_errors` 加进作者的候选集，重跑正式诊断评分，让验收表覆盖“合理但与 gold 不同”的更多写法。
4. §7 记录器与真实 `run` 的差别，补上 `ignore_errors` 一项。

## 6. 未查

- 真实 GNU 工具链端到端：镜像里没有 autoreconf、autoconf、automake。
- actor 开发条件。
- 位置参数用法在生态中的常用程度。
- 跨题关系。
- 作者 v1 草案的结果。
- 除 gold 以外的 17 个版本在 gnu 单测整目录下的结果。
- 作者的 `matrix.py`、`semantic_v1`/`semantic_v2` 私有矩阵输出：只读了 result.md 里的汇总，没有逐文件核对。
- 本次正式评分 grader profile 与 09-19 历史不同的原因。
