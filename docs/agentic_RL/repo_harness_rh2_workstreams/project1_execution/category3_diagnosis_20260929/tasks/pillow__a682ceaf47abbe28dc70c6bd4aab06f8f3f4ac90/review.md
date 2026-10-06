# pillow__a682ceaf47abbe28dc70c6bd4aab06f8f3f4ac90 独立复核

2026-09-30 / 独立复核者（Claude，新会话，不继承作者上下文），按统一标准 v1 §7.3 对作者结论找反证。

**复核对象**：
- 本目录的 [result.md](result.md)、[initial_judgment.md](initial_judgment.md)、[public_read.md](public_read.md)、[commands.json](commands.json)、`evidence/`；
- 实验目录 `rh2/experiments/category3_cloud_20260929/pillow_a682/`：19 个补丁（含 gold）、`make_candidates.py`、`probe_matrix*.py`、`run_matrix.py`、`hidden_test_1_revised_v1.py`、`hidden_test_1_revised_v1_nowarn.py`、`revision_draft_v1.json`。

**顺序**：
1. 先读原件、实跑 21 个 base 对 gold 的探针场景，写[初判](review_initial.md)并封存。
   - sha256 `d8f6b25ce7c99676a4ca91b32990ff4b00a72fb79fd7a4845d75fc39718b6167`，写完未改；
   - 负责人 07:54 UTC 的提交 `4668a7f8` 已收入此文件，版本与现存相同，可证之后未改；
   - 派发说明里转述的作者结论，我在写初判前已经看到，初判开头已如实登记。
2. 再读作者材料。
3. 最后自造候选，跑私有模拟评分。

复核者的脚本、候选、修订草案与证据都在 `rh2/experiments/category3_cloud_20260929/pillow_a682/review/`。

## 总判断：部分同意，阻断项 3 项

**同意的部分**：
- **原版判 S1 成立。**
  - 唯一目标键 `test_removed_transparency` 的图、像素和元组与题面示例逐字相同，属第 2 步 T2c；
  - 第 3 步的 `w_literal` 在原测试得 1，属 T2b；
  - 作者另外 6 个错误候选在原测试也得 1，而且违例都落在主路径上。

  我把作者 20 个候选在原测试、v1、v1 无 warns 三版上逐格重跑，60/60 格与作者账本相同，连失败键都一致。
- **R-c v1 的四段检查都有公开依据，不过严。** 在 v1 上为 1 的有：
  - gold；
  - 作者的 4 个合理实现；
  - 我另造的 3 个写法（`r_retry`、`r_none_marker`、`r_kwtuple`），它们与 gold 和作者的 4 个都不同；
  - 上游 10.1.0、10.4.0、11.3.0 的 wheel。
- **`pytest.warns(UserWarning)` 应保留**（§4）。除作者给的依据外，还有一条更硬的理由：去掉它会放过错误候选 `w_filter_leak`。这个候选在进程里留下全局过滤器，之后 `Image.convert` 这条公开警告就不再出现（探针 P13）。
- 四处“不作要求”中三处同意：关键字传元组、旧接口 `getdata`、RGB 图放整数透明度。X1、E3 的登记成立，两者都已实核。

**不同意“按 v1 交第2类”。** v1 仍放过我构造的 3 个错误候选。它们在原测试、v1、v1 无 warns 三版上都得 1，但各自违反一条公开要求：

| 阻断 | 候选 | 做法 | 违反什么、怎样看到 |
| --- | --- | --- | --- |
| **B1** | `w_mutate_kept` | 透明色能用时，把调用者 `im.info` 里的元组“同步”成调色板索引 | v1 的 (c) 只在丢弃透明度的两种情形后检查。这张图接着存 PNG 会抛 `TypeError: cannot unpack non-iterable int object`（P08） |
| **B2** | `w_nosaveall` | 认为多帧写入本来就用归一化后的帧，只修 `save_all=False` 的入口 | `im.save(out, save_all=True)` 只有一帧，或两帧完全相同时，仍抛 `TypeError`（P05、P06）。作者登记 S02“没有已知候选利用”，现在有了 |
| **B3** | `w_order_cache` | 用模块级缓存记住“分配失败过”的颜色，以后直接丢弃 | 题面示例之后，同一颜色在调色板有空位的 1×1 图上也被丢弃（P09，base 与 gold 保留）；之后的保存也不再警告 |

