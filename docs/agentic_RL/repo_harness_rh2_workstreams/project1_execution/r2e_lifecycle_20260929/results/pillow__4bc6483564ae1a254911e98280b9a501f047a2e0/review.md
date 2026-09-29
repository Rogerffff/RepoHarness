# pillow `4bc64835` 独立复核（第二步）

2026-09-29 08:08（+08，本机时钟）· 独立复核者（Claude，与第一步同一上下文）· 按复核角色卡第二步与统一标准 v1。
没有运行项目代码，没有开容器。唯一的本地计算是在复核者 scratchpad 里重建主审的 R-c 文件、算哈希、做语法解析。
第一步初判见同目录 `reviewer_initial.md`，本文不改它；本文写明哪些初判保留、哪些修改。

路径缩写（都相对仓库根目录）：
- `LIFE/` = `runs/r2e_lifecycle_20260929/`
- `INV/` = `LIFE/inv/pillow_4bc6/`
- `DEV/` = `LIFE/devcheck_rev/unrev/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/`
- `OUT/` = 本题结果目录（本文所在目录）
- `PRIV/` = `runs/r2e_static_prep_20260924/v3/private/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/`
- `wt/` = `runs/r2e_static_prep_20260924/v3/public/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/worktree/`

## 0. 结论

**修订可以开做。** 主审的 R-c（`OUT/card.md` 附录 A.1、A.2）可以原样实施。本题没有已批准的材料修订，不存在冲突，也不需要 D4。唯一的调整是：验收矩阵要实跑 A2。

| 类别 | 内容 |
| --- | --- |
| **同意** | 下面 8 条主审结论，逐条核过（见 §1）：<br>1. 严重度 S1：T2a 由静态阅读确定，T2b 由 D1 实跑 1.0 坐实。<br>2. 处置为 `needs_repair`。<br>3. R-c 的设计：新增 `test_invert_mode_1`，用 `hopper("1")`、独立 oracle，断言模式和尺寸、断言输入不被修改。<br>4. gold 作正对照，不需要 D4。<br>5. W1 属于第 4 步 S1，与 T2 同根，由同一个 R-c 修复。<br>6. v1 四项用途结论。<br>7. X1 关系与 T3 的登记。<br>8. 环境无问题。 |
| **修改** | 1. gold 对非规范取值的问题，处理方式同意（登记为 S2，不断言），但理由要改写：<br>　- 公开**文档**偏向"按 1-bit 值取反"；<br>　- "按存储字节取反"的依据是实现一致性和上游 gold，不是文档；<br>　- 字节 1 由常见写法产生，不是罕见输入（§2.2）。<br>2. A2 从"可选、静态推断"改为验收时实跑（§4）。<br>3. 我撤回初判里推荐的 R-c#2（断言题面原例），改为可选的用户决定项。 |
| **保留（未决，不阻塞）** | 是否要求非规范存储值也按 1-bit 语义反相。<br>- 默认口径：两种约定都接受，测试对此保持中立。这是我的推荐，与主审一致。<br>- 用户若选严格口径，gold 在题面原例上就构成第 4 步 S1，要走 D4、以 A1 作正对照（§2.2）。 |
| **新的高影响问题** | 没有。 |

## 1. 逐项核对主审的决定性主张

