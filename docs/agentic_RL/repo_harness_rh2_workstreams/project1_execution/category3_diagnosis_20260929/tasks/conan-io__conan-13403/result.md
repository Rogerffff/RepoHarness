# conan-io__conan-13403：第3类诊断结果

2026-09-29 / Claude（云端，第3类第二批主审）。原分类：第3类“已有具体疑点，缺辨别实验”。工作项：执行 base／gold／保留 args 首位的实现，核真实 cwd、命令与恢复。

**结论：问题和修法已明确，建议转第2类。**

- 旧题卡的三个疑点都已用实验回答：
  - 内部 mock 误拒合理实现：**成立**。3 个行为与 gold 完全一致的实现在原材料正式评分中得 0。
  - “调用 chdir 但不进入上下文”可以骗过测试：**成立**。该退化候选在原材料正式评分中得 1。
  - gold 破坏旧的位置参数调用：**成立**，但判为 S2 登记，不作修订依据（理由见 §3）。
- 另有两个新发现：
  - 测试没有题面本身的 build 目录场景，只对 source 下相对子目录有效的候选得 1；
  - 吞掉错误的候选也得 1。
- 修订草案 **v2**（R-e＋R-b＋R-c）：只替换测试补丁，测试 ID 与 F2P／P2P 名单不变。**gold 仍是正对照**。正式诊断评分中 18 个候选全部符合预期：gold 与 4 个合理实现为 1，noop 与 12 个错误候选为 0。
- 落地只需要 D6 的测试补丁替换，不需要调整参考分组，也不需要派生镜像。

## 1．公开要求

题面标题：“Can't specify Autotools.autoreconf() location to the build directory”。

- 用户要对 build 目录里的 `configure.ac` 运行 `autoreconf`，但不想为此改 recipe 的 source 目录。在外层 `with chdir(self, self.build_folder)` 里调用也不生效。
- 题面指出 `Autotools.configure` 有 `build_script_folder` 参数，`autoreconf` 却没有，并且被写死为 source 目录。

据此得到的公开要求：

1. `autoreconf` 可以指定执行目录。题面点名以 `configure` 的 `build_script_folder` 为参照，参数名和“相对路径以 source 目录为基准、绝对路径原样使用”的语义都来自这一参照（base `autotools.py:36-59`）。
2. **题面场景本身**是 build 目录，它通常是 source 之外的绝对路径。
3. 不指定时仍用 source 目录。base 的公开用法依赖这一点：`conan new autotools_lib` 模板（`conan/internal/api/new/autotools_lib.py:48`）与功能测试 `test_autotools_option_checking` 都在 `build()`（运行目录为 build 目录）里无参调用 `autoreconf()`。
4. 不需要修改 recipe 的 source 目录（题面原话）。
5. base 已有的相邻行为保持不变：
   - `args` 参数照常生效；
   - 目录切换是临时的，调用后回到原目录。模板在 `autoreconf()` 之后接着调用 `configure()` 和 `make()`，它们依赖当前目录；
   - 命令失败时照常报错。

**另一种读法不成立（不属 P5）**：把缺省改成“调用者当前目录”，确实能让外层 `chdir` 生效，但会让上述模板在 build 目录里找不到 `configure.ac`，与 base 的公开用法冲突。题面也没有提出这种改法。

题面陈述已在 base 上核实（见 §2（1）的 base 行：调用者在 build 目录时，base 仍在 source 执行），**不需要 R-f**。

## 2．实测

- **镜像**：`xingyaoww/sweb.eval.x86_64.conan-io_s_conan-13403:latest`，按原名经 `mirror.gcr.io` 拉取。RepoDigests 为 `sha256:6c7a9b7d…71da84`，与 ingest 冻结值一致。本机 image ID 为 `dffa4bbc…`，已打 `c3keep/conan13403:src` 标签。
- **配方**：09-19 修复目录中没有本题，使用原镜像，无派生配方。
- **运行环境**：Docker 29.3.1、overlay2、cgroup v1。
- **gold**：sha256 `5b3a40f0…fd10`，与历史一致。
- **原测试补丁**：sha256 `e6811f47…d433`，与历史一致。