**修法**：在作者 v1 上补三小段，共 15 行，键集和期望映射（93 键）都不变。草案见 `review/materials/hidden_test_1_review_v2.py`（`3573f459…`）与 `revision_draft_review_v2.json`，编辑块已用 RH2 的 `_apply_edits` 重放核对。私有模拟结果：
- 为 1：gold 与 7 个合理实现；
- 为 0：noop、作者的 13 个错误候选、我的 5 个错误候选、`q_prestrip`；
- 我抽测的 12 个候选在评分 UID 54322 下与 root 逐格一致；
- 上游 10.1.0、10.4.0、11.3.0 也通过 v2 的该函数。

**停止条件**（详见 §7）：
- 采用 v2 或逐字等价的改动后，本题测试层不再需要聚焦复核；
- 第2类正式评分的逐候选结果与 §3.2 表的 h4 列一致，即可完成；
- 此后再想出的反例只登记，除非它落在 §7 列出的主路径上，并能指出具体违例；
- `pytest.warns` 保留，不需要用户决定。

**与初判的差异**：
- (c) 的依据，初判认为较弱。读到同仓先例 r2e-mr-063，并看到 P08 的实际后果（改过 `info` 的图接着存 PNG 会崩溃）后，接受为有依据的检查。
- 其余初判结论经实测维持：原版 S1、`pytest.warns` 保留、`save_all` 单帧应纳入、多捕获 `TypeError` 属合理实现。

## 1．复核范围与证据层级

- **全部是私有模拟，不是 R2E 正式评分链。**
  - 每个候选开一个全新容器，root、`--network none`，驱动为共用工具 `semantic_control.py`；
  - 镜像 `c3keep/pillow_a682:src`，即 `namanjain12/pillow_final@sha256:c9ee334c…5733`，Image ID `5831b933…`，Pillow 10.1.0.dev0，Python 3.9.21，与冻结摘要一致；
  - 流程：把 `/r2e_tests` 复制到 `/testbed/r2e_tests`，换入对应版本的 `test_1.py`，运行评分包的 `run_tests.sh`（`8285765f…`）；
  - 计分：`grade_r2e.py` 用上游口径 `prime_calculate_reward`，我另算 RH2 生产口径（键集相等且逐键相等）。164 格两种口径全部一致，每格都解析到 93 键，没有多余键。
- **材料版本**：

  | id | 文件 | sha256 |
  | --- | --- | --- |
  | h0 | 镜像原件 `test_1.py` | `ff7a439c…` |
  | h1 | 作者 v1 | `7f247bf4…` |
  | h2 | 作者 v1 无 warns | `7ca12079…` |
  | h4 | 复核 v2 | `3573f459…` |
  | h5 | 复核 v2 无 warns | `6fd35e4b…` |

  期望映射都是 `a465b6c9…`，93 键。
- **候选共 28 个**：
  - 作者 19 个补丁（含 gold）加 base，共 20 个，从作者目录原样 `git apply`，sha256 与作者清单一致；
  - 复核者 8 个，由 `review/make_review_candidates.py` 按精确文本替换生成（§3.1）。
- **规模**：
  - root 下 28 个候选 × 5 版材料，共 140 格；
  - 每个候选另跑公开测试 `Tests/test_file_gif.py` 与 `Tests/test_image_convert.py`，以及复核者探针 `probe_review.py`（P01–P16，§3.3）；
  - UID 54322 下 12 个候选 × h1、h4，共 24 格。做法与作者相同：一次性容器里放开 `/root`，再用 `setpriv` 降权。这是私有近似，没有套正式 profile。
- **初判前的探针**：`review/evidence/pre_initial/probe0.py` 及其输出，base 对 gold，21 个场景。sha256 与初判里登记的相同，初判写的是“在 scratchpad”，事后才复制进来。
- **上游对照（只作佐证，不当公开依据）**：
  - 从 PyPI 取 `Pillow-10.1.0.tar.gz`（`e6bf8de6…`），其中 `_write_local_header` 与 gold 逐字相同，`test_removed_transparency` 与隐藏测试逐字相同，CHANGES 有 “#7284”；
  - 10.1.0、10.4.0、11.3.0 的 cp39 wheel，sha256 与作者 `wheels_sha256.txt` 和 PyPI 登记值一致；
  - 11.3.0 的测试文件取自 GitHub raw（`922e26da…`），它把断言收紧为 `match="Couldn't allocate palette entry for transparency"`。
- **结果文件**：
  - 汇总：`review/summary_table.txt`（评分）、`review/probe_table.txt`（探针）；
  - 原始输出：`review/evidence/{r2_A,r2_B,r3_uid,r4_getcolors}/`，由 `archive_evidence.py` 归档，含账本、每格完整日志、探针、公开测试、`candidate.diff`；
  - 其它：`review/evidence/upstream_v2/`、`review/evidence/x1_e3_check/`。
