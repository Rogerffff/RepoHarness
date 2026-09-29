# iterative__dvc-9395 独立复核

2026-09-29，独立复核者（新会话）。

**总判断：部分同意。** 我同意作者的三点：T1 成立，方向上应删除计数断言（R-b）；`--dry` 与未配置 remote 两项回归可以按 S2 登记；证据层级的说明是诚实的。但作者的处置还不能照原样交接，原因有两个：

1. 只删计数的 `revised_test_v1` 过不了 R-b 验收。F2P `test_repro_pulls_mising_data_source` 只断言返回值为真，“吞掉错误”的退化补丁在修订版里得 1；其中一个变体在**原测试**里就得 1，已经命中 §4 第 3 步。
2. G1 只查了 dry 和无 remote 两条路径。gold 在“用户改了数据源之后再 `repro --pull`”这条常用路径上会失败；如果是在终端里交互运行，用户确认提示后，所做的修改会被旧数据覆盖。这一条需要明确裁定，不能直接并入“边缘路径 S2、不阻塞”。

封存的初判 `review_initial.md`（sha256 `29b5a480…164ee`）写于一切实跑之前，之后没有改动。

## 0．方法与证据层级

- 所有结果都是**私有模拟**：root 身份、`--network none`、每次一个一次性容器，镜像为 `xingyaoww/sweb.eval.x86_64.iterative_s_dvc-9395:latest`。镜像 RepoDigest 是 `sha256:479c3af7…c0e`，与冻结值一致；本地 image ID `22951bac…`，Docker 29.3.1。按规定**没有跑正式评分**。
- 判分方式与作者相同：对两个测试文件执行 `pytest -rA -p no:cacheprovider`，然后逐 ID 对照 2 个 F2P、27 个 P2P；F2P 和 P2P 全部 PASSED 才记 1。每次运行都解析出 30 个 ID，29 个参考 ID 一个不缺；多出的一个是 `test_repro_pulls_mising_import`，它不在参考名单里。
- 行为对照用的是真实 CLI（`python -m dvc`，非 TTY）。每个场景新建一个临时 git+dvc 仓库和本地目录 remote，比较调用前后工作区与 `.dvc/cache` 的快照；HTTP 场景在容器 loopback 上起 `http.server` 充当只读 remote。
- 脚本和候选补丁在 `/tmp/rev9395_indep/`（临时目录，没有入库）。关键 diff 见附录。
- 上游材料（PyPI 上的 dvc 各版本 wheel 和 sdist）晚于本题，题面作者看不到。这里只用来**佐证**维护者后来怎么看这些行为，不作为公开依据。

## 1．逐条主张核对

