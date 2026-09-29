# conan-io__conan-13403 独立复核：初判（封存）

2026-09-29 / 独立复核者（Claude 子代理，不继承作者上下文）。本稿写于读作者 `result.md`、`evidence/` 与 `rh2/experiments/category3_cloud_20260929/conan13403/` 任何文件之前，写完不再修改。

**已读材料**：`s2/ingest/` 三份 bundle 中本题的题面、gold、test_patch、F2P/P2P；既有调查 `swegym_task_audit_20260920/quality_expansion_20260925/results/conan-io__conan-13403/` 下的 `card.md`、`public_read.md`、`analysis_before_history.md`（前半）、`review.md`、`old_findings_delta.md`（前半）；镜像 `c3keep/conan13403:src` 中 base 的 `conan/tools/gnu/autotools.py`、`conan/tools/files/files.py::chdir`、`conans/test/utils/mocks.py::ConanFileMock`、`conans/model/conan_file.py::run`、`conans/util/runners.py::conan_run`、原 `autotools_test.py`，以及仓内 `autoreconf` 调用点（grep）。**本稿没有任何运行结果**，下面全部是静态推导。

## (a) 公开核心要求与参数依据

- **核心要求**：`Autotools.autoreconf()` 要能由用户指定执行目录（`configure.ac` 所在处），尤其是构建目录，而不必改 recipe 的 `source_folder`。题面“user should be able to decide”意味着新增选项，不改默认值；无参调用仍在 `source_folder` 执行，是合理的旧行为保持。
- **参数名 `build_script_folder`**：题面原文“At least `Autotools.configure` allows you to specify the `build_script_folder` location, but `Autotools.autoreconf` does not”直接点名了 configure 的这个参数作为对照。我判断：沿用同名参数有**较强公开依据**（题面点名 + 同类 API 一致性），但题面没有写成硬性规定。换名实现会因关键字 TypeError 得 0；它是否算“合理实现被误拒”，我倾向“边缘”，不作为主要 T1 依据。
- **相对路径基准**：base 的 `configure()` docstring 写明“Subfolder where the configure script is located. If not specified conanfile.source_folder is used.”，实现是 `os.path.join(source_folder, build_script_folder)`。同名参数沿用同一基准，依据是这个类比，**不是题面直写**。题面标题说的是“build directory”，所以另一种读法是“相对 build_folder”；但若与 configure 同名却换基准会造成不一致，我认为 source 基准的依据足够，相对 build 的读法较弱。
- **绝对路径**：用户场景的自然写法是 `autoreconf(build_script_folder=self.build_folder)`（绝对路径）。`os.path.join` 遇到绝对路径会丢弃前缀，gold 支持。**这是题面核心实例，但原测试没有测**（见 b、c）。

## (b) 隐藏测试断言了什么

唯一 F2P `conans/test/unittests/tools/gnu/autotools_test.py::test_source_folder_works`，P2P 为空。

| 断言 | 性质 |
| --- | --- |
| configure 子目录 / 默认两条命令串（原有） | 结果行为（经 `ConanFileMock.run` 记录的命令串），旧行为保护 |
| `autoreconf(build_script_folder="subfolder")` 后 `chdir_mock.assert_called_with(autotools, "/path/to/sources/subfolder")` | **实现细节**：要求 (1) 通过模块属性 `conan.tools.gnu.autotools.chdir` 调用；(2) 第一个位置实参是 Autotools 实例本身；(3) 第二个位置实参恰为该字符串（`newdir=` 关键字或 `Path` 对象都不匹配）；(4) 只查工厂被调用，不查是否进入上下文、`run` 是否在该目录执行 |
| `autoreconf()` 后 `chdir_mock.assert_called_with(autotools, "/path/to/sources")` | 同上，默认目录的“调用意图” |
| 末次 `conanfile.command == 'autoreconf -bar foo'` | 结果行为：toolchain 的 `autoreconf_args` 仍进入命令 |
| 夹具：source 设为不存在的 `/path/to/sources` | 隐含约束：任何不经被 mock 的 `chdir` 而真实切目录的实现（`os.chdir`、局部导入的 `chdir`）都会 FileNotFoundError；任何做存在性检查的实现都会失败 |
| `ConanFileMock.run(command, win_bash, subsystem, env, ignore_errors)` 无 `cwd` 形参 | 隐含约束：用真实 `ConanFile.run(cwd=...)`（base 已支持）实现的解会 TypeError |

结论：目录这一核心行为**完全靠 mock 调用形状判定**，没有任何对“实际执行目录”的断言。