| # | 主张（出处） | 我核对的证据 | 判定 |
| --- | --- | --- | --- |
| 1 | D1（mode "1" 时返回 `image.copy()`）正式评分 1.0（`OUT/card.md:16`） | `INV/ledger_D1.jsonl:1`：reward 1.0，`keys_equal=true`，24/24，apply 用户为 agent/54321，`git_apply`，`included_paths=['src/PIL/ImageOps.py']`，`stage_error=null`。<br>日志 `INV/logs_D1/evallog_replay-r2e-inv-4bc6-D1-0_a13fcfcb.eval.log`：:1 显示 `M src/PIL/ImageOps.py`，:6 `APPLY_RC=0`，:27 `test_sanity` PASSED，:51 显示 24 passed。<br>补丁 sha256 `86a32236…`，与 `OUT/cands/pillow_4bc6_D1.patch` 相同。 | **确认。** 补丁确已交付，目标测试确已执行，结果完整，满足 v1 §4 对退化探测证据的全部要求。**T2b 成立。** |
| 2 | D1 确实违反要求（输出等于输入） | `INV/pcheck_canon_D1.json`：输入 `0xA5` 经 D1 后仍输出 `[255, 0, …]`，脚本第 8 行 `assert out.tobytes() == bytes([0x5A])` 失败，报 `b'\xa5'`。这是 root 身份的一次性容器，只证明行为，不是评分 | **确认** |
| 3 | W1（原地修改调用者的图）得 1.0，并且确实改了输入 | `INV/ledger_W1.jsonl:1`：1.0，24/24。<br>`INV/pcheck_canon_W1.json`：输出正确，但第 9 行 `assert im.tobytes() == bytes([0xA5])` 失败 | **确认** |
| 4 | A1、A2 在当前材料下都是 1.0，没有误拒 | `INV/ledger_A1.jsonl:1`、`INV/ledger_A2.jsonl:1` 都是 24/24。`INV/pcheck_canon_A1.json` 为 OK。A2 没有做私有行为检查 | **确认** |
| 5 | gold 对题面原例的输出是 254，按 1-bit 看仍是全白 | `DEV/private_control.json` 的 `results.repro_issue_example.stdout`：<br>- 输入原始值 1，极值 (1, 1)；<br>- 输出原始值 254，极值 (254, 254)；<br>- `equals all-black: False`；<br>- 转成 L 后极值 (255, 255)。<br>这与我初判附录 B 的推断逐项一致 | **事实确认**。定性见 §2.2 |
| 6 | 新机器上 noop 为 0、gold 为 1，与旧机器逐键一致 | `LIFE/env_verify/ledger_l1_noop.jsonl:11`：0.0，只有 `test_sanity` 不符。<br>`ledger_l1_gold.jsonl:11`：1.0，24/24。<br>两次与候选评分用的是同一张镜像 `d6de4045…`（`r2e_derive_v1+sysconfig_v1`，`e2e17bf1…`）。日志里的 `RH2_SETUP_HIDDEN_TESTS_TREE=7e15b739…` 与 v3 材料一致 | **确认** |
| 7 | 解题侧条件已验 | `DEV/orig/captures/env.out`：uid 54321，没有 pip。<br>`env_pil_import.out`：从 `/testbed/src/PIL` 导入，`_imaging` 在树内。<br>`r2e_preflight.out`：三项 ok。<br>`DEV/devcheck.log`：13 项检查全为真，命令 8/8（含 preflight 与 env 两条系统命令，公开读者给的命令是 6 条）。<br>`DEV/orig/attempt.json`：`git_sanitize` 后 refs、remotes、reflog、不可达对象都是 0，HEAD 仍为 base | **确认**（"8/8"的分母含两条系统命令，只是措辞问题） |
| 8 | 所引公开依据 | `wt/src/PIL/Image.py:2418-2421`（thumbnail 特意注明原地修改）✓；<br>`wt/src/PIL/ImageOps.py:575-576`（exif_transpose "return a copy"）✓；<br>`wt/src/PIL/Image.py:1696`（point 默认输出模式与输入相同）✓；<br>`wt/src/PIL/TiffImagePlugin.py:1666-1675` ✓；<br>`wt/setup.cfg:67`（`addopts = -ra --color=yes`，所以期望键带 ANSI）✓ | **确认**。例外：`ImageChops.invert` 那条引用，见 §2.2 第 3 点 |
| 9 | R-c 文件的哈希（`OUT/card.md:111, 148`） | 我在 scratchpad 里把 A.1 的函数追加到 `PRIV/hidden_tests/test_1.py` 的副本上，得到 sha256 `9bdba0cc…`，语法解析通过。<br>`PRIV/expected_output.json` 能用 `json.dumps(indent=4)` 逐字节复现（1480 字节）；加上新键后为 25 键，sha256 `b2a68136…` | **确认** |
| 10 | 证据有没有混用 | 评分账本都是评分用户 54322、断网、当前镜像。<br>`pcheck_*` 和 `private_control` 标注为 root 一次性容器、"not grading"，只用来说明行为。<br>devcheck 的 captures 是 uid 54321、走正式启动路径。<br>主审文中这三类证据分开写，没有把旧机器的行、独立 runner 或一次性试跑当成当前评分 | **没有发现混用** |

