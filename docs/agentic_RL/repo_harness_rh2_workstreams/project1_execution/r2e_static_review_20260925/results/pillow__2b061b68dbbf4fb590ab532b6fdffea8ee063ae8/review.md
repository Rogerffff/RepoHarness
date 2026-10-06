# pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8：独立复核（第二步）

- 角色：独立复核者，只做静态审查。日期：2026-09-25。
- 本文写于封存稿 `reviewer_initial.md` 之后，封存稿未改动。
- 没有运行代码或容器，没有修改原件。
- 第二步新读的材料列在 §8。
- 路径简写：
  - `H/` = `PRIVATE_DIR/hidden_tests/`
  - `W/` = `PUBLIC_DIR/worktree/`
  - "base Lxxxx" 指 `W/src/PIL/Image.py` 的行号

## 结论

| 主审主张 | 复核结论 | 要点 |
| --- | --- | --- |
| 处置为 `needs_review`，理由是题意/测试争议 | 同意 | 与初判一致 |
| 修订公开题面（历史提案 B） | 同意，另加两条措辞护栏（§2.4） | — |
| 隐藏测试与期望映射不改 | 有条件同意 | 题面修订消除不了 N2（新进程首次调用默认 `open` 的路径没有覆盖）。若测试不改，应把 N2 登记为已知漏测，并单独决定是否补检查。测试支撑修订仍作为选项 |
| 两个期望 FAILED 键的测试体不执行，因此"给 `show()` 加警告"的解静态得 1 | **同意**：已沿调用链逐步核对（§1.1） | 两处措辞需要精确化：测试执行到 `pytest.warns(None)` 那一行为止；`save` 的"警告保护"在上游原本就不存在 |
| N2：`list(ID)` 快照得 1，但新进程首次 `open` 失败 | 同意，严重度上调到**中** | 触发这个问题的写法很自然；评分和解题者本地的 pytest 都测不到（§2.1） |
| A1（`formats=123`）只会拒绝显式抛 `ValueError` 的实现 | **修改** | 另外两种实现也会被拒：在原有 `try` 内做成员检查（TypeError 被吞掉）；把非 list 包成列表（抛 KeyError）（§2.2） |
| 跨题可见：同池 5 题的 base 已含上游终版实现 | 核实，同意 | — |
| "先正常打开、再按 `im.format` 过滤"的实现应得 1 | 修改为"可争议" | 这种实现仍用全部插件解析输入，与上游后续 docstring 的 "restrict the set of formats checked" 不符 |

**最小后续实验**：在当前派生镜像上跑一个 CPU 小批，用 RH2 回放评分（§6）。若只能跑一个，先跑 (ii)（快照 / 列表推导变体）。与主审的优先级分歧保留在 §7。

## 1. 逐项核对主审的决定性主张

### 1.1 两个 FAILED 键，以及"给 `show()` 加警告能得 1"（协调者指定重点）

**调用链核对：**

1. **`test_no_resource_warning_on_save`**（`H/test_1.py:613-621`）
   - `Image.open(test_file)` 会执行。
   - `:621` 的 `pytest.warns(None, im.save, temp_file)` 走函数式 `warns`：先构造 `WarningsChecker(None)`，其 `__init__` 在 `recwarn.py:279` 抛 TypeError，所以 `im.save` 不会被调用。
   - 日志证据：noop 日志 L56、L84-87；gold 日志相同。
2. **`test_show_deprecation`**（`:783-793`）
   - `monkeypatch.setattr(Image, "_show", …)` 和 `Image.new` 会执行。
   - `:788` 的 `with pytest.warns(None)` 同样在构造时失败。
   - 之后的语句都不执行：`im.show()`（`:789`）、`assert not raised`（`:790`）、`show(command="mock")` 及其 DeprecationWarning 断言（`:792-793`）。
   - 日志证据：noop 日志 L98、L126-129。
3. **没有其它键会调用 `Image.show`。**
   - 全文件只有上面这两处调用 `im.show()`。
   - `test_showxv_deprecation`（`:597-611`）直接调用 `Image._showxv(im)`（`:608`），不经过 `Image.show`。
   - helper 只有在 `SHOW_ERRORS` 环境变量存在时才调用 `show()`（`H/helper.py:21-29`），评分时没有这个变量。