- **未做**：正式评分链与派生镜像、UID 54321 开发条件、Codex 复核（§8）。

## 2．作者主张逐条核对

| # | 作者主张 | 判断 | 依据 |
| --- | --- | --- | --- |
| 1 | 当前生效的是原始材料 v0，修订单 v1–v11 没有本题 | 同意 | `grep a682ceaf s2_r2e/revisions/*.json` 无结果；评分包 `material_revisions: []` |
| 2 | 唯一目标键与题面示例逐字相同，属 S1（T2c） | 同意 | 隐藏 `test_1.py` 等于公开 `Tests/test_file_gif.py` 加这一个函数，已 `diff`；函数用的图、像素、元组都是题面原样 |
| 3 | `w_literal` 原测试得 1，第 3 步命中 T2b | 同意 | h0=1；它在 gold 的修改位置只特判 `(255,255,255)`。探针 P02（hopper）、P15（PNG 读回）、P16（256 级灰）上仍抛 `TypeError` |
| 4 | 另 6 个错误候选原测试得 1，都违反公开要求 | 同意 | 逐格复现 h0=1。违例都在主路径上：<br>• `w_count256`、`w_notin_image` 在 P02、P15 上崩溃<br>• `w_drop_full` 在 P03、P04 丢掉本来能用的透明色，`w_drop_big` 在 P04 丢掉<br>• `w_mutate`、`w_convert_mutate` 改调用者的图，第二次保存不再警告（P10b） |
| 5 | v1 四段检查各有公开依据 | 同意 | (a) 的输入就是公开 `test_image_convert.py::test_trns_RGB`（172–192 行）的输入<br>(b)(b′) 的依据是公开 `test_rgb_transparency` 单帧部分和 base 行为（P03、P04 base 保留）<br>(c) 的依据是 PNG 文档把 RGB 图 `info["transparency"]` 定义为该图的透明色（`image-file-formats.rst:666-673`），GIF 文档写保存选项“默认取 info 值”（241-247），同仓先例 r2e-mr-063 已有“saving does not modify the image that is saved” |
| 6 | v1 不误拒：gold 与 4 个合理实现为 1 | 同意，并扩充 | 我另造的 `r_retry`、`r_none_marker`、`r_kwtuple` 在 v1、v2 都为 1。三者的差别分别在异常驱动、显式标记、同时处理关键字元组 |
| 7 | v1 下 13 个错误候选为 0，“已知相关错误候选仍为 0” | **数字属实，结论不完整** | 13 个都复现为 0，但不含 `w_mutate_kept`、`w_nosaveall`、`w_order_cache`，这三个在 v1 为 1（B1–B3） |
| 8 | root 与 UID 54322 结果相同 | 同意 | 我抽的 12 个候选在 h1u、h4u 上与 root 逐格一致 |
| 9 | gold 与上游 10.1.0 的 `_write_local_header` 逐字相同；10.1.0、10.4.0、11.3.0 通过 v1 | 同意 | sdist 已核。三版 wheel 也通过复核 v2 的 `test_removed_transparency`、`test_rgb_transparency`、`test_transparent_optimize`。10.0.0 未重跑 |
| 10 | 保留 `pytest.warns(UserWarning)` | **同意，补充依据** | 见 §4 |
| 11 | 关键字传元组不作要求 | 同意 | 文档把保存选项 `transparency` 定义为 “Transparency color index”（246-247）。gold 报错（P11）、`alt_typeerror` 静默忽略、`r_kwtuple` 按调色板换成索引（P11b 索引正确），三者在 v1、v2 都为 1，测试确实不偏向任何一种 |
| 12 | 旧接口 `getdata` 不作要求 | 同意 | 手册没有写它，公开 `test_getdata` 不带透明度。gold 以及在 gold 上改的 `alt_prestrip_warn`、`r_kwtuple` 改变了它的行为（P12：`gce=None`）；`r_retry`、`r_none_marker`、`alt_typeerror` 保持 base 行为（`gce=1`）。两类在 v1、v2 都为 1 |
| 13 | RGB 图放整数透明度不作要求 | 同意 | 不是文档里的合法表示，题面只谈元组。作者说“只有 1、I 模式直接转 RGB 会产生这种组合”：读码可见这两条路径不换算整数，L 转 RGB 会换成元组；是否“只有”这两条，未穷举 |
| 14 | `save_all=True` 只有一帧：可选加固，不建议加 | **不同意** | `w_nosaveall` 利用了它（B2）。`save_all` 是文档化选项，这是同一核心要求的另一个实例，修法只需一小段 |
| 15 | 题面不需要 R-f | 同意 | 示例只定义函数、没有调用，属小瑕疵；Expected Behavior 写得明确，不会把人引向“把元组转成数字” |
| 16 | X1：本题 base 是同仓其余 6 道 R2E pillow 题的后代 | 同意，已核 | 在来源镜像里 `git merge-base --is-ancestor`：6 道题的 base 与修复提交都是本题 HEAD（`7a1e2840`，2023-07-09）的祖先（`review/evidence/x1_e3_check/`） |
| 17 | E3：来源镜像含修复提交对象，派生镜像已清理 | 同意，已核 | 来源镜像 `git cat-file -t a682ceaf…` 为 `commit`；09-24 审查 R17 记派生镜像 `fix_present=no`；M3 清理探针清理后取不到该对象。私有对照只由 root 在断网容器里运行，不涉及解题 |
| 18 | 原版不进能力比较与训练 | 同意 | 原版有已证的 S1 未修 |
| 19 | 交接清单第 3 条的预期分数 | 需要更新 | 按 v2 加入复核者的 8 个候选，见 §3.2 表与 §7 |