## (c) 可能误拒的合理实现 / 可能得 1 的错误实现（均未运行，待第二步核实）

可能被误拒（T1 候选）：
1. `with chdir(self._conanfile, folder)`：按 `chdir` 自身 docstring（“conanfile: The current recipe object. Always use self.”）传 recipe，比 base 的 `chdir(self, ...)` 更合文档；首参不匹配而失败。**依据最强**。
2. `self._conanfile.run(command, cwd=folder)`：真实 `ConanFile.run` 有 `cwd`，行为等价；mock 的 `run` 不收 `cwd`，且 `chdir` 未被调用。
3. 直接 `os.chdir` + try/finally，或局部 `from conan.tools.files import chdir`：夹具目录不存在 → FileNotFoundError。
4. 目录不存在时先抛清晰 `ConanException` 的实现：夹具目录不存在 → 失败。属于“更完整的修复被惩罚”，但依据弱于 1–3。
5. 换参数名：见 (a)，边缘。

可能得 1 的错误实现（T2 候选）：
1. **noenter**：`chdir(self, folder)` 调用但不 `with`，或 `with chdir(...): pass` 后在外面 `run` —— 实际不切目录，mock 断言照样满足。属 §4 第 3 步退化候选。
2. **字符串拼接**：`source_folder + "/" + build_script_folder` —— 相对 "subfolder" 正确，绝对 `self.build_folder` 变成 `/src//abs/build`，**恰好违反题面核心场景**；原测试只用相对值，会放过。按 §4 第 4 步（同一核心要求的其它实例）或第 1 步（构建目录这一核心实例无直接断言）应判 S1。
3. **改 `source_folder`**：`self._conanfile.folders.source = build_script_folder` 再按 source 切目录 —— 传 None 时回落 base，测试顺序（先 configure 后 autoreconf）看不到副作用，得 1；但之后的 `configure()`、`package()` 等都被改到新目录，违反题面“不必改 source folder”。属依赖顺序 / 作用在错误对象上。
4. **吞错误**：`try: ... except Exception: pass` 包住 run —— mock 的 run 不抛，得 1；违反 base 与 configure 都有的“命令失败即抛出”公开行为。
5. **指定目录时丢 args**：原测试只在默认调用后查命令串，得 1。

## (d) gold 回归

- gold 把签名从 `autoreconf(self, args=None)` 改为 `autoreconf(self, build_script_folder=None, args=None)`。旧的合法位置调用 `autoreconf(["--install"])` 会把列表绑定到 `build_script_folder`，`os.path.join(source_folder, list)` 在 `run` 前 TypeError。空列表位置调用落默认分支，不受影响；`args=` 关键字调用不受影响。
- 仓内调用点（grep）只有无参与 `args=[...]` 关键字两种，没有位置调用。gold 的顺序与 `configure(build_script_folder=None, args=None)` 一致，属有意的 API 对齐（上游最终接受的签名我记忆中亦如此，但**本轮未联网核实**）。
- 严重度：公开签名的兼容性破坏，但只影响“非空位置 args”这一不常见调用形态 → 按 §4 第 4 步属边缘路径，**S2（G1 → T3 登记）** 合理。它不是处置依据：原测试既不要求也不惩罚位置兼容；把 `args` 留在首位的兼容实现同样能过。

## (e) 初判处置

- T1（mock 形状、首参对象、夹具目录不存在、mock run 无 `cwd`）+ T2（noenter 退化候选得 1；绝对构建目录这一核心实例无断言）→ **S1**。
- 修订方向：**R-e**（把 `chdir` mock 换成真实临时目录，在 `run` 时记录 `os.getcwd()`，覆盖默认、相对子目录、绝对构建目录三例，并核对调用后目录恢复）为主，外加 **R-c** 补绝对构建目录这一非示例核心实例。新断言只能以“实际执行目录 / 命令串 / 旧行为”判，不以 helper 名或调用对象判。
- “目录不存在须报错”：base 行为是 `os.chdir` 抛错；静默回落到别处执行会在错误目录跑 autoreconf，因此“必须以某种异常失败”有依据，但**不得限定异常类型**（FileNotFoundError / ConanException 都应接受）。“失败须抛出且恢复目录”：`chdir` docstring 写明“temporary change”，base 与 configure 都让 run 的异常上抛，有依据。“相对路径以 source 为基准”：依据是 configure 同名参数类比，足够但应在理由里写明是类比。
- 当前用途：SWE-Gym 暂无修订机制（D6），误拒未消解 → **仅作问题定位**，不进能力比较分母与训练；修订版测试可作为机制落地后的候选，按 §5 验收。位置参数回归按 S2 登记。
