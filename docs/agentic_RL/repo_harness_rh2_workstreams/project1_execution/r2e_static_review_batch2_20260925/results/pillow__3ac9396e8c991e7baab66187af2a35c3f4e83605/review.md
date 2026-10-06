# 独立复核（第二步）：pillow__3ac9396e8c991e7baab66187af2a35c3f4e83605

2026-09-25，独立复核者。封存初稿见 `reviewer_initial.md`，本文不改动它。本文只做静态阅读和已有证据核对，没有运行代码或容器，也没有修改任何原件。协调者 09-25 跑的候选评分与私有容器核对是执行事实，本文只核对这些事实能否支持各项主张。

## 0. 结论

- **同意主审的处置**：作为开发诊断用的静态候选，state 保持 `needs_review`，reason 为"静态候选，待 actor 验证"；不修订材料。
- **同意主审的主要事实**，包括：根因与分母是否为 0 无关；唯一目标键是 `test_exif_div_zero`；期望里没有非 PASSED 键；隐藏测试用的是自带的 helper；pytest 在本仓有恒定噪声；本题修复出现在同仓 6 题的公开初态里；"评分镜像与 devcheck 镜像不同"这一缺口已经关闭。
- **修改三处**：
  1. **漏测要扩大到回归面，并提升证据级别**。主审只写了"部分修复也能过"（K2、K4b）。实跑表明，引入回归的错误实现也能得 1：我的 C6 把未注册 tag 的整数写成 RATIONAL，reward 为 1（11/11）。私有容器核对中，65000=5 读回为 `(5.0,)`、类型 5，base 与 gold 都读回 `(5,)`。check 25 与 26 的证据级别应从"静态推断"改为"当前 CPU、真实 RH2 评分"，并写入 C6。
  2. **I2 的措辞要修改**。"K2 不算违背题意"只在题面字面上成立。公开文档把"IFDRational 按类型自动识别"写成了一般约定，devcheck 实测 base 上 1/2 同样失败，K2 却只处理分母为 0 的情况。它是满足字面要求的特判，不宜写成可以接受的等价解。原始 reward 1 保留；这条差异只作为"奖励无法区分根因修复与特判"的记录，对训练用途更相关。
  3. **H17 的因果只是推断**。主审把"来源宿主机上 `test_ifd_rational_save` 为 ERROR"归因到缺少 libtiff，但主审自己也写明没有重读宿主机记录。结论可以写成"该键依赖 libtiff 编码器（静态加镜像实测），来源宿主机 ERROR 的原因未核实"。
- **更正我初判里的一条修订建议**：我曾建议可选地补一个"未注册 tag 写非零分母"的键。**这会把需求扩大到题面字面范围之外**，K2 满足题面文字却会被判 0。因此除非同时修订题面（属于 T0，由用户决定），否则不建议这样改。只针对 C6 的"旧行为保护"键不扩大题面需求，但断言写法有陷阱，见 §3。
- **最小后续实验**：处置层面已经不需要 CPU 实验，剩下的是 actor 验证：真实消息的渲染，以及真实模型求解。只有在决定为 C6 补回归键时，才需要先在私有容器里用 gold、K1、K4b、C6 四个候选试跑候选断言（见 §6）。

## 1. 主审决定性主张的逐项核对