## 3．反例与新问题

### 3.1 复核者候选

生成脚本为 `review/make_review_candidates.py`，补丁在 `review/cands/`。

| 候选 | 类别 | 做法 | sha256 |
| --- | --- | --- | --- |
| `r_retry` | 合理：异常驱动 | `_write_single_frame` 捕获局部图像头因元组回退抛出的 `TypeError`，用去掉该键的副本重写；关键字元组照旧报错 | `a383d1d0` |
| `r_none_marker` | 合理：显式标记 | 归一化删掉透明度时在 `encoderinfo` 记 `None`，局部图像头把 `None` 当“无”；版本判断同步改为“有非 None 的透明度才用 89a”；保留 `info` 回退 | `f23c67b7` |
| `r_kwtuple` | 合理：更完整 | gold，另把 `save()` 关键字传入的元组按归一化后的调色板精确查找换成索引，查不到就自发 UserWarning 并不用透明度 | `e02d7be4` |
| `w_mutate_kept` | 依赖顺序、副作用 | gold，另在透明色能用时把调用者 `im.info` 的元组改成调色板索引 | `aa7b2023` |
| `w_nosaveall` | 只覆盖路径子集 | 只在 `save_all=False` 时让局部图像头跳过原图元组 | `a9d12e0e` |
| `w_order_cache` | 依赖顺序 | gold，另用模块级集合记住分配失败过的颜色，下次在转换前直接剥掉 | `173d65bd` |
| `w_getcolors256` | 规模阈值 | gold，另在图已用满 256 色时用 `getcolors()`（默认上限 256 色）判断透明色在不在图里；多于 256 色时它返回 `None`，被当作“不在”而丢弃 | `a9acd3c5` |
| `w_filter_leak` | 抑制症状 | gold，另在归一化 RGB 图时装一条不还原的 `warnings.filterwarnings("ignore", message=…)` | `a6378f93` |

其它方向的排查：
- **规模与阈值**：作者的 `w_count256`、`w_drop_big` 已覆盖“恰好 256 色”与“多于 256 色”两种阈值。我另造的 `w_getcolors256` 踩的是 `getcolors()` 默认上限这个常见陷阱，原测试得 1，v1 由 (b′) 拦下。只要不改量化器，“能否分配”等价于“归一化后的调色板里有没有这个颜色”，(a)、(b)、(b′) 正好覆盖三种组合，我没找到新的阈值漏洞。
- **模式与数据形态子集**：元组透明度的文档化来源只有 RGB 图（PNG 文档 670-671），所以只认 RGB 的写法在合法输入上与完整写法等价，没有单独造候选。RGBA、P 图带元组不是标准表示：RGBA 上 base 与 gold 都不报错（P14），P 图上两者都抛 `TypeError`（初判探针 S17），不作要求。
- **吞错**：作者的 `w_swallow_save` 写出残缺文件，已被拒。多捕获一个 `TypeError`（`alt_typeerror`）属合理实现。

### 3.2 私有评分（节选，全表见 `review/summary_table.txt`）

记法：`0T` 表示目标键失败；`+n` 表示另有 n 个回归键失败；`-` 表示未跑。