4. **多出的警告不会让别的键出错。**
   - 评分命令带 `-W ignore` 和 `PYTHONWARNINGS='ignore::UserWarning,…'`。
   - `W/setup.cfg:11-13` 的 pytest 段没有 `filterwarnings`。
   - 因此 `pytest.warns` 之外多出来的警告都被忽略。
5. **结论**：`gold` 加上"无参 `show()` 发 DeprecationWarning"，或 `gold` 加上"在 `save` 里压掉警告"，逐键状态都与 gold 相同，得 1。
   - 同意主审。证据级别为源码推断加日志推断，可以用 CPU 实验 (iii) 确认。
   - 在现题面下，这是题面 Expected 第 3 条直接诱导出的、与 `docs/deprecations.rst` 和公开测试相反的改动，而评分不会发现。

**两处措辞修正（不改变结论）：**

- **"测试体从不执行"不精确。** `pytest.warns(None)` 之前的语句会执行：`Image.open`、`monkeypatch.setattr`、`Image.new`。不执行的是被检查的操作和断言。主审在 analysis §3.3 的写法是准确的，协调者的转述扩大了范围。
- **"`save` 的警告行为不受保护"需要限定。** 在旧版 pytest 中，`pytest.warns(None, …)` 只记录警告、不做断言，所以上游这条测试本来只保护"`save` 不抛异常"。真正丢失的保护是 `show()` 的两条：无参调用不告警；带 `command` 时发 DeprecationWarning。

### 1.2 其它主张

| # | 主审主张（出处） | 核对 | 结论 |
| --- | --- | --- | --- |
| 1 | 目标键唯一；noop 为 0、gold 为 1；重复运行稳定；与 M3 一致（analysis §0、附录 A） | 初判已独立核对 4 份 current 日志、sha 链，以及 M3 的 a1 / a2 | 同意 |
| 2 | 合法修复翻不动两个 FAILED 键；"唯一途径是改测试设施"（delta #6） | 前半句成立。后半句偏窄，还有两条途径：(a) 被测包的导入期代码，例如在 `src/PIL/__init__.py` 里给 `_pytest.recwarn` 打补丁，`r2e_grading_scripts.py:22-23` 把这类情况归入 DR4、不处理；(b) `.venv` 里的 pytest 对 agent 可写（历史 R07；探针 `WRITE_SITE=ok`，agent_probe.log L34），这类改动会不会进入冻结补丁未知 | 前半同意，后半修改。这些都是越界改法，不改变处置 |
| 3 | 回退语义实现必判 0（A2） | `:96-98` 用 `pytest.raises(UnidentifiedImageError)` 包住的正是题面示例的调用 | 同意。这是读代码就能确定的结果，CPU 只是程序性确认 |
| 4 | N2：快照实现得 1 | 见 §2.1 | 同意，并上调严重度 |
| 5 | gold 对未注册、小写或未知的格式名抛 KeyError | base L2896 的 `OPEN[i]` 在 `try` 内；KeyError 不在 L2905 的捕获元组里，经 L2910-2913 原样抛出；`register_open` 会转大写（L3048），gold 不转 | 同意 |
| 6 | A1 区分力弱，只拒显式 `ValueError`（delta #4） | 见 §2.2 | 修改 |
| 7 | 跨题可见：`2d01f7d0`、`3a61c9e9`、`4bc64835`、`a682ceaf`、`f9d3ee0f` 的 base 已含上游终版实现（delta N4） | 逐题 grep 公开包：5 题都有 `def open(fp, mode="r", formats=None)`、`i = i.upper()`、`if i not in OPEN:`，且 `Tests/test_image.py` 有 `test_open_formats`。`2d01f7d0` 的这个测试（L93-113）是本题隐藏测试的超集，多了 `["jpeg"]` 等大小写变体；它的 docstring（L2938-2949）写明了 list/tuple、`None` 表示全部格式、其它类型抛 TypeError | 同意 |
| 8 | 解题侧条件已在镜像层面实测（delta #9、#10） | 历史探针原件：uid 54321（L2）、`WHICH_pip=MISSING`（L11）、`PYTEST_VERSION=pytest 8.3.4`（L22）、`IMPORT_FROM_TMP=/testbed/src/PIL/__init__.py`（L26）、`R2E_TESTS_ROOT=absent`（L66）、复现段（L121-128）、`NET_CONNECT_RC=1`（L132）；定向公开测试为 `2 failed, 52 passed`（targeted L79-81） | 同意。主审标"镜像层面实测、正式 actor 链待验"，标法正确 |
| 9 | 历史 R06 附注"`non_passed_reasons` 为空"已过时 | 当前 `facts.json` 的 4 个 `rh2_runs` 都有原因行 | 同意 |
| 10 | 历史 R17 的无泄漏结论只覆盖派生镜像 | M3 在来源镜像上执行 `git branch --contains 2b061b68`，结果包含 `main`（M3 `facts/2b061b68dbbf/facts/git_contains.txt`），与环境卡 §2 一致 | 同意 |
| 11 | 上游提交只改了 `src/PIL/Image.py` 与 `Tests/test_image.py` | M3 账本第 10 行的 `gold_meta`（included / excluded），以及 `facts/.../git_fix_files.txt` | 同意 |
| 12 | 解析器对两侧都去色；`Effects.c` 没有 `srand` | `rh2/src/repoharness2/envpack/r2e_parsers.py:117-127`；`W/src/libImaging/Effects.c:104-105、136-137` | 同意 |
| 13 | "先打开、再按 `im.format` 过滤"的实现应得 1（analysis §5） | 隐藏测试区分不了这种实现。但它仍然用所有插件解析输入，不符合上游后续 docstring 所说的 "restrict the set of formats checked"（`2d01f7d0` base L2939）；遇到 MPO 文件时行为也与 gold 相反 | 修改为"可争议"。属于低风险的宽松放行，不是误拒 |