| # | 作者主张（result.md） | 判断 | 依据 |
| --- | --- | --- | --- |
| 1 | T1：`alt_ds_only` 在原测试下只因 `call_count == 3`（实际 2）得 0（:12、:54） | **同意** | 我重跑原测试：`alt_ds_only` 在 `test_restore_pull` 报 `E assert 2 == 3`；在只删了计数行的 v1 下，整题得 1，说明其余断言全部满足。我独立写的 `mine_ondemand`（数据源在 `Stage.run` 里拉取，run-cache 在 `restore` 里按需拉取）也一样：原测试只因 `2 == 3` 失败，v1 下得 1。上游佐证：dvc 2.57.0（2023-05-17，本题之后的首个发布）的 sdist 里，同一场景的 `test_restore_pull` 写的是 `assert mock_checkout.call_count == 2`，3.51.0 仍是 2。可见 `== 3` 是 gold 这一版中间实现留下的痕迹 |
| 2 | `alt_ds_only` “行为与 gold 相同”（:54） | **部分同意** | 在两个 F2P 场景和作者的 6 个行为场景里确实相同。我补的场景中二者有差别，而且 `alt_ds_only` 往往更好：B5、B9 下 gold 失败而 alt 成功；B1b（dry）下 gold 会把 bar 写回工作区，alt 只下载 runs。这句话应限定在“已测场景内相同” |
| 3 | G1：gold 在 `--dry` 下有副作用（:8、:40–41） | **同意** | B1b（只缺 bar、本地 cache 清空）：base 工作区和 cache 都不变，并打印将要执行的命令；gold 把 bar 写回工作区，cache 多出 3 个文件（其中 1 个 runs 条目），还输出 “Data and pipelines are up to date.”，dry 的报告本身失真。B1c（缺 foo）：gold 写回 foo；base 在这个场景下本来就因为 dry 读缺失依赖而报 `[Errno 2]`，这是 base 原有的问题，与本题无关 |
| 4 | G1：未配置 remote 时报 `NoRemoteError`（:9、:42–43） | **同意** | B2（无 remote、已是最新）：base rc 0；gold rc 251，报 `no remote specified`。补充一个对 S2 判定有用的事实：B2c（无 remote、走 run-cache 恢复路径）下 **base 也报 no remote**（rc 255）。也就是说，`--pull` 不配 remote 在 base 里本来就会失败，gold 只是扩大了失败面 |
| 5 | G1 两项都是“不常见组合”，按 §4 第 4 步记 S2、不阻塞（:11、:60） | **部分同意** | dry 和无 remote 两项我同意记 S2。依据：题面没有涉及；base 在无 remote 时已会失败；上游直到 3.67.1 也没有给顶层 run-cache 拉取加 dry 或 NoRemote 保护。**但 G1 清单不完整**，见 §2 的 N2–N4。其中 N2（改过的数据源）落在常用路径上，是 S1 候选 |
| 6 | R-b v1：base 0、gold 1、`alt_ds_only` 1、`gold_guarded` 1（:71） | **同意（数字）** | 逐项复现，与作者 `evidence/revised_v1/*/r1_revised_refs.out` 一致 |
| 7 | 删除计数后，“退化方向（运行命令而非恢复、什么都不拉）仍会被拒绝”（:71） | **不同意（结论不完整）** | 作者只跑了 noop，“运行命令”一条只是从 `cmd_run` 的 mock 推断的，没有构造 §4 第 3 步的退化候选。我按 §4 列出的“吞掉错误、抑制症状”方向，在 gold 的修改位置构造了两个候选：`w_swallow` 在 v1 下**得 1**（原测试里它只是碰巧被 `== 3` 挡住）；`w_swallow3` 在**原测试**里就**得 1**。两者都没有拉回 foo，也没有生成 bar（见 N1、B7） |
| 8 | `gold_guarded` 可作可选正对照（:60） | **部分同意** | 对一条窄的 dry 断言可以用：我的 dry 探针 `test_probe_dry_no_side_effects` 上 guarded 通过、gold 失败；guarded 在原测试、v1 和我的 v2 下都得 1。但它不能作通用正对照，理由有三：它由作者构造，不是独立核实的解；改过的数据源（B3、B3t）、HTTP remote（B4、B4b）、B5、B9、`--no-run-cache`（B6）这些缺陷它全部照旧；B2b（无 remote 加上 foo 被修改）下它报 `ConfirmRemoveError`，而 base 正常。所以 :55 说它“无 remote 正常，与 base 一致”，只在“无修改”的场景里成立 |
| 9 | 证据层级：没有正式评分，全部是私有模拟（:13、:86） | **同意，说法诚实** | result.md 在两处明确写了。影响中等：计数、返回值、文件存在性都是确定性断言，而且我验证过，不装 pygit2 pin 时 base 与 gold 在 29 个参考 ID 上的结果和装 pin 时完全一致，环境差异改变参考结果的可能性很小。不过 §4 第 3 步和 R-b 验收都要求正式评分，交接时要列出需要正式复验的组合（见 §4）。“云端无法重建 dvc_tail_v1”这一说法**未查** |
| 10 | pygit2 固定为 1.14.1 | **没有问题** | wheel 的 sha256 `230493d4…dd93` 与 PyPI 公布值一致。镜像自带 1.15.1，它只让**不计分**的 import 测试在运行期失败：scmrepo 1.4.1 `resolve_rev` 里 `from pygit2 import GIT_OBJ_COMMIT` 报 ImportError。测试收集正常，29 个参考 ID 不受影响（base 装与不装 pin 都是 27 通过、3 失败；gold 不装 pin 是 29 个参考全过，只有 import 失败）。任务说明里“会让相关测试在收集或运行阶段出错”的描述偏宽 |

## 2．我发现的反例与新问题

### N1　F2P 只断言返回值为真，“吞掉错误”的退化补丁能过（§4 第 3 步命中，S1/T2b）