| # | 主审主张（出处） | 引用是否支持 | 证据是否对应当前材料、用户和环境 | 判定 |
| --- | --- | --- | --- | --- |
| A1 | 唯一目标键是 `test_exif_div_zero`：noop 为 ERROR，报错与题面逐字相同；gold 为 PASSED；共 5 次、分布在 3 个 build 上（analysis §1、card §2、delta H2） | 支持。我逐个核过：RF 的 all、reps、requal 三组，环境轮复跑，以及 09-25 `ledger_p3ac9_noop.jsonl`（日志 `…ed969340eccc-pill_029f6ef4`）。image 分别是 `74c3618c`、`7a80aa71`、`c9ec14f7`，mismatched 都只有这一个键 | 都是 current 材料：隐藏测试树为 `43f98461…`，评分用户 54322，正式评分代码（`scripts_digest 054f8a04…`、`profile 1bb8e0cf…`） | 同意 |
| A2 | 根因是 `TagInfo` 默认 `type=4`，使猜类型分支执行不到；与分母是否为 0 无关（analysis §0、I1） | 支持。源码为 `TiffTags.py:26`、`TiffImagePlugin.py:496-503`。devcheck 的 `pr3_2` 以 agent 身份在 `c9ec14f7` 上运行：base 上 41988 写 1/2 失败，282 写 0/0 成功；私有核对 `p3ac9_none.json` 也是 zero 与 half 都 RAISES | 对应 actor 身份与当前镜像 | 同意 |
| A3 | 读回形状 `[0]` 来自题面示例，没有只能从隐藏材料得知的要求（analysis §3 反查） | 支持。公开读者在接触隐藏材料之前，已经独立推出 R3（元组形状）与 R4（必须写成有理数类型），见 `public_read.md:31-32` | 这是公开侧先行得出的推断，不属于看过答案后说"显然" | 同意 |
| A4 | K1、K1b 得 1，隐藏测试不限定类型码；K3 得 0 且目标键为 FAILED；K4 得 0 且目标键为 ERROR（TypeError）；K4b 得 1（card §5） | 实跑与预测逐项一致。K3 日志第 36–38 行为 `AssertionError: 0 != 1`，状态 FAILED；K4 日志第 36–38 行为 `TypeError: 'IFDRational' object is not subscriptable`，状态 ERROR。其余键全部 PASSED | 均在 `c9ec14f7` 上跑，apply_ok；`included_paths` 与补丁一致 | 同意（从静态升级为实测） |
| A5 | K2 得 1，但 1/2 仍会失败；"因为题面只描述了零分母，这不算违背题意"（I2、analysis §4） | 事实部分得到支持：K2 reward 为 1，`p3ac9_pillow_3ac9_K2_zero_denominator_only.json` 中 half 仍 RAISES。评价部分见 §2 | 私有核对以 root 身份、不联网运行，是执行事实 | **修改**措辞 |
| A6 | gold 让未注册整数标签的类型码从 LONG 变为 SHORT，读回的值不变（I3） | 现在有实测：`p3ac9_ir_pillow__3ac9396e…json` 中 int65000 读回 `(5,)`、类型 3；base（`p3ac9_ir_none.json`）为 `(5,)`、类型 4 | 同上 | 同意，证据升级为实测 |
| A7 | pytest 噪声落在提示指定的路径上；unittest 方式 42 个全 OK（I4、H8） | 支持：`pr7_4_pytest.out:304-314`、`pr8_5_cmd.out:122-124`；私有 gold 对照的计数相同 | actor 身份，当前镜像 | 同意 |
| A8 | 本题修复与两个新增测试出现在同仓 6 题的公开初态里；gold 扫描漏报（I5、N4） | 支持。我在初判中独立核过 6 个公开 worktree 的 `TiffTags.py:26` 与 `_setitem`，结果相同 | 只看公开包 | 同意 |
| A9 | "镜像 build 不同"的缺口已关闭（delta §2） | 支持。09-25 在 `c9ec14f7` 上跑了 noop、gold 以及 7 个候选，`recipe_sha256 0da821a1…` 与历史运行相同 | — | 同意，我初判的 G5 随之关闭 |
| A10 | 未跟踪的 `temp.tiff` 会经 `git add -N .` 加 `diff --binary` 被交付，不影响得分（delta §2、check 16） | 我核了 `rh2/src/repoharness2/grading/manager.py:329-373`：导出只排除基线未跟踪文件清单；worktree 的 `.gitignore` 里没有 `*.tif*`。隐藏测试不读 `/testbed/temp.tiff` | 只做了静态核对，没有实跑；R2E actor 链是否确实经过这段导出脚本，我没有追到调用处 | 同意"静态、低风险、可选实跑"的定级 |
| A11 | `test_ifd_rational_save` 依赖 libtiff；来源宿主机上它是 ERROR，原因是缺 libtiff（card §4.6、H17） | 依赖 libtiff 有依据：`WRITE_LIBTIFF=True` 这一轮会走 `Image._getencoder(..., 'libtiff', ...)`（`TiffImagePlugin.py:1433`），devcheck 中 `libtiff_encoder True`。但 `expected_provenance.md:15` 只记录了"PASSED→ERROR"，没有记录原因，主审也写明没重读宿主机记录 | 原因只是推断 | **修改**：写成"依赖 libtiff，宿主机 ERROR 的原因未核实" |
| A12 | 设计对照 c（sleep）在导入阶段就 SyntaxError，没有测到期限耗尽（旁注） | 支持：`evallog_replay-r2e-rf-contrast-c_5f93e150.eval.log:42-44,73` | diagnostic 行 | 同意 |
| A13 | v3 提示已改成"pip may be unavailable"，历史 issue 1 已过时（H7） | 支持：`public_bundle.json` 的 `public_hints` | — | 同意 |