## 2. 主审未覆盖或需要修改的范围

### 2.1 N2 应上调为中（也纠正我初判的偏窄描述）

- **gold 为什么没问题。** gold 在 `preinit()`（base L2889）之前执行 `formats = ID`（gold.patch L18-19，插在 base L2870 之前），靠 `init()` 就地往同一个列表里追加插件（L3049）。
- **两种出错写法。** 候选如果在同一位置做拷贝，就会出问题。拷贝可以是 `list(ID)`、`tuple(ID)`，也可以是更自然的大小写归一化 `formats = [f.upper() for f in formats]`（在 `None` 分支之后统一执行）。
  - **快照取在 `preinit()` 之前**：新进程里 `ID` 为空，快照是空列表；两轮 `_open_core` 都不尝试任何格式，**第一次 `Image.open` 任何文件都会抛 `UnidentifiedImageError`**。
  - **快照取在 `preinit()` 之后**：只有非预载格式（TIFF 等）在首次打开时失败。
- **评分测不到。** 第一次 `formats=None` 的打开（`:104-107`）发生在 A2 已经触发 `init()` 之后。
- **解题者本地也测不到。** 运行 `python -m pytest Tests/test_image.py` 会加载 `Tests/conftest.py`，其 `pytest_report_header` 调用 `features.pilinfo()`，进而调用 `Image.init()`（`features.py:230`），在会话一开始就载入全部插件。只有在新进程里执行 `python -c` 才能暴露问题。
- **影响。** 这类实现会让任何脚本的第一次打开图片失败，却得满分。题面修订消除不了这个问题。
- **建议。** 若"隐藏测试与期望不改"，应把它登记为已知漏测，并由用户决定是否补一条"新进程里默认 `open`"的子进程检查。这条检查的依据是旧行为，不扩大需求；但它会改变评分标准，需要版本化，并用 noop 和 gold 复核（两者都应通过）。
- **修正初判。** 我的初判 P5 只写到"非预载格式首次打开失败"并定为低风险，描述偏窄。以主审给出的两种情形为准，并上调严重度。

### 2.2 A1（`formats=123` 必须抛 TypeError）会拒绝的不只是显式 ValueError

- **在原有 `try` 内做成员检查。** 在 `_open_core` 原有的 `try`（base L2895-2909）里写 `if formats is not None and i not in formats: continue`。`i not in 123` 抛出的 TypeError 会被 L2905 吞掉，最终抛 `UnidentifiedImageError`，于是 `:93-94` 失败。这个实现对 list、tuple、`None` 的行为全部正确。
- **把非 list 包成列表。** 为了支持单个字符串，把非 list 的参数包成 `[formats]`。结果 `OPEN[123]` 抛 KeyError（不在 L2905 的捕获元组里），`:93-94` 同样失败。
- **判断。** 风险仍然低，多数实现会让 TypeError 自然向外传出。但主审"只拒显式 ValueError"的说法不成立。