- **在哪里断言的**：`test.patch:27` 只有一句 `assert dvc.reproduce(pull=True)`。
- **退化候选**（只改 gold 的两个修改位置）：
  - `w_swallow`：保留 gold 顶层的 `stage_cache.pull(None)`；`pull=True` 时 `_reproduce_stages` 捕获异常，记一条 warning，然后把 stage 加进结果。
  - `w_swallow3`：在 `w_swallow` 基础上，对有命令的 changed stage 做 gold 那样的预拉取，从而凑出 3 次 checkout。
- **违反了什么**：题面的核心要求是把缺失的数据源拉回来，让本次 repro 能完成。B7 用 CLI 复现 F2P 场景：两个候选都 rc 0，但 foo、bar、dvc.lock 都不存在，只打出 `WARNING: failed to reproduce 'foo.dvc': missing data 'source': foo`。
- **得分**：

  | 候选 | 原测试 | v1 |
  | --- | --- | --- |
  | `w_swallow3` | **1** | **1** |
  | `w_swallow` | 0（`assert 2 == 3`） | **1** |

  也就是说，原题本身已有第 3 步 S1；v1 删掉计数以后，漏洞反而变大了。按 §4 第 3 步还需要 1 次正式评分确认。
- **修法**（R-c，有公开依据的窄断言）：在该 F2P 末尾加两句：

  ```python
  assert (tmp_dir / "foo").read_text() == "foo"
  assert (tmp_dir / "bar").read_text() == "foo"
  ```

  依据是：缺失的数据源已被拉回，下游 `cp foo bar` 确实执行了。gold 仍能通过，不需要 D4。

### N2　用户修改过的数据源加 `--pull`：gold 失败，交互时会丢失修改（S1 候选，需要裁定）

gold 在 `gold.patch:28` 以 `stage.changed()` 作为触发条件，而 changed 也包括“modified”。于是 gold 对旧 hash 做一次 `force=False` 的 checkout，`dvc_data` 在 `_remove` 里会发出 prompt。

| 场景 | base | gold、`alt_ds_only`、`gold_guarded` | `mine_ondemand` |
| --- | --- | --- | --- |
| B3：foo 被改为 `new`，非 TTY | rc 0；foo.dvc 更新为新 hash，bar=`new` | rc 255：`failed to reproduce 'foo.dvc': unable to remove '…/foo' without a confirmation. Use -f to force.` foo.dvc 没更新，bar 仍是旧值 | rc 0，行为同 base |
| B3t：同上，但用 `script` 伪造 TTY 并回答 y | 无提示，结果正确 | 提示 `file/directory '…/foo' is going to be removed. Are you sure you want to proceed? [y/n]`；回答 y 后 **foo 被还原成旧内容**，并输出 `'foo.dvc' didn't change, skipping … Data and pipelines are up to date.` | 无提示，结果正确 |
| 对照：同样修改，不带 `--pull` | 全部候选 rc 0，结果正确 | | |

pytest 形式的探针 `test_probe_modified_source_kept` 结果一致：gold、alt、guarded 都因 `ConfirmRemoveError → ReproductionError` 失败；base、`mine_ondemand`、`mine_retry` 通过。

**为什么我倾向 S1**：

- 题面把范围限定为 “missing and necessary”，被修改的文件不属于缺失。
- “改了数据再 repro”是有公开旧测试的常用行为（`tests/func/test_repro.py` 的 `test_repro_changed_data`、`test_repro_data_source`）。题面的用意又是让 `repro --pull` 成为一条命令搞定的默认用法。
- 失败形态里包含“确认提示之后静默丢失用户修改”，后果严重。

**反证**：上游 2.57.0 到 3.50.x 期间，`Stage.run` 对任何 changed 数据源都执行 `repo.pull` 再 `checkout`，按源码推断会有同样的问题，这一点**未实测**。这种状态持续了约一年，直到 3.51.0（2024-05-23）才改成“除缺失数据外无其它变化时才拉取”（`Pull stages with missing data if otherwise unchanged`）。这说明这条路径可能没那么常被踩到。

**结论**：这一项必须明确裁定，不能沉默地并入 dry、无 remote 那一类 S2。

- 若判 **S1**：走 R-c，补一条“`pull=True` 时保留用户对数据源的修改”的断言。gold 和作者的两个候选都会失败，按 D4 需要一个**经他人独立核实**的替代解作正对照；`mine_ondemand`、`mine_retry` 是我写的，可以作候选，但不能自证。做不到就暂挂。
- 若判 **S2**：写明理由，登记为已知缺口，并列入事后审计。