## 2. 候选实跑对照（两套命名）

补丁都在 `runs/r2e_actor_20260925/grader_cands/`，我逐个读过。**K4 与 C4、K4b 与 C3 是同一行改动**，只是插在 dict 开头的位置不同，不影响行为。RC6 就是我的 C6。

| 主审 | 我的初判 | 补丁要点 | 预测 | 实际（c9ec14f7，各 1 次） | 私有核对（root、不联网） | 判读 |
| --- | --- | --- | --- | --- | --- | --- |
| K1 | 与 C1 同类 | `_setitem`：未注册 tag 且值全是 IFDRational 时设 5 | 1 | 1（11/11） | 41988 写 0/0 与 1/2 都 OK，类型 5 | 合理替代解被接受 |
| K1b | — | 同上，类型设 10 | 1 | 1 | 未跑 | 隐藏测试不限定类型码 |
| K2 | — | 只在分母全为 0 时设 5 | 1 | **1** | 1/2 仍抛 `struct.error` | 满足字面要求的特判也能得 1 |
| K3 | 与 C5 同类（错误实现） | 只给 IFDRational 加 `__index__` | 0 | 0，目标键 FAILED（`0 != 1`） | — | 正确拒绝 |
| K4 | C4 | 登记 41988 为 RATIONAL，长度 1 | 0 | 0，目标键 ERROR（TypeError） | — | 违反公开示例的 `[0]`，被拒有公开依据 |
| K4b | C3 | 同上，长度 0 | 1 | **1** | 0/0、1/2 都 OK；int65000 仍为类型 4 | 只修 41988 的窄修复也能得 1 |
| — | C6 | gold，但判断改成 `isinstance(v, Rational)` | 1 | **1** | int65000 读回 **`(5.0,)`、类型 5**；gold 读回 `(5,)`、类型 3 | 引入回归的错误实现被接受 |

**同一个失败键，合理程度不同**：noop、K3、K4 都只错 `test_exif_div_zero`，但三者性质不同。K3 违反 R2：读回分母是 1。K4 按 EXIF 规范把计数写成 1，符合现代 Pillow 的写法，但违反公开示例的读回形状。原始 reward 都保留为 0。K4 只能记作"遵循外部规范、违反公开示例"的样本；公开读者在读隐藏材料前已经推出了 R3，所以 K4 不算误拒，也不需要列为规格争议。

## 3. 主审没有覆盖到的范围（反查）

1. **回归面漏测（新增，实测）**：C6 得 1，但它把未注册 tag 上的 int 静默改成了有理数。
   - 这违背文档里"数值自动识别"的约定（`image-file-formats.rst:503-510`），也违背 base 的旧行为（公开读者 P5：一律 LONG）。
   - v1 旧 API 下，读回的元素也会从 int 变成 IFDRational 元素。这一条只是静态推断，没有实测。
   - 公开读者在 `public_read.md:66` 已经点名了这个陷阱，所以它是一个现实的错误方向，不是凭空构造的。
   - 主审的 check 25 写的是"错误修复会被拦下（K3）"，只覆盖了一类错误实现，这句话不能推广到所有错误实现。