### 2.3 期望映射依赖镜像里的 pytest 版本在 8 以上（主审未提）

- `install.sh` 只写了 `uv pip install setuptools pytest …`，没有固定版本（image_readout L25）。两个 FAILED 键完全取决于 pytest 8 拒绝 `pytest.warns(None)`。
- 现在镜像按 digest 固定，所以结果稳定。但若来源镜像或派生镜像被重建，装到的 pytest 行为不同，这两个键就会变成 PASSED，**包括 gold 在内的所有解都会判 0**。
- 这是支持"测试支撑修订"的另一条理由：修订后就不再依赖 pytest 版本。

### 2.4 修订措辞护栏（对应"修订是否扩大原需求"）

- **不扩大需求。** 主审建议的修订内容是：限制格式；不匹配时沿用 `UnidentifiedImageError`；`None` 表示全部格式；list/tuple 的约定可以写入。这些都在上游 API 约定之内。`UnidentifiedImageError` 本身也是 base docstring 已公开的"无法识别"异常（base L2856-2857）。
- **护栏 1。** 如果以上游后续的 docstring 为蓝本，不要带入本题 gold 不满足的后续行为：大小写不敏感（即后续公开测试里的 `["jpeg"]` 等变体）、按需调用 `init()`。否则题面会比 gold 宽，gold 自己就不合规，而且测试查不出来。
- **护栏 2。** 示例只用预载格式（PNG、JPEG），避免落在 gold 的 KeyError 缺口上，比如 `formats=['TIFF']`。
- **代价。** 修订后，题面几乎完整说明了目标测试的四条断言，本题会变成直接的特性实现题。难度和训练价值属于用途问题，静态审查不代为回答。

## 3. 是否先看了答案，再把隐藏要求说成"显然"

- **基本没有。** 主审的映射表把 A1、接受 tuple、A4 标成"无公开依据 / 惯例"，把回退语义标成"有争议"。
- **小问题。**
  - `card.md` §1 和 analysis §0.1 把"其它类型抛 TypeError""接受 tuple"直接写成任务定义，没有标注"这是评分要求，公开材料未写"。建议卡片区分"公开可推知"和"隐藏测试要求"。
  - delta #14 用上游后续 docstring 支持把 list/tuple 写进题面。作为修订依据可以，但那是另一道题 base 里的未来知识，不能反过来说明本题的解题者本来就能知道。
- **公开读者的疑义。**
  - 严格语义与回退语义的冲突，无法用公开材料消除，是真问题。
  - pytest 版本、导入路径、`r2e_tests` 是否存在，这些在环境里跑一条命令就能搞清楚，不是题目缺陷。
  - 主审 §1 的处理是正确的。

## 4. 处置与"可探针"的表述

- **同意现有处置。** `probe_candidate=false`、`state=needs_review`、reason 为"题意/测试争议"，与记录模板一致。
- **剩余条件应列成清单。** "修订题面后可作为静态候选"这一句，应当展开为以下剩余条件：
  1. 修订版获批并版本化（新的 `problem_statement_sha256` 与 pins），并跑过触发反例；
  2. N2 的去留决定；
  3. 正式 actor 链改用派生镜像，提示去掉 conda/pip 的说法（环境卡 §2、E09）；
  4. 跨题可见的数据划分决定。

  其中第 3 条是平台前置条件，不属于本题材料；第 1、2、4 条属于本题。
- **标注不一致。** `card.md` §3 把"材料与初态"标为"通过"，而 `screening_record.json` 的 check 2 是 `issue`。建议统一；我倾向于 `issue`，理由是材料之间彼此对应，但题面描述的初始问题不是真实缺口。

## 5. 与我初判的差异