### N3　HTTP remote：gold 连 base 原有的 `--pull` 能力也破坏了（需登记，我倾向 S2）

- **B4**（默认 remote 为 HTTP，缺 foo）：base 按缺陷报 `missing data 'source'`；gold、alt、guarded 报 `run-cache is not supported for http filesystem`，题面的修复在 HTTP remote 上等于没做。`mine_ondemand` 能正常拉回 foo。
- **B4b**（HTTP remote，bar、lock 和 bar 的缓存被删，本地 runs 保留）：base 能从 run-cache 恢复（rc 0）；gold、alt、guarded 全部 rc 255。这是**对 base 已有功能的回归**。
- 根因是 gold 在顶层无条件调用 `stage_cache.pull(None)`，而 `StageCache.transfer` 在 base 的 `dvc/stage/cache.py:231` 对 HTTP 会抛 `RunCacheNotSupported`。
- 上游在 2.57.0 之后、2.58.2（2023-05-31）之前修掉了这个问题（`try/except RunCacheNotSupported` 并打 warning），还专门加了测试 `test_repro_pulls_continue_without_run_cache`。可见维护者把它当作真缺陷。HTTP 是有文档的 remote 类型，但不是主流，所以我倾向记 S2 并明确登记。

### N4　其它未登记的 gold 回归（S2 级，需登记）

- **B5**：新 stage 的输出文件已存在于工作区，内容不在缓存里。gold 预拉取时执行 `checkout(obj=None)` 试图删除它，报 `ConfirmRemoveError`，rc 255。base、alt、mine 正常。
- **B9**：依赖变了，旧输出既不在本地也不在 remote。gold 报 `ConfirmRemoveError`，rc 255，阻断了本可以重算的情况。base、alt、mine 正常。
- **B6**：带 `--no-run-cache --pull` 时，gold、alt、guarded 仍然下载 runs；base 和 mine 不下载。上游在 2.58.x 已改为遵守 `run_cache` 参数。

### N5　`assert_called_once_with` 也会误拒合理实现（T1，次要）

`mine_retry` 的做法是：`restore` 找不到记录时拉取 run-cache，然后**再调用一次** `restore`。它在四个行为探针上全部通过，也能正确恢复 bar，但原测试和 v1 都判 0，原因是 `Expected 'restore' to be called once. Called 2 times.`

这条断言沿用自公开旧测试。但在“本地 run-cache 缺失”这个新场景下，“恰好一次”属于实现细节。

### N6　P3 风险：需要拉取远端 run-cache 的要求比较隐含

修改后的 `test_restore_pull` 要求在本地 runs 缺失时从 remote 拉回来。题面的依据只有 “all missing files” 加上 `--pull` 原本服务于 run-cache 这两点，只修数据源的实现（例如旧 DeepSeek 候选、我的 `w_nort`）会因此得 0。依据中等，我建议登记，不必修订。

### N7　我的修订草案 v2 的验证结果

v2 在作者 v1 的基础上做了三处改动：

1. `assert_called_once_with` 放宽为 `assert_called_with`；
2. `bar` 从“存在”改为内容等于 `"foo"`；
3. F2P 数据源测试补上 N1 的两句内容断言。

| noop | gold | alt_ds_only | gold_guarded | mine_ondemand | mine_retry | w_nort | w_swallow | w_swallow3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 0 |

gold 仍是正对照。这份草案没有覆盖 N2，是否补 N2 的断言取决于裁定。

## 3．阻断项

1. **R-b v1 不能单独验收**。
   - **问题**：删掉计数以后 `w_swallow` 得 1，违反“已知相关错误候选仍为 0”；原测试本身又已命中 §4 第 3 步（`w_swallow3` 得 1）。
   - **要求**：同一轮修订里补 N1 的 R-c，即 F2P 数据源测试断言 foo、bar 的内容。
   - **验收**：对 noop、gold、`alt_ds_only`、`w_swallow`、`w_swallow3` 在原测试、v1、新版本下各做正式评分。私有预期见 N7。