| 候选 | h0 原测试 | h1 作者 v1 | h2 v1 无 warns | **h4 复核 v2** | h5 v2 无 warns | h1u | h4u |
| --- | --- | --- | --- | --- | --- | --- | --- |
| base（noop） | 0T | 0T | 0T | **0T** | 0T | 0T | 0T |
| gold | 1 | 1 | 1 | **1** | 1 | 1 | 1 |
| `alt_typeerror`、`r_retry`、`r_kwtuple` | 1 | 1 | 1 | **1** | 1 | 1 | 1 |
| `alt_frame`、`alt_integral`、`alt_prestrip_warn`、`r_none_marker` | 1 | 1 | 1 | **1** | 1 | - | - |
| `q_prestrip` | 0T | 0T | 1 | **0T** | 1 | 0T | 0T |
| `w_literal`、`w_mutate` | 1 | 0T | 0T | **0T** | 0T | 0T | 0T |
| `w_count256`、`w_notin_image`、`w_drop_full`、`w_drop_big`、`w_convert_mutate` | 1 | 0T | 0T | **0T** | 0T | - | - |
| `w_swallow_save`、`w_keep_trns`、`w_nearest` | 0T | 0T | 0T | **0T** | 0T | - | - |
| `deg_off` | 0+7 | 0T+7 | 0T+7 | **0T+7** | 0T+7 | - | - |
| `w_silent` | 0T+1 | 0T+1 | 0+1 | **0T+1** | 0+1 | - | - |
| `w_imout` | 0+1 | 0+1 | 0+1 | **0+1** | 0+1 | - | - |
| `w_getcolors256`（复核者） | 1 | 0T | 0T | **0T** | 0T | - | - |
| **`w_mutate_kept`** | 1 | **1** | 1 | **0T** | 0T | **1** | 0T |
| **`w_nosaveall`** | 1 | **1** | 1 | **0T** | 0T | **1** | 0T |
| **`w_order_cache`** | 1 | **1** | 1 | **0T** | 0T | **1** | 0T |
| **`w_filter_leak`** | 0T | 0T | **1** | **0T** | **1** | 0T | 0T |

**v2 下各候选的失败位置**（`review/evidence/r2_A/<候选>/h4_rv2.out`）：
- `w_mutate_kept`：(b) 之后新加的 `assert im.info["transparency"] == (255, 0, 0)`，实际值为 `0`；
- `w_nosaveall`：新加的 `im.save(out, save_all=True)` 抛 `TypeError`；
- `w_order_cache`：新加的 1×1 白色透明图，`assert "transparency" in reloaded.info` 失败；
- `w_filter_leak`、`q_prestrip`：示例处报 “DID NOT WARN”；
- 其余错误候选在 v2 的失败位置与作者 v1 相同。

**公开测试**：28 个候选中只有 `deg_off`（7 项）、`w_silent`（`test_rgb_transparency`）、`w_imout`（`test_transparent_optimize`）有失败，其余都是 119 passed / 2 skipped。换句话说，B1–B3 与 `w_filter_leak` 在全部公开测试上都是绿的，只能靠隐藏测试拦下。

### 3.3 行为探针（节选，全表见 `review/probe_table.txt`）

| 场景 | base | gold 与 7 个合理实现 | 与之不同的候选（节选） |
| --- | --- | --- | --- |
| P01 题面示例 | `TypeError` | 无透明度，1 条警告 | `q_prestrip`、`w_silent`、`w_filter_leak` 没有警告；`w_keep_trns`、`w_nearest` 带透明度；`w_swallow_save` 读回失败 |
| P02 hopper＋像素 (0,0)；P15 同图经 PNG 读回 | `TypeError` | 无透明度，1 条警告 | `w_literal`、`w_count256`、`w_notin_image` 仍崩溃 |
| P03 示例图＋(255,0,0)；P04 hopper＋纯色条 | 保留（索引 0、90） | 同 base | `w_drop_full` 两处都丢弃，`w_drop_big`、`w_getcolors256` 在 P04 丢弃；**`w_mutate_kept` 把调用者 `im.info` 改成 0、90** |
| P05 示例 `save_all=True` 单帧；P06 两帧相同 | `TypeError` | 无透明度 | **`w_nosaveall` 仍 `TypeError`** |
| P07 两帧不同 | 无透明度，1 条警告（base 本来就能存） | 同 base | `q_prestrip`、`w_silent`、`w_order_cache`、`w_filter_leak` 没有警告 |
| P08 能用透明色的图先存 GIF 再存 PNG | PNG 透明色 (255,0,0) | 同 base | **`w_mutate_kept`：存 PNG 时 `TypeError: cannot unpack non-iterable int object`（`PngImagePlugin.py:1355`）** |
| P09 P01 之后，1×1 图用同一颜色 (255,255,255) | 保留（索引 255） | 同 base | **`w_order_cache` 丢弃**；`w_mutate_kept` 把 `im.info` 改成 255 |
| P13 普通保存一次 GIF 后，再对 `test_trns_RGB` 的同一输入调用 `convert` | 1 条警告 | 1 条警告 | **`w_filter_leak`：0 条，进程里残留 1 条 ignore 过滤器** |
| P11、P11b 关键字传元组 | `TypeError` | gold、`alt_frame`、`alt_prestrip_warn`、`r_retry`、`r_none_marker` 报错；`alt_typeerror`、`alt_integral` 静默忽略；`r_kwtuple` 换成正确索引 | 不作要求 |
| P12 旧接口 `getdata`，P 图 `info` 为整数 | 写透明标志 | 两类都有（见 §2 第 12 条） | 不作要求 |