| 项 | 初判 | 现在 | 理由 |
| --- | --- | --- | --- |
| N2 | P5，低风险，只提到非预载格式 | 中，分两种情形 | 主审指出：快照若在 `preinit()` 之前取值，任何首次打开都会失败；再加上本地 pytest 也会掩盖问题 |
| `show()` 警告被放行 | P6 只写了"死键丢失 `show()` 的保护" | 采用主审的表述：题面第 3 条诱导出的有害改动得 1 | 把"题面诱导"和"评分放行"连起来看，更贴近实际用途风险 |
| 优先实验 | C1（conftest 兼容补丁） | (ii) | 题面修订后，C1 的诱因基本消失；(ii) 的结果决定"测试不改"是否足够 |
| C1 陷阱机制、C2、题面主症状错配 | 见初判 | 不变 | 主审结论一致；C2 例外，见 §2.2 |

## 6. 最小后续实验（均未执行）

在当前派生镜像上用 RH2 回放评分，一个 CPU 小批：

1. **(ii)** 把 gold 的 `formats = ID` 改成 `formats = [f.upper() for f in formats]`（统一执行）或 `list(ID)`。
   - 预测评分得 1。
   - 另在新进程里执行 `python -c "from PIL import Image; Image.open('Tests/images/hopper.png')"`，预测抛 `UnidentifiedImageError`。
2. **(iii)** gold 加上无参 `show()` 发 DeprecationWarning。预测得 1。
3. **(i)** 回退语义实现。预测得 0。它是题面修订的程序性触发反例。
4. **可选。**
   - C1：在根 `conftest.py` 里让 `pytest.warns(None)` 只记录不断言，预测得 0。
   - C2：成员检查写在 `try` 内，预测得 0。

这些实验不需要真实模型。"在误导性题面下，解题者会不会去改 conftest 或 `show()`"属于清单第 33–36 项，静态审查回答不了。

## 7. 保留的分歧

1. **实验优先级。** 主审优先跑 (i)，我优先跑 (ii)。(i) 的结果读代码即可确定；(ii) 会影响"测试不改"是否足够。
2. **N2 的严重度，以及是否补子进程检查。** 主审把 N2 列为次要问题，补检查属于新断言、需另行审定。我认为应在 CPU 确认之后，把它作为必须决定的事项。
3. **测试支撑修订。** 双方都认为是可选项、由用户决定。我补充了 pytest 版本依赖这条理由（§2.3），倾向于在本题进入训练之前做。

## 8. 第二步实际读取范围

- **OUTPUT_DIR**：
  - `public_read.md`
  - `analysis_before_history.md`：文件头注明由协调者从被拒写入中保存；它先于读历史写成，这一点我无法独立核实
  - `old_findings_delta.md`、`card.md`、`screening_record.json`
- **历史材料**（`refs.json` 所列 9 项）：
  - `screening_record.json`、`findings.md`
  - `facts.json`（只看了 `rh2_runs[].non_passed_reasons`）
  - `known_issues.json`（只看了三个列名族）
  - `decisions.md`（E06、E09、E10、E14、T0-3 这几行）
  - `results_20260924.md`（pillow 各行）
  - 材料修订提案、复现脚本
  - P4 README（§0、§1、§2.1–2.4、§3、§4、§7.7）
- **历史指向的原件**：
  - `runs/r2e_env_repair_20260924/p4/dev_probe/pillow__2b061b68…/agent_probe.log`
  - `…/targeted_public_tests/pillow__2b061b68…/agent_probe.log`
  - `…/image_readout/pillow__2b061b68….txt`
  - M3 `facts/2b061b68dbbf/facts/{git_fix_files,pytest_version,git_contains}.txt`
  - M3 账本 `r2e_gold_m3.jsonl` 第 10 行（`gold_meta` 字段）
- **为核对主审 N4 新增的暴露**：其它 6 道 pillow 题公开包中的以下内容：
  - `src/PIL/Image.py`：grep 了 `def open`、`i.upper()`、`if i not in OPEN`；`2d01f7d0` 读了 `open` 里 `formats` 相关的片段和 docstring；
  - `Tests/test_image.py`：grep 了 `test_open_formats`、`pytest.warns(None`；`2d01f7d0` 读了该测试全文。
- **RH2 源码与公开源码**：`rh2/src/repoharness2/envpack/r2e_parsers.py:117-127`；公开 `src/libImaging/Effects.c` 中 `rand` 的 grep。
- **没有读**：批次 README、`assignments.json`、其它题的私有材料、40 项清单。因此没有核对 `checks` 编号是否与清单定义一致。
- 没有运行任何代码或容器。