## 2. 四个复核重点

### 2.1 W1（原地修改输入）得 1：属于第 4 步 S1；"输入不被修改"这条断言有公开依据

- **判定：** 同意主审，W1 属于第 4 步 S1，与 T2 同根，由同一个 R-c 修复。
  - W1 是审查中构造的候选，v1 第 4 步允许用这类已有候选作证据。
  - 它破坏的是每次调用都会用到的行为，不是边缘路径。凡是反相后还要继续用原图的调用都会受影响，例如 `ImageChops.difference(im, ImageOps.invert(im))`。
  - 因为第 1、3 步已经判为 S1，W1 的归类不改变处置，只决定 R-c 里是否保留"输入不变"这一行。结论是保留。
- **公开依据，按强弱排列：**
  1. **`invert` 自身对 L/RGB 的既有行为。** 走 `_lut` → `image.point(lut)`，总是返回新图、不改输入（`wt/src/PIL/ImageOps.py:53-56, 525-528`）。把 mode "1" 纳入同一个函数，应当沿用同一约定。这一条比主审引用的旁证更直接。
  2. **公开读者独立推出同一要求。** 公开读者没看过 gold 和隐藏测试，却把"返回新图，不修改输入"列入 R3（可推知），并把"原地修改输入图"列为不宜接受的做法（`OUT/public_read.md:26, 71-74`）。这说明该要求不是看了答案之后的说法。
  3. **文档惯例。**
     - `Image.thumbnail` 专门注明会原地修改，并建议先 `copy()`（`Image.py:2418-2421`），说明原地修改是需要特别注明的例外；
     - `exif_transpose` 即使不做变换也返回副本（`ImageOps.py:575-576`）；
     - `docs/reference/Image.rst:332` 写道 "Most methods … when returning new images"。
  4. **仓库在同一功能区的做法。** TIFF 保存对 mode "1" 先 `im.copy()` 再逐像素改（`TiffImagePlugin.py:1668`）。
- **误拒风险：** 看不到。gold、A1、A2、`ImageChops.invert` 路线和"转 L 再转回"路线都返回新图。`hopper("1")` 返回的是缓存图的副本（`PRIV/hidden_tests/helper.py:249-258`），改它不会串到其它测试。

### 2.2 gold 对非规范取值：事实已确认；同意"登记、不断言、不需要 D4"，但理由要改写

1. **事实（实测）：** 见 §1 第 5 行。gold 对题面原例输出原始值 254，任何按 1-bit 解读的视图（`tobytes`、保存、`convert("L")`）都和输入一样是全白。另外，按 1-bit 语义看，gold 与退化候选 D1 在这个例子上无法区分，只是原始值不同（254 对 1）。所以题面原例本身不适合作为"反相正确"的验收实例（主审 `analysis_before_history.md:106` 已指出，我同意）。
2. **新断言不会让 gold 失败，也不需要 D4。** R-c 只用 `hopper("1")`，它由 RGB 抖动转换得到，只含 0 和 255（`wt/src/libImaging/Convert.c:1484, 1515`）。
   - 在规范输入上，gold 逐位反相、模式为 "1"、不改输入，已实测：`INV/pcheck_canon_gold.json`、`DEV/private_control.json` 的 `check_mode1_invert_canonical` 都是 OK。
   - 新测试的比较是在 `convert("L")` 之后做的，不管实现输出 0/255 还是 0/1 都一样。