## 4．`pytest.warns(UserWarning)` 的处理意见：保留

**结论**：这条断言有公开依据，只检查类别，不属于 R-b 要放宽的“无依据实现约束”；也不满足 P5 第二分支“两种读法都有公开依据”，因此不交用户。

**公开依据**：
1. **这是 base 在同一路径上已有的行为。** 警告由 `Image.convert` 的 ADAPTIVE 分支发出（`Image.py:1027-1034`），在崩溃之前就已发出。修复只要不绕开这次转换，警告就自然保留：gold 与 6 个合理实现都是这样；`alt_prestrip_warn` 绕开了转换，但自己发了一条。
2. **公开测试对同一机制直接断言了它。** `Tests/test_image_convert.py:190-191` 用 hopper 加像素 (0,0) 的元组转 P（ADAPTIVE），断言 `pytest.warns(UserWarning)` 且结果无透明度。GIF 保存走的正是这次转换。
3. **公开 GIF 测试对“透明度用不上”的兄弟情形也这样断言。** `test_rgb_transparency` 多帧部分（1100–1108 行）：RGB 图放 `b""`，保存时要求 UserWarning，读回无透明度。
4. **在 base 本来就能保存的兄弟路径上，现有可见行为就是“警告并不用透明度”。** P07（两帧不同）base 有 1 条警告。`q_prestrip` 连这条已能工作的路径上的警告也去掉了，这改变了既有行为，不只是修了崩溃。
5. **只查类别，不查文案、来源或次数。** 自发一句不同措辞 UserWarning 的 `alt_prestrip_warn` 为 1。

**它还挡住一个错误候选：`w_filter_leak`。**
- 这个候选在保存路径里装了一条不还原的全局过滤器。普通地存一次 GIF 之后，整个进程里 `Image.convert` 的这条公开警告都不再出现（P13），而这正是 `test_trns_RGB` 断言的行为。
- 公开测试查不出它，119 项全过。原因有两点：
  - pytest 在每个测试结束时恢复警告过滤器，泄漏带不到下一个测试；
  - 没有哪个公开测试在同一个测试里先存 RGB 图的 GIF、再检查 `convert` 的警告。
- 在隐藏测试里，只有目标键的 `pytest.warns` 能拦下它：h1 为 0、h2 为 1；v2 为 0、v2 无 warns 为 1。去掉这条断言，就要另想办法拦它，例如检查 `warnings.filters` 没被改，那是更靠近实现的检查。

**反方理由（如实登记）**：
- 题面只说 “saved without using transparency, and no exception should be raised”，没提警告；公开读者也把 R8 列为多解释。
- base 另有三处在“256 色已满”时静默处理，注释写 “there is no need for transparency”：`convert` 的非 ADAPTIVE 分支（`Image.py:1080-1087`）、P 模式元组分支（986-989）、`_get_background`。

**我的判断**：
- “题面没提警告”只说明题目不要求去掉警告，不能当作“必须静默”的依据；
- 静默的先例都在别的分支或别的属性上，GIF 保存实际走的 ADAPTIVE 分支在 base 里会警告，并有公开测试断言；
- 所以“必须静默”这个读法没有直接公开依据，P5 第二分支不成立；
- 上游 11.3.0 把这条断言收紧为按文案匹配，说明上游也把它当作行为的一部分。这只作佐证。

**代价与登记**：有意绕开或压掉这条既有警告的实现（`q_prestrip` 类）会得 0。建议在题卡的训练价值与难度备注里写明这一严格点及其依据。估计频率低：解题者要主动绕开 `convert` 才会丢掉警告。

## 5．阻断项

依据：§5 R-c 验收“已知相关的错误候选仍为 0”，以及负责人原则 2：已知错误候选不能因少见或不自然而放过，要么给出修法，要么说明它不违反公开要求。三项都已给出修法，并私有验证。