2. **等价性比较有陷阱**：`IFDRational.__eq__` 委托给 `_val`（`TiffImagePlugin.py:305-306`），所以 `IFDRational(5,1) == 5` 成立，`(IFDRational(5,1),) == (5,)` 也成立。
   - 如果以后为 C6 补回归键，只断言相等**区分不出** C6，必须断言值的类型，例如 `type(v[0]) is int`，或者断言 v1 API 的形状。
   - 同时**不能断言类型码为 4**：gold 会得到 3，那样 gold 反而判 0。
   - 这是任何修订草案都必须带上的约束。
3. **K4b 的窄修复只在 41988 上实测过**。它对其它未注册 tag（例如 65000=`IFDRational(1,2)`）仍会失败，这一点只是静态推断，没有实跑；私有核对里的"其它 tag"只测了 int。
4. **环境卡与本题入口不一致**（我初判的 G6，主审没有提到）：`r2e_environment_card.md` §1 写的是 `pytest -rA r2e_tests`，本题实际是 `unittest_custom_runner.py`。评分可用已由运行证明，只影响环境卡的描述，建议协调者在卡上注明"入口按题不同"。
5. **dict 形式的 `tiffinfo` 与 v1 IFD 的写入路径**：`_save` 在复制类型时 `except: pass`（`:1318-1321`），对 dict 形式会依赖 ifd 自身的推断。gold、K1 预计都能处理，K4b 也可以（按 tag 登记）。没有测试覆盖，这是题面范围外的低风险项，只记录，不影响结论。

## 4. "先看答案再说显然"与公开疑义的检查

- 主审的隐藏要求 R3（元组形状）、R4（有理数类型码）都在公开读者记录里预先出现过，**没有**"先看答案再说显然"的问题。
- 公开读者列出的关键未知（`public_read.md:265-270`）都能由公开材料或执行事实消除：
  - 类型码 5 还是 10：K1b 实测不限定。
  - 保存前的 `tagtype` 不被检查：隐藏测试没有这条断言，所以在保存阶段修复的做法也会被接受（静态推断）。
  - 非零分母：没有测试。
  - `_imaging`、导入路径、pytest 是否可用：devcheck 已实测。
- 公开读者的疑义都不构成题目缺陷；其中"零分母框定过窄"已由主审记为 I1。

## 5. "可探针"与修订建议的检查

- **可探针**：主审把"静态候选"与"剩余条件"分开了（I6 actor 待验；check 3 为 unknown；check 33–36 为 not_checked），没有把 09-24 的 `environment_qualified` 当成质量合格（delta §0 与 §4 写明两者范围不同）。符合要求。
- **修订建议**：主审只提了环境说明层面的 S3（注明 pytest 噪声和 unittest 替代方式），不涉及题面和测试，不扩大需求，也不泄漏答案。同意，是否采纳由任务面决定。
- 我初判 §7 的可选修订（补一个非零分母的键）**撤回**，理由见 §0。如果将来为训练用途要收紧奖励，有两条路，都属 T0，由用户决定：
  - 题面与测试同时扩大到"未注册 tag 上的任意 IFDRational"；
  - 只补 C6 的旧行为保护键，受 §3 第 2 条的断言约束。

## 6. 建议主审记录做的具体改动（由协调者收口，我不改主审文件）

- `checks.25`：证据改为"当前 CPU、真实 RH2 评分"。写明 K2、K4b（C3）、C6 各得 1，K3、K4（C4）各得 0。删掉"错误修复会被拦下（K3）"这句的一般化表述。
- `checks.26`：在 gold 的类型码变化（已实测 3 对 4）之外，补上"未注册 int 的值类型没有回归保护，C6 把它变成 IFDRational 仍得 1"。
- `checks.24`：由"待实跑确认"改为"已确认"：K1、K1b 为 1；K4 为 0，但被拒有公开示例依据。
- `issues`：
  - I2：摘要改成"满足字面要求的特判、窄修复和引入回归的错误实现都能得 1；奖励无法区分根因修复"，evidence_level 改为当前真实 RH2 评分，severity 对诊断用途保持 low，对训练用途标 medium-low。
  - I3：证据级别升级为实测。
  - 可以另起一条 C6 的记录，或并入 I2。