3. **要改写的理由：**
   - **两种读法的依据并不对等。**
     - 支持"按 1-bit 值取反"的是文档和所有输出路径：`wt/docs/handbook/concepts.rst:28-29` 写明 1-bit 像素取值范围是 0–1；打包、转 L、逻辑运算都把非零当白。
     - 支持"按存储字节取 `255 - v`"的，是实现一致性（L/RGB 的查找表）、`ImageChops.invert` 的**实现**（`Negative.c` 按位取反）和上游 gold 本身。
     - 主审写"`ImageChops.invert` 文档写 `MAX - image`，对 "1" 也得到 254"（`old_findings_delta.md:60`，`analysis_before_history.md:104`），这里把实现当成了文档：文档没有规定 mode "1" 的 MAX；按文档的 0–1 范围算，MAX − 1 = 0，结果是黑色。
   - **字节 1 不是罕见输入。** `Image.new("1", …, 1)`、`ImageDraw` 的 `fill=1` / `outline=1`、`putpixel(…, 1)` 都经过 `getink`，按原始字节 1 存储（`wt/src/_imaging.c:537`；draw_ink 在 `:2783`，putpixel 在 `:1761` 附近）。用这些写法画的掩膜，按 gold 式实现反相后看起来不变。所以这个已登记的缺口应写成"常见的用户自建 1-bit 图在 gold 式实现下看不出反相，评分对此保持中立"，而不是"罕见的边缘值"。
4. **仍同意不断言。** 理由有三：
   - 断言 1-bit 读法，会让上游 gold 和最自然的几种实现（gold、A2、`ImageChops.invert`）判 0，而 Pillow 自己的代码对这类值也不一致（TIFF 反相循环 `TiffImagePlugin.py:1672` 同样让字节 1 保持白色）；
   - 断言原始值 254，又会反过来拒绝 A1；
   - 两种断言都等于替任务选口径。
   
   当前测试和 R-c 对两种读法都中立，不产生误拒，也不会奖励退化解。在"两种约定都接受"的默认口径下，第 4 步不命中，登记为 G1/P4、S2 是一致的。
5. **可选的用户决定（不阻塞）。** 如果用户要求"非规范取值也按 1-bit 语义反相"：
   - gold 就在第 4 步构成 S1；
   - 按 D4 以 A1 作正对照，补一个题面原例断言，并记录 gold 的失败；
   - 先要在 A1 和 A2 下各跑一次 `repro_issue_example` 留证（A1 预期原始值 0、全黑；A2 预期 254、仍白）。

   我推荐维持默认口径。`screening_record.json` 里 `P4-G1-noncanonical-example` 的 summary，建议按第 3 点改写依据与常见程度。

### 2.3 新增键与已批准修订不冲突；建议保持独立键，不并入 `test_sanity`

- **没有冲突：**
  - `PRIV/revisions.json` 是 `[]`；
  - `PRIV/run_refs.json:3-9` 的 `material_revisions` 为空；
  - `PRIV/grading_bundle.json` 的 `material_revisions` 为空；
  - 协调者确认本题 v3–v9 材料相同。
  
  所以没有任何已批准的期望修订会和新增键冲突。新键名与现有 24 键不重名，也没有参数化。
- **建议保持独立键 `test_invert_mode_1`（同意主审首选）：**
  - 失败时，能把"修好了报错但输出不对"（只挂新键，如 D1、W1）和"没修好报错"（`test_sanity` 也挂）分开，对问题定位和事后分析有用；
  - 上游的 `test_sanity` 原样保留。
- **独立键的代价与核对点：**
  - 期望映射从 24 键变成 25 键，要在修订单里声明"新增 1 键"；
  - 同步更新 grading bundle 里的隐藏测试树与期望的 sha256，并重建派生镜像（隐藏测试在镜像里）；
  - 验收时核对：25 键严格相等，新键在日志里确实执行。
- **什么时候改为并入：** 只有当修订机制不方便加键时，才把断言并入 `test_sanity` 第 66 行之后，这样键集不变。两种写法都在 R-c 范围内。

### 2.4 A2（放宽 `_lut`）不会被新断言误拒