**B1：保存时改写调用者的图，在“透明色能用”的情形没有被检查（`w_mutate_kept`）**
- **当前行为**：v1 的 (c) 只在示例和 (a) 之后断言 `im.info` 不变，两处都是“丢弃透明度”的情形。`w_mutate_kept` 在 (b)、(b′) 这类透明色能用的情形，把调用者 `im.info["transparency"]` 从 `(255,0,0)` 改成调色板索引 `0`，h0、h1、h2、h1u 都得 1。
- **违反的要求**：与作者判 `w_mutate` 的依据相同：保存不改被保存的图（PNG 文档对 `info` 的定义、GIF 文档的“默认取 info 值”、同仓先例 r2e-mr-063）。这是主路径：带 tRNS 的 RGB 图，透明色是一大片背景色，本来就能放进调色板，这是最常见的来源（作者 §3.2 也这样论证）。
- **可见后果**：同一张图接着存 PNG，抛 `TypeError: cannot unpack non-iterable int object`（P08）。按 `convert` 的代码推断（未实跑），再存 GIF 时整数 0 会被当成颜色 (0,0,0)，透明的变成另一种颜色。
- **修法**：在 (b) 读回断言之后加一行 `assert im.info["transparency"] == (255, 0, 0)`。
- **修后预期**：`w_mutate_kept` 为 0（已测：h4、h4u 为 0），合理实现不受影响（全部为 1）。

**B2：`save_all=True` 只有一帧时没有被检查（`w_nosaveall`）**
- **当前行为**：只修 `save_all=False` 入口的写法在 h0、h1、h2、h1u 都得 1。对题面示例调用 `save_all=True`，或两帧完全相同（被合并成一帧），仍抛 `TypeError`（P05、P06；base 相同，gold 正常）。
- **违反的要求**：K1“保存 GIF 时 `info` 里是元组也不能抛异常”，这是同一核心要求的另一个实例。`save_all` 是文档化的保存选项（`image-file-formats.rst` Saving 节）；只有一帧时，`_write_multiple_frames` 按设计退回同一个单帧写入函数。作者 §3.3 的“没有已知候选利用这一点”已不成立。
- **路径次要**，但修法只需一小段，按原则 2 不宜只登记。
- **修法**：示例部分在 (c) 之后加：

  ```python
      # The same image saved with save_all=True, as a single frame
      im.save(out, save_all=True)

      with Image.open(out) as reloaded:
          assert "transparency" not in reloaded.info
  ```

  这里不再要求警告，以免增加断言面。
- **修后预期**：`w_nosaveall` 为 0（h4、h4u），其余候选不变。

**B3：先前失败过的颜色在后续图上被错误丢弃（`w_order_cache`，依赖顺序）**
- **当前行为**：模块级缓存记住示例里分配失败的 `(255,255,255)`，之后遇到同一颜色就先剥掉。h0、h1、h2、h1u 都得 1。
- **违反的要求**：P1“元组颜色能放进调色板时照常写出透明度”，依据是公开 `test_rgb_transparency` 单帧部分和 base 行为。P09 中，示例之后的 1×1 图透明度被丢掉（base 与 gold 为索引 255）；之后的保存也不再发出既有警告（P05–P07、P10b）。候选写法不自然，但原则 2 不允许因此放过；它恰好也是本批“依赖执行顺序”一类的代表。
- **修法**：在示例部分、B2 那段之后加：

  ```python
      # The same colour is still used for an image with a free palette entry
      im = Image.new("RGB", (1, 1))
      im.info["transparency"] = (255, 255, 255)
      im.save(out)

      with Image.open(out) as reloaded:
          assert "transparency" in reloaded.info
  ```

  它与公开 `test_rgb_transparency` 单帧部分的断言强度相同，只换了颜色，并放在示例之后。
- **修后预期**：`w_order_cache` 为 0（h4、h4u）。这段没有增加新的约束面：只做精确查找、不分配新项的写法，本来就会被公开 `test_rgb_transparency` 的 1×1 用例拒绝（读码推断，未单独造候选）。

**合并后的草案 v2**：
- 文件：`review/materials/hidden_test_1_review_v2.py`，`3573f459d7e313f7b3ca14ae691fccc9268d82ba079de8c7cdb870abf466274a`；
- 编辑块：`review/materials/revision_draft_review_v2.json`（`21581578…`），作用在原件 `ff7a439c…` 上，字段集合等于 RH2 的 `_REVISION_FIELDS`，用 `_apply_edits` 重放得到同一 sha256；
- 与作者 v1 的差别只有上面三段，其它逐字相同；键名与期望映射不变。