2. **G1 的“S2、不阻塞”结论要先补全再下**。
   - **问题**：N2（改过的数据源）是常用路径上的回归，必须由主审明确裁定 S1 还是 S2，并写出理由；N3、N4 至少要登记。
   - **要求**：判 S1 时，按 D4 取得他人独立核实的替代正对照，否则暂挂。在裁定之前，本题的训练候选资格保持 conditional。

## 4．非阻断建议

- 同一轮 R-b 里，顺带把 `mock_restore.assert_called_once_with` 放宽为 `assert_called_with`（N5），并把 `bar` 的存在性断言改为内容断言。两处都便宜，也都已验证。
- 收窄 result.md 的措辞：“`alt_ds_only` 行为与 gold 相同”“`gold_guarded` 无 remote 与 base 一致”只在已测场景内成立。另外，上游 2.57.0 同场景断言为 `== 2`，可以作为 T1 的佐证补进去（注明它不是公开依据）。
- 证据归档：`evidence/refs_v1/summary.json` 只剩 `gold_guarded` 一项，看起来是被后一次运行覆盖了。各候选自己的文件是齐的。
- 交给第 2 类做正式评分时，建议覆盖：原测试、v1、最终版分别跑 noop、gold、`alt_ds_only`、`w_swallow`、`w_swallow3`。如果 N2 判 S1，再加上替代正对照。
- 把 pygit2 的环境坑改写得更准确：只影响不计分的 import 测试，参考 ID 不受影响。

## 5．未查

- 正式评分：按规定没有跑。dvc_tail_v1 配方能否在云端重建，未查。
- 真实 actor 的开发条件和模型求解。
- S3、SSH 等其它 remote 类型；`exp run --pull`；目录型数据源与部分缺失的情形。
- 上游 2.57 到 3.50 在“改过的数据源”上的行为：只看了源码，没有实跑。
- 3.51.0 那次修改的动机（issue、PR 原文）。

## 附录：候选与命令（文件在 `/tmp/rev9395_indep/`）

| 文件 | sha256 前 12 位 | 内容 |
| --- | --- | --- |
| `mine_ondemand.patch` | `504afd2b6a3d` | `Stage.run` 的数据源分支里，`pull` 且非 dry 时，只对**不存在的**输出执行 `cloud.pull` 加 `out.checkout`；`StageCache.restore` 找不到记录时，在 `pull` 且非 dry 的条件下执行 `self.pull(None)`（捕获 `NoRemoteError`、`RunCacheNotSupported`），然后再 `_load` 一次 |
| `mine_retry.patch` | `ddf35b356ca0` | 数据源部分同上；run-cache 部分改在 `run_stage` 里：`RunCacheNotFoundError` 时拉取 runs，再调用一次 `restore` |
| `w_nort.patch` | `35a93e6592c1` | 只有 `mine_ondemand` 的数据源部分（不完整候选） |
| `w_swallow.patch` | `b475dd2bf5a0` | gold 顶层 `stage_cache.pull(None)`；`_reproduce_stages` 在 `pull` 时 `except Exception` 后记 warning，执行 `result.append(stage)` 再 `continue` |
| `w_swallow3.patch` | `dcc198d267a8` | 在 `w_swallow` 基础上加 `if kwargs.get("pull") and stage.cmd and stage.changed(): stage.repo.pull(stage.addressing, allow_missing=True)` |
| `revised_test_v2_probe.patch` | `e6ba88039083` | 即 N7 所述 v2 |
| `probe_extra.patch` | `0383574ac8cd` | 四个复核探针：改过的数据源被保留、run-cache 不支持时继续、dry 无副作用、无 remote 且已是最新。只用于复核，不建议照搬进评分 |
| `behav.py` | — | 行为场景 B1–B9，经 CLI 调用 |

用到的命令：

```bash
docker run --rm --network none -v /tmp/rev9395_indep:/in:ro -v …/wheels:/wheels:ro \
  -v …/out:/out --entrypoint bash <image> /in/run_tests.sh <name> <patch|noop> yes /in/<test.patch|revised_test_v1.patch|revised_test_v2_probe.patch>
# 容器内：pip 装 pygit2 1.14.1 → git apply 候选 → git apply 测试补丁
#        → pytest -rA -p no:cacheprovider tests/func/test_repro_multistage.py tests/func/test_run_cache.py
python3 grade.py out/<name>.log   # 逐 ID 对照 2 个 F2P、27 个 P2P
```

每次容器运行的墙钟时间在 10 到 60 秒之间。