- A2 在 mode "1" 上执行的就是 `image.point(lut)`，查找表同为 256 项的 `255 - i`（`_lut` 只对 RGB 做三倍扩展）。所以它对任何输入的输出都与 gold 逐字节相同，新测试下的行为也与 gold 一致，预期得 1。
- 它的副作用只是让 posterize、solarize、autocontrast、equalize 也接受 "1"。25 个键里没有一个期望这些函数对 "1" 抛错（唯一的 `pytest.raises` 是 `test_scale` 的 `ValueError`），所以不会因此改变任何键。
- 它对非规范值的行为与 gold 相同（254），新断言不涉及。
- **建议：** A2 代表公开读者的第一条路线（`OUT/public_read.md:48`），又最接近上游写法，验收时应实跑一次（约 75 s），不要只靠静态推断。

## 3. 反查：主审可能没覆盖的范围

- **其它合法实现。**
  - `ImageChops.invert(image)`：按位取反，规范输入下 0↔255，返回新图、模式为 "1"；
  - "转 L 反相再 `convert("1")`"：输入只有 0/255 时抖动不改变结果；
  - 输出原始值为 0/1 的实现：新测试在 `convert("L")` 之后比较。

  按源码推断，这三种在 R-c 下都得 1。不需要逐个实跑，A1、A2 已覆盖两类代表。
- **错误实现是否还能漏过。** 下面几种按源码推断都会被 R-c 拒绝，不需要另跑：
  - 输出 mode "L"：模式断言拒绝；
  - 固定输出全黑或全白、只反相一部分、尺寸不对：像素或尺寸比较拒绝。
- **`out.mode == "1"` 这一行建议保留。** 主审把它标成"依据较弱、可删"，但它有三条依据：
  - `invert` 对 L/RGB 一直保持模式；
  - `point` 默认输出模式与输入相同；
  - 公开读者独立推出了同一要求（`OUT/public_read.md:26, 73`）。
- **可选的 T3 项（`test_invert_l_rgb_values`）。** 如果加上，就是第 26 个键。它在 base 上也能通过，所以 noop 下也会 PASSED，属于回归键，验收时要按此核对。不加也不影响处置。
- **其它模式。** 候选把其它模式的报错改成静默返回，属于题面之外的旧行为，最多算 S2，不要求补测。
- **平台面（与本题无关，只作提醒）。** `DEV/orig/post_run_facts_root.txt` 显示，devcheck 期间 `.venv/lib/python3.9/site-packages/_pytest/**/__pycache__` 下新写了 pyc 文件，即 agent 对 venv 的部分目录可写。这与旧记录 R07（venv 可写，属反作弊面，另议）是同一类问题，归 A 线，不影响本题结论，本轮没有核实导出与评分是否会带上这些文件。

## 4. 对 R-c 的意见与验收

- **实施内容：** 按 `OUT/card.md` 附录 A.1、A.2 原样实施，包括 `out.mode == "1"` 和"输入不变"两行。**不加**题面原例断言。T3 项可选。
- **验收矩阵（全部用正式评分、在重建后的派生镜像上跑）：**

  | 候选 | 预期 reward | `test_invert_mode_1` | `test_sanity` |
  | --- | --- | --- | --- |
  | gold（正对照） | 1 | PASSED | PASSED |
  | noop | 0 | FAILED（OSError） | FAILED（OSError） |
  | D1（触发反例） | 0 | FAILED（输出等于输入） | PASSED |
  | W1（触发反例） | 0 | FAILED（输入被改） | PASSED |
  | A1（替代正对照） | 1 | PASSED | PASSED |
  | A2（替代正对照，**本复核要求实跑**） | 1 | PASSED | PASSED |

- **每条都要额外核对：**
  - 键集严格等于 25 键；
  - 日志里新键确实执行；
  - 投影 `included_paths` 为 `src/PIL/ImageOps.py`；
  - 隐藏测试树的哈希与修订单一致。
- 之后保存新旧版本、理由和触发反例（D1、W1），交 Codex 复核。
- 修订后的题只能作"标明版本的自建题"。