v2 的验收（私有模拟）：

| 验收项 | 结果 |
| --- | --- |
| 正对照 gold 为 1、noop 为 0 | 满足，root 与 UID 54322 都是如此 |
| 合理实现不被误拒 | 7 个为 1：作者 4 个、复核者 3 个；上游 10.1.0、10.4.0、11.3.0 的该函数也通过 |
| 已知错误候选为 0 | 作者 13 个与复核者 5 个全部为 0，`q_prestrip` 也为 0 |
| 键集严格相等 | 93 键，没有多余键 |

## 6．非阻断建议

1. **(c) 也可以加在 (b′) 之后**，即 `assert im.info["transparency"] == (0, 255, 0)`，与 B1 对称。只有“只在多于 256 色的图上才改 `info`”这种更刻意的写法需要它，我没有为此造候选，按 §7 登记即可。
2. **更新结论页**：
   - §3.3 S02 那一句改为引用 B2；
   - 交接清单第 3 条的预期分数表加入 `r_retry`、`r_none_marker`、`r_kwtuple`（1→1）、`w_mutate_kept`、`w_nosaveall`、`w_order_cache`、`w_getcolors256`（1→0）、`w_filter_leak`（0→0，无 warns 变体下为 1）；
   - §4 的对照变体一段补上 `w_filter_leak` 的影响：去掉 warns 后它变为 1。
3. **题卡登记 `pytest.warns` 的严格点与依据**（§4），并写明它同时起到拦截全局过滤器泄漏的作用，免得日后被当作可随手删的文案断言。
4. **(b′) 依赖量化器能精确产出 (0,255,0)。** 只要候选不改量化器，这是确定的：7 个合理实现和上游三版都通过。若日后在别的构建上复验，先确认 base 在作者的 S17 上仍是 4096 个像素透明。

## 7．停止条件

- **测试层完成的标志**：
  - 采用 v2，或对作者 v1 做逐字等价的三处改动；
  - 第2类在正式评分链上用派生镜像加修订材料跑一轮诊断评分，结果与 §3.2 表的 h4 列一致。

  至少要跑的候选：

  | 期望 | 候选 |
  | --- | --- |
  | 1 | gold、`alt_typeerror`、`r_kwtuple` |
  | 0 | noop；作者的 7 个触发反例（`w_literal`、`w_count256`、`w_notin_image`、`w_drop_full`、`w_drop_big`、`w_mutate`、`w_convert_mutate`）；复核者的 `w_mutate_kept`、`w_nosaveall`、`w_order_cache`、`w_filter_leak`；`q_prestrip` |

  一致即完成，本题测试层不再需要聚焦复核。
- **之后只登记、不再阻断的反例**：
  - 只在多于 256 色、透明色能用的图上改调用者 `info`（非阻断建议 1）；
  - 只在示例以外的路径去掉警告；
  - 关键字元组、`getdata`、RGB 整数透明度、RGBA 或 P 图带元组的任何行为；
  - GIF 版本号（87a 或 89a）；
  - 其它 GIF 解码器的差异。
- **仍会阻断的新反例**必须同时满足两点：
  - 落在主路径上：满调色板示例类图，多于 256 色的照片或 PNG 读回图，透明色能用的 RGB 图，普通保存或 `save_all` 单帧，保存前后调用者的图；
  - 能指出违反 §4 或本页 B1–B3 所列的哪条公开要求。

  “还能再想出反例”本身不构成继续的理由（review-standards §10.5 第 8 条）。
- **`pytest.warns`**：保留，不需要用户决定。若负责人仍倾向放宽，必须同时补一条能拦住 `w_filter_leak` 的检查，否则会引入新的漏判。

## 8．未查事项

- R2E 正式评分链、派生镜像、D6 或材料修订入口的落地；本页全部是私有模拟。
- Codex 对修订的复核。
- 解题身份（UID 54321）的开发条件：沿用 09-24 环境审查与负责人 devcheck，未重做。
- UID 54322 只抽了 12 个候选 × 2 版材料；其余候选只有 root 结果。
- 上游 10.0.0 没有重跑。上游 PR #7284 页面读不到，改用 PyPI sdist、wheel 与 GitHub raw 上的测试文件。
- 没有真实模型候选，全部候选由主审或复核者构造。
- 16 位 PNG 的 tRNS 元组（分量可能大于 255）、Windows 等其它平台上的量化结果，以及其它 GIF 解码器，都未查。
- 作者关于“只有 1、I 模式转 RGB 会产生 RGB 整数透明度”的说法只读码核对，未实跑。不影响结论。