- `checks.7` 与 card §4.6：libtiff 的因果改为"原因未核实"。
- `proposed_experiments`：把 K1–K4b 与 RC6 的实跑结果和账本路径写进去，next_step 改为 actor 验证。

## 7. 与我初判的差异

- **初判 §0 中"C3、C6 的静态预期为 1，C4 为 0"**：全部由实跑确认。
- **初判 G5（镜像 build）**：已关闭。
- **初判 G1 的修订方向**：部分撤回，见 §0 与 §5。
- **初判漏掉的一点**：`test_ifd_rational_save` 是一个依赖环境（libtiff）的回归键，由主审提出，我同意，但因果需要改为"未核实"（A11）。
- **初判没有考虑的一点**：未跟踪的 `temp.tiff` 怎样交付，由主审提出，我同意"静态、低风险"的定级。

## 8. 未解决或保留的分歧

- **K2 的定性**：主审认为"不算违背题意"；我认为"符合字面要求，但偏离文档约定和根因的特判"。两边的事实没有争议，差别只在记录措辞和训练用途的严重度。由协调者裁定；原始 reward 1 不变。
- **C6 是否要单独补回归键**：我倾向于只记录，不修订。本题当前用途是开发诊断，修订属于 T0。这一条没有与主审直接冲突，但在主审的记录里目前缺失。

## 9. 最小后续实验

1. **处置层面不需要 CPU 实验**。唯一的下一步是 actor 验证：模型实际收到的消息，以及真实模型求解（主审的 S4）。
2. **可选，只在考虑为 C6 补回归键时做**：在私有容器里对 gold、K1、K4b、C6 运行一段候选断言，判定标准是 gold、K1、K4b 为真、C6 为假。候选断言是：未注册 tag 65000 写 5 后读回，`type(v[0]) is int`。先确认这条断言能区分，再谈修订。
3. **可选**：主审的 S2（未跟踪 `temp.tiff` 的实跑交付对照），只关系到共享机制。

## 附录：本步读取范围

- `OUTPUT_DIR` 中的 `public_read.md`、`analysis_before_history.md`、`old_findings_delta.md`、`card.md`、`screening_record.json`（全文）。
- 历史：`runs/r2e_static_prep_20260924/v3/history/pillow__3ac9396e…/refs.json`，以及其中列出的：
  - `findings.md` 全文；
  - `screening_record.json` 的 checks、issues、solver_conditions、classification、disposition；
  - `facts.json` 中的 install_mode、pth_line 字段；
  - `repros/pillow__3ac9396e….py` 全文；
  - `known_issues.json`、`results_20260924.md`、`packages/p4/README.md` 中与本题相关的行（grep）。
  - `decisions.md` 中没有本题条目，没有展开阅读。
- `runs/r2e_t0_batch2_20260924/provenance/expected_provenance.md` 中本题所在的行。
- 协调者 09-25 的证据：
  - `runs/r2e_actor_20260925/grader/ledger_p3ac9_*.jsonl`（9 份）；
  - K3、K4、K4b、K2、RC6 的 eval 日志（关键行）；
  - `private_public_b2/p3ac9_*.json`（8 份）；
  - `grader_cands/pillow_3ac9_*.patch`（7 份）；
  - `pillow_3ac9_extra_commands.json`。
- 为核对 A10，读了 `rh2/src/repoharness2/grading/manager.py:315-380`，以及公开 worktree 的 `.gitignore`（grep）。
- 为核对 A12，grep 了 `evallog_replay-r2e-rf-contrast-c_5f93e150.eval.log`。
- **没有读**：本批 README、`assignments.json`、`grader_candidates.md`；首批审查目录、Codex 复核目录及其它 review 目录；其它题的私有包；P4 的 `dev_probe` / `targeted*` 原始日志；`reconcile.json`。