## 5. 用途（v1 四项，复核意见）

同意主审（`OUT/screening_record.json:172-177`）：

| 用途 | 结论 | 说明 |
| --- | --- | --- |
| 问题定位 | yes | — |
| 能力比较 | conditional | 条件是预登记的事后审计：对得 1 的补丁跑 `check_mode1_invert_canonical`，原始 reward 与审计结果分列；或者直接用 R-c 后的版本 |
| 训练候选 | no | 当前有未处理的 S1；R-c 验收并经 Codex 复核后重评 |
| 留出评测候选 | no | 同上；另有 X1 |

补充一条：R-c 后重评训练候选时，把 §2.2 改写后的已知缺口（常见的非规范 1-bit 图，评分中立）一并登记为 S2。这不构成障碍，前提是用户维持默认口径。

## 6. 最小后续实验

1. **R-c 验收：** 按 §4 跑 6 次正式评分。这是必需的。
2. **可选：** 只有用户考虑严格口径时，才在 A1 和 A2 下各跑一次 `repro_issue_example`，一次性容器即可，为 §2.2 第 5 点留证。

## 7. 与第一步初判的关系

| 初判内容 | 现在的处理 |
| --- | --- |
| S1（T2a）；退化候选得 1 的推断（我初判里叫 W1，即协调者的 D1） | **保留**，并已由实跑坐实 |
| gold 对题面原例的推断（附录 B） | **事实保留**，已由实测坐实 |
| 把它作为第 4 步的条件项、推荐 R-c#2 | **修改**：降为可选的用户决定项，理由见 §2.2 |
| R-c 的写法 | **采纳主审版本**：与我初判的 R-c#1 实质相同，多了"输入不变"一行。我初判里的纯色图断言不是必需的 |
| 用途四项 | **保留**，与主审一致 |

## 附录：第二步新增的读取范围

- **`OUT/`：**
  - 全文：`public_read.md`、`commands.json`、`analysis_before_history.md`、`old_findings_delta.md`、`card.md`、`screening_record.json`、`cands/*.patch`（4 个）。
- **历史：**
  - 全文：`runs/r2e_static_prep_20260924/v3/history/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/refs.json`；它所列本题的 `findings.md`、`repros/…py`。
  - 只看了摘要字段：本题 `screening_record.json`（`disposition`、`issues`、`usage`、`revision_refs`）和 `facts.json`（键和 `identity`）。
  - 只 grep 了本题条目：`known_issues.json`、`decisions.md`、`results_20260924.md`、`packages/p4/README.md`（后者另读了开头 30 行）。
- **`LIFE/` 下的新机证据：**
  - `env_verify/ledger_l1_{noop,gold}.jsonl` 第 11 行；
  - `INV/`：`ledger_{D1,A1,W1,A2}.jsonl`（关键字段）、`logs_*/…eval.log`（开头、摘要段与结尾）、`pcheck_canon_{none,gold,D1,A1,W1}.json`、`run.sh`、`pcheck_canon.sh`、`run.log`，以及补丁 sha256 与 `OUT/cands/` 的比对；
  - `DEV/`：`devcheck.log`、`private_control.{json,log}`、`orig/captures/*.out`、`orig/activation_check.json`、`orig/post_run_facts_root.txt`、`orig/attempt.json`（关键字段）、`orig/bringup_artifacts/cc_version_observed.json`。
- **补查的公开源码：**
  - `wt/src/PIL/Image.py:2410-2425`、`wt/src/PIL/ImageOps.py:573-580`、`wt/docs/reference/Image.rst:326-336`、`wt/docs/reference/ImageOps.rst:1-12`、`wt/setup.cfg:67-68`；
  - `wt/src/_imaging.c` 中 `_putpixel` 与 `_draw_ink` 调用 `getink` 的位置；`wt/src/PIL/ImageDraw.py` 中 `_getink` 的片段。
- **本地计算：** 只在复核者 scratchpad 里重建 R-c 文件，算哈希、做语法解析，没有运行测试。