### （1）私有行为矩阵（`semantic_control.py`：root、断网、一次性容器）

做法：
- 不 mock `chdir`，使用真实临时目录 `src/`、`src/sub/`、`build dir/`，每个目录都放一个 `configure.ac`；
- 把 `recipe.run` 换成记录器，记录命令执行时的实际目录。记录规则与 `ConanFile.run` 相同：给了 `cwd` 就用 `cwd`，否则用进程当前目录；
- 每个场景开始前，进程当前目录设为 build 目录；
- 不执行系统 autoreconf（镜像中没有 autoreconf、autoconf、automake）。

脚本为 [`matrix.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/conan13403/matrix.py)，汇总见 `evidence/semantic_v2/matrix_summary.txt`。

| 版本 | 缺省 | `args=` | 位置参数 `(['--install'])` | 相对 `sub` | 绝对 build 目录 | 其它绝对目录 | 目录不存在 | 命令失败 | 调用后目录 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| base | SRC | SRC | SRC | `TypeError`（无此参数） | 同左 | 同左 | 同左 | 同左 | 恢复 |
| **gold** | SRC | SRC | **`TypeError: join() argument must be str…`** | SRC/sub | BUILD | SRC/sub | 报错，不执行 | 抛出 | 恢复 |
| `argsfirst`（args 保持首位） | SRC | SRC | SRC | SRC/sub | BUILD | SRC/sub | 报错 | 抛出 | 恢复 |
| `conanfile_chdir` | 同 argsfirst | | | | | | | | 恢复 |
| `runcwd`（`run(cwd=...)`） | 同 argsfirst | | | | | | | | 恢复 |
| `oschdir`（try/finally） | 同 argsfirst | | | | | | | | 恢复 |
| `noenter` | **BUILD** | **BUILD** | `TypeError` | **BUILD** | BUILD | **BUILD** | **在 BUILD 执行** | 抛出 | 恢复（从未切换） |
| `relonly` | SRC | SRC | SRC | SRC/sub | **`FileNotFoundError`** | **`FileNotFoundError`** | 报错 | 抛出 | 恢复 |
| `buildlit` | SRC | SRC | SRC | SRC/sub | BUILD | **`FileNotFoundError`** | 报错 | 抛出 | 恢复 |
| `norestore` | SRC | SRC | SRC | SRC/sub | BUILD | SRC/sub | 报错 | 抛出 | **泄漏到 SRC 或 SRC/sub** |
| `nofinally` | 正常 | | | | | | 报错 | 抛出 | **失败后泄漏** |
| `fallback` | 正常 | | | | | | **静默改在 SRC 执行** | 抛出 | 恢复 |
| `swallow_all` | 正常 | | | | | | **不报错** | **不报错** | 恢复 |
| `swallow_run` | 正常 | | | | | | 报错 | **不报错** | 恢复 |
| `mutate_source` | SRC | | | SRC/sub，**并改写 recipe 的 source 目录**；此后缺省也变成 SRC/sub | | | | | 恢复 |
| `cwd_default` | **BUILD** | **BUILD** | **BUILD** | SRC/sub | BUILD | SRC/sub | 报错 | 抛出 | 恢复 |
| `named`（参数名 `folder`） | SRC | SRC | SRC | `TypeError`（无 `build_script_folder`） | | | | | 恢复 |
| `rel_build`（相对 build 目录） | SRC | SRC | SRC | **`FileNotFoundError`**（build/sub） | BUILD | SRC/sub | 报错 | — | 恢复 |

矩阵读法：
- 空格表示与 argsfirst 相同。
- 所有版本的命令文本都正确：`autoreconf --verbose`，传 `args` 时为 `autoreconf --verbose --install`。
- base 公开单测目录 `conans/test/unittests/tools/gnu` 在 18 个版本上全部通过。

**结论**：
- gold、`argsfirst`、`conanfile_chdir`、`runcwd`、`oschdir` 都满足 §1 的全部公开要求。其中 gold 只有位置参数调用失败。
- 其余构造各违反 §1 的至少一条，违反处已在表中加粗。

### （2）原材料正式评分

正式评分用 `replay_grade.py run`：grader UID 54322、deny_all、2 CPU／4 GiB，每次 12–23 秒。

| 候选 | reward | F2P | 失败原因（评分日志原文） | 行为判断 |
| --- | --- | --- | --- | --- |
| noop | 0 | 0/1 | `TypeError: … unexpected keyword argument 'build_script_folder'` | 与 09-19 历史一致 |
| gold | 1 | 1/1 | — | 与历史一致 |
| `argsfirst` | 1 | 1/1 | — | 正确；原测试不锁参数顺序 |
| `noenter` | **1** | 1/1 | — | **错误**：从不切换目录 |
| `relonly` | **1** | 1/1 | — | **错误**：题面的 build 目录场景失败 |
| `buildlit` | **1** | 1/1 | — | **错误**：只认 build_folder 这一个值 |
| `swallow_all` | **1** | 1/1 | — | **错误**：吞掉目录错误与命令失败 |
| `conanfile_chdir` | **0** | 0/1 | `Expected call: chdir(<…Autotools object…>, '/path/to/sources/subfolder')`／`Actual call: chdir(, '/path/to/sources/subfolder')` | **正确**，因 mock 首参身份被拒 |
| `runcwd` | **0** | 0/1 | `TypeError: ConanFileMock.run() got an unexpected keyword argument 'cwd'` | **正确**，因测试替身不支持公开的 `run(cwd=)` 被拒 |
| `oschdir` | **0** | 0/1 | `FileNotFoundError: … '/path/to/sources/subfolder'` | **正确**，因夹具目录不存在被拒 |
| `named` | 0 | 0/1 | `TypeError: … 'build_script_folder'` | 参数名有公开依据（§3 边界） |

- 全部 11 次运行：参考缺席 0，`apply_ok`，安装末命令 RC 0，清理成功。
- 下列错误候选只做了私有对照（`c3_f2p_original`），没有跑原材料正式评分：
  - `swallow_run` 通过原测试；
  - `norestore`、`nofinally`、`fallback`、`mutate_source`、`cwd_default`、`rel_build` 不通过。

  其中 `norestore`、`nofinally`、`fallback` 被拒，只是因为夹具的 `/path/to/sources` 不存在，不是因为测试检查了目录恢复或错误处理。

## 3．判定（v1 §3–§4）

- **T1（已由正式评分确认）**：`conanfile_chdir`、`runcwd`、`oschdir` 行为与 gold 一致，却被判 0。三处被拒的原因都没有公开依据：
  - mock 断言要求 `chdir` 的首参是 `Autotools` 对象。`chdir` 的文档反而写的是“The current recipe object”；
  - `ConanFileMock.run` 不接受 `cwd`，而公开的 `ConanFile.run(command, stdout=None, cwd=None, …)` 接受；
  - `/path/to/sources` 是不存在的路径，只能配合 mock 使用。
- **T2b（S1，§4 第 3 步）**：退化候选 `noenter` 在 gold 的修改位置写成：调用 `chdir(self, script_folder)`，但不进入上下文。它在原材料正式评分中得 1。
  - 违反的公开要求：指定目录与缺省 source 目录都不生效，命令始终在调用者当前目录执行；
  - 得分原因：`MagicMock.assert_called_with` 只检查调用参数，`@contextmanager` 生成器要进入上下文才会执行 `os.chdir`。
- **§4 第 4 步（S1）**：以下已构造候选得 1，但违反同一核心要求的其它实例：
  - `relonly`：用字符串拼接，只对 source 下的相对子目录有效，题面本身的 build 目录场景报 `FileNotFoundError`；
  - `buildlit`：只特判 build_folder 这一个值；
  - `swallow_all`：目录不存在或 autoreconf 失败都只打警告，然后继续。

  测试只有相对子目录 `"subfolder"` 这一个实例，没有题面所说的 build 目录。
- **§4 第 1 步**：核心要求只有间接断言（mock 调用参数），不检查真实执行目录与恢复。它的失效已由上面的第 3 步证实。
- **§4 第 2 步**：不命中。测试输入 `"subfolder"` 不是题面示例的字面值。
- **T6**：P2P 为空，已按规定做了第 3 步的退化探测。
- **G1，登记为 S2／T3**：gold 把新参数放在 `args` 之前，旧调用 `autoreconf(['--install'])` 在执行前就报 `TypeError`（私有矩阵）。不作修订依据，理由如下：
  - 题面没有涉及 `args`；
  - 本仓库公开代码中没有位置参数调用。grep 结果：模板与测试里都是无参或 `args=`；
  - 上游 conan 2.0.3 发布的就是 gold 的写法，到 2.32.0 仍未改动（PyPI sdist，sha256 分别为 `508f97b0…`、`59a03386…`）。

  修订版**不锁参数顺序**，gold 与 `argsfirst` 都得 1。该用法在 conan-center-index 等生态中的常用程度**未查**。
- **两处边界判断，供复核**：
  - **参数名**：题面原文点名 `configure` 的 `build_script_folder`，要求 `autoreconf` 同样提供，所以用别的参数名（`named`）得 0 不算误拒；
  - **相对路径基准**：以 source 目录为基准，是同名参数在 `configure` 上的既有语义，所以 `rel_build` 得 0 不算误拒。

  如果复核认为参数名依据不足，可按 R-f 补一句“与 `configure` 使用同名参数”，测试不用改。

## 4．修法（交第2类）：修订版测试草案 v2

### 草案文件

- 测试补丁：[`revised_test_v2.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/conan13403/revised_test_v2.patch)，sha256 `e3836c11…421c59f9`。
- 完整测试文件：[`revised_autotools_test_v2.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/conan13403/revised_autotools_test_v2.py)。
- 材料文件：[`materials_revised_v2.json`](../../../../../../../rh2/experiments/category3_cloud_20260929/conan13403/materials_revised_v2.json)，版本 `c3-conan13403-autoreconf-folder-v2`。
- 父版本：原 test_patch（`e6811f47…`）。中间有一版私有草案 v1（`revised_test_v1.patch`，`1e02583d…`），只做了私有对照：`buildlit` 与 `nofinally` 能通过 v1，v2 为此补了两处断言。

范围：`test_source_folder_works` 原位改写，测试 ID 不变，F2P／P2P 名单不变。`configure` 的两条原断言原样保留。

### 需求—断言依据表

| 断言 | 公开依据 | 拦下的错误候选 |
| --- | --- | --- |
| 去掉 `chdir` 的 mock，改用含 `configure.ac` 的真实目录，以及记录 `run` 实际执行目录的替身（兼容 `run(cwd=…)`） | R-e／R-b：mock 的首参身份、替身签名、虚构路径都没有公开依据 | 放行 `conanfile_chdir`、`runcwd`、`oschdir` |
| 在 build 目录中调用、不指定目录时，在 source 目录执行（调用两次，分别在指定目录调用之前和之后） | base 行为；模板与功能测试依赖；原测试的缺省断言 | `noenter`、`cwd_default`、`mutate_source` |
| 相对 `"subfolder"` → `source/subfolder` | `configure` 同名参数的语义；原测试 | `rel_build` |
| `build_script_folder=conanfile.build_folder, args=["--install"]` → 在 build 目录执行 `autoreconf -bar foo --install` | 题面场景；base 中 `args` 的组合方式；功能测试的 `args=` 用法 | `relonly` |
| 另一个绝对目录（`source/subfolder` 的绝对路径） | 题面“由用户决定”的一般表述；`configure` 的 `os.path.join` 语义 | `buildlit` |
| 每次调用恰好执行一次，命令文本精确 | 原测试断言 `autoreconf -bar foo`；base 的组合方式 | 在多个目录重复执行的实现 |
| 每次调用后，调用者当前目录仍是 build 目录 | base `chdir` 是临时切换；模板在 autoreconf 之后接着调用 configure/make | `norestore` |
| recipe 的 source/build 目录不被改写 | 题面“without having to change … the recipe's source folder” | `mutate_source` |
| 指定目录不存在时报错（不限异常类型），且不在任何目录执行 | base `chdir` 对不存在的目录报错；题面“由用户决定” | `fallback`、`swallow_all` |
| autoreconf 失败时异常照常抛出，且当前目录恢复 | `ConanFile.run` 失败时默认抛 `ConanException`（`ignore_errors=False`）；base `chdir` 的 finally | `swallow_run`、`nofinally` |

**明确不锁定**：参数顺序、参数是否只能用关键字传、用 `chdir` 还是 `run(cwd=)`、`chdir` 的首参、日志输出。

### v2 正式诊断评分

`replay_with_install_recipe.py --materials`，grader 后缀 `+c3-conan13403-autoreconf-folder-v2`，名单不变，每次 12–18 秒。

| 候选 | reward | 失败位置（修订测试行号） |
| --- | --- | --- |
| gold（正对照） | **1** | — |
| `argsfirst` | **1** | — |
| `conanfile_chdir` | **1** | —（原 0，误拒已纠正） |
| `runcwd` | **1** | —（原 0，误拒已纠正） |
| `oschdir` | **1** | —（原 0，误拒已纠正） |
| noop | 0 | 78：无此参数 |
| `noenter` | 0 | 79：缺省调用在 build 目录执行（原 1） |
| `relonly` | 0 | 78：绝对 build 目录 `FileNotFoundError`（原 1） |
| `buildlit` | 0 | 78：其它绝对目录 `FileNotFoundError`（原 1） |
| `swallow_all` | 0 | 87：目录不存在时没有报错（原 1） |
| `swallow_run` | 0 | 94：失败被吞 |
| `fallback` | 0 | 87 |
| `norestore` | 0 | 81：目录泄漏 |
| `nofinally` | 0 | 96：失败后目录泄漏 |
| `mutate_source` | 0 | 82：source 目录被改写 |
| `cwd_default` | 0 | 79 |
| `named` | 0 | 78（边界，见 §3） |
| `rel_build` | 0 | 78：`build/subfolder` 不存在（边界，见 §3） |

全部 18 次运行：参考缺席 0，`apply_ok`，安装末命令 RC 0，清理成功。每个错误候选都失败在针对它的那条断言上（`formal_revised_v2/failure_reasons.txt`）。

**R-b／R-c／R-e 验收（v1 §5）**：

| 验收项 | 结果 |
| --- | --- |
| 正对照（gold）为 1，noop 为 0 | 满足 |
| 误拒已纠正 | 满足：3 个合理实现从 0 变为 1 |
| 已知错误候选为 0 | 满足：原材料得 1 的 4 个错误候选均为 0 |
| 核心要求有直接断言 | 满足：断言真实执行目录与题面场景 |
| 保存版本与理由 | 满足：见 `materials_revised_v2.json` |
| Codex 复核 | **待做** |

## 5．依赖与当前用途

- **落地方式**：D6 **测试补丁替换**（整段替换 test_patch）。不改参考分组，不需要派生镜像。D6 首片不接受测试替换，这项能力按计划随后续切片引入。
- **交接给第2类的清单**：
  1. 以 `revised_test_v2.patch`（`e3836c11…`）替换原 test_patch，F2P／P2P 名单不变；
  2. 正式版本复验 §4 的正式诊断评分表：gold 与 4 个合理实现为 1，noop 与 12 个错误候选为 0。候选补丁都在实验目录中；
  3. 正对照为原 gold，不需要按 D4 另找替代正对照；
  4. 等独立复核与 Codex 复核完成后再入库。
- **当前用途**：
  - **原版**：只作问题定位，不进能力比较分母，也不进训练。原因是误拒已确认：3 个合理实现得 0；另有 S1 缺口：退化候选与部分修复得 1。
  - **v2 落地后**：可申请训练候选，已具备 noop 0／gold 1、第 2 步与第 3 步的结果。仍差：独立复核、Codex 复核、actor 开发条件核对。

## 6．独立复核

待做，由不继承本会话上下文的复核子代理进行。建议重点核对：

- §3 的两处边界判断（参数名、相对路径基准）；
- G1 位置参数定为 S2 是否合适；
- v2 中“目录不存在须报错”“失败须抛出且恢复目录”两条断言的依据是否足够；
- 有没有能通过 v2 的其它错误候选。

## 7．未做与剩余事项

- 真实 GNU 工具链端到端（在 build 目录真正运行 autoreconf 并生成 configure）：**未查**。镜像中没有 autoreconf、autoconf、automake，功能测试 `test_basic.py` 未跑。
- 真实 actor 开发条件（UID 54321、激活环境、写权限）：**未查**。
- 位置参数用法在生态中的常用程度：**未查**。
- 跨题关系（同仓其它 Autotools 题）：**未查**。
- 本题没有模型求解证据。
- 记录器与真实 `ConanFile.run` 的差别：`cwd` 不存在时，记录器抛 `FileNotFoundError`，真实 `conan_run` 会包成 `ConanException`。修订测试在这一处只要求“有异常”，所以不影响结论。
- 本次正式评分的 grader profile 摘要（`3ec1bfa8…`）与首批云端试点相同，`scripts_digest` 为 `8aa2dac2…`。两者都与 09-19 历史（`1bb8e0cf…`、`3552fb9b…`）不同，原因未查。noop 与 gold 的逐项结果与历史一致。

## 8．版本与证据

- 代码与运行环境见[环境说明](../../environment.md)。
- 实验文件在 `rh2/experiments/category3_cloud_20260929/conan13403/`：

  | 文件 | 用途 | sha256 |
  | --- | --- | --- |
  | `_edit.py` | 候选构造 | `2fe3ba64…` |
  | `matrix.py` | 私有矩阵 | `934301b6…` |
  | `semantic_spec.json` | 私有对照规格 | — |
  | `run_formal.sh` | 正式评分驱动 | — |
  | `summarize_matrix.py` | 矩阵汇总 | — |
  | `*.patch` | 各候选补丁 | 见下表 |

- 候选补丁 sha256：

  | 候选 | sha256 | 候选 | sha256 |
  | --- | --- | --- | --- |
  | `argsfirst` | `9bd9b28a…` | `norestore` | `5d62f541…` |
  | `conanfile_chdir` | `0b91dd3f…` | `nofinally` | `501e6dc8…` |
  | `runcwd` | `381b1c44…` | `fallback` | `0abb95c9…` |
  | `oschdir` | `db8310bd…` | `swallow_all` | `64451b59…` |
  | `noenter` | `3a6e42a9…` | `swallow_run` | `8e651f11…` |
  | `relonly` | `1533f7b5…` | `mutate_source` | `3c0acf1f…` |
  | `buildlit` | `dd2f4546…` | `cwd_default` | `315844f9…` |
  | `named` | `43f869b7…` | `rel_build` | `32f1dbcc…` |

- 原始证据在 [evidence/](evidence/)：

  | 目录或文件 | 内容 |
  | --- | --- |
  | `formal/` | 原材料正式评分 |
  | `formal_revised_v2/` | 修订版诊断评分，含各候选 `audit_*/materials.json` |
  | `semantic_v1/` | 私有对照：原测试与 v1 草案 |
  | `semantic_v2/` | 私有对照：加入 `buildlit`、`nofinally` 与 v2 草案 |
  | `revised_patch_gen/` | 由容器导出的修订测试补丁 |
  | `evidence_manifest.json` | 全部文件的 SHA256。`prepared/`、`private/`、`artifacts/` 只登记摘要 |
