# 题卡：pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96

2026-09-29 · R2E 私有主审（单题闭环试行，统一标准 v1）· 依据：[`analysis_before_history.md`](analysis_before_history.md)（读历史前封存）、[`old_findings_delta.md`](old_findings_delta.md)、今晚新机器上的实跑。独立复核尚未进行。

**结论**：评分链可靠，题意可以从公开材料推断出来。但隐藏测试有两处 S1 漏判，**进训练前必须先做 R-c1 + R-c2**。不需要用户决定。处置为 `needs_repair`（scope `static_review`）。

## 1. 目标、版本与用途

- **目标**：保存 `'1'`/`'L'` 模式的 TIFF 时，保留用户在 `tiffinfo` 里给的 `{262: 0}`（WhiteIsZero，即 0 表示白）。base 在 `TiffImagePlugin._save` 里用默认值 1 把它覆盖了。
- **版本**：
  - 来源：R2E `e8b9fcbc`；base `5db0969f`（Pillow 8.4.0.dev0）；材料 `expected_v0`，没有修订。
  - 派生镜像：`rh2-r2e-derived/pillow:2d01f7d02243-r2e_derive_v1s`（`sha256:2a981728…`，配方 `r2e_derive_v1+sysconfig_v1`）。
  - 新机器上：noop 为 0，gold 为 1。

**v1 四项用途**

| 用途 | 结论 | 还差什么 / 依据 |
| --- | --- | --- |
| 问题定位 | yes | — |
| 能力比较 | conditional | 二选一：<br>① 用 R-c 验收后的版本，并标明版本；<br>② 在原版上预登记事后审计：得 1 的补丁都要核对"默认值和显式 1 仍写 1"与"压缩保存可用"，原始 reward 和审计结果分开记。<br>开发路径和评分条件已经核过（devcheck、新机器 noop/gold）。 |
| 训练候选 | no（当前版本） | 两个 S1 还没处理。R-c1 + R-c2 验收并经 Codex 复核后重新评估；预计转为 yes，届时 S2 缺口已登记。 |
| 留出候选 | no（当前版本） | 先要满足训练候选的条件。另外，同仓 4 道更晚的题的初始工作树里含有本题答案，所以 pillow 必须整仓放在留出侧（D3）。修订后只能作为"标明版本的自建题"。 |

## 2. 关键需求—测试映射

| 需求 | 公开依据 | 测试 / 断言 | 覆盖 | 证据 |
| --- | --- | --- | --- | --- |
| `'1'`/`'L'` 写 262=0 后读回 0 | 题面 `UP:7,26` | `test_photometric[1]`、`[L]`，`T1:456` | 覆盖 | noop 失败于 `assert 1 == 0`；gold PASSED |
| 写 0 时像素往返不变 | 读取端会反相解码（`TIP:136,160`）；公开测试断言 WhiteIsZero 与 BlackIsZero 两种文件解出同一张图；base 本来就能往返 | `T1:457`，`assert_image_equal` | 覆盖；题面没明写 → P4 | 只改标签的 C2 在这里失败，得 0 |
| 不指定时默认仍写 1；显式指定 1 时写 1 | 默认值表 `SAVE_INFO`（`TIP:1459-1460`）；题面 "retain the specified…" | 无 | **缺失 → S1（T2b）** | 退化候选 D 得 1（62/62）；私有对照里 D 把这两种情况都写成了 0 |
| 压缩（libtiff）保存同样可用 | 文档列出的 `compression` 选项；覆盖 262 的那一行在两条写出路径分叉之前 | 无 | **缺失 → S1（第 4 步）** | C3 得 1，但两种压缩保存都抛 `AttributeError: encoderconfig`（镜像里 libtiff 4.3.0 可用） |

## 3. 八个方面：查了什么、没查什么

- **公开需求**：已查。题面只写了标签值，像素语义要从读取端推断（P4）。
- **材料与初态**：已查。隐藏测试就是 base 的测试文件加上 `test_photometric`；noop 的失败原因与题面一致；devcheck 在 base 上复现了问题。
- **测试是否测到要求**：已查。有两处 S1 缺口（见上表）。T3 级缺口没有覆盖：`tiffinfo` 用 IFD 对象或元组的写法、其它模式和取值、多帧保存、保存时调用方图像被就地改动（最后一项没有构造候选）。
- **会不会误拒合理解**：已查。范围更窄、改用 packer 的替代解 C1 得 1。
- **回归与 gold**：已查。gold 在全部公开要求上都正确，四项私有对照都通过。gold 还把"尊重用户给的 262"扩大到所有模式和取值，并对 `'1'` 用逐像素循环（G1）。这两点都不是题面要求，也没有测试。
- **开发条件**：已查（devcheck，agent 身份，Claude Code 2.1.205 + 桩端点）。PIL 从 `/testbed/src` 导入；libtiff 4.3.0 可用；没有 pip，解题也不需要；公开 TIFF 测试有 2 个与本题无关的基线失败。未验证：模型实际收到的消息、经 adapter 的链路（A 线通用问题）。
- **交付与评分边界**：已查。补丁只改 `src/PIL/TiffImagePlugin.py`，按 `included_paths` 交付；2 个死键结果稳定，不影响判分。没查：`.venv` 对 agent 可写这类通用反作弊面（A 线）。
- **题目关系**：已查（X1）。本题 gold 和 `test_photometric` 出现在 `4bc64835`、`3a61c9e9`、`f9d3ee0f`、`a682ceaf` 四题的公开初态里；本题 base 已包含 `2b061b68`、`3ac9396e` 的修复。

## 4. 问题清单

| 编号 | 严重度 | 内容 | 证据层次 |
| --- | --- | --- | --- |
| T2b | S1 | 默认值和显式 1 没有断言；退化候选 D（`'1'`/`'L'` 一律写 WhiteIsZero 并反相像素）得 1 | 当前真实评分 + 私有对照 |
| T2（第 4 步） | S1 | libtiff 写出路径没有覆盖；C3（gold 漏掉 `encoderconfig` 提升的版本）得 1，但压缩保存会崩溃 | 当前真实评分 + 私有对照 |
| P4 | 登记 | 题面没写像素语义，但公开依据充分；只改标签得 0 属于正确拒绝，不交用户 | 静态分析 + 当前真实评分 |
| T5 | 无害 | 2 个死键：pytest 8.3.4 不接受 `pytest.warns(None)` | 当前与历史评分 |
| T3、X1、G1 | 登记 | 见第 3 节 | 静态分析 |

## 5. 修订方案：R-c1 + R-c2，同一轮完成（预授权模板）

- **补丁草案**：在 `analysis_before_history.md` 附录 B。
  - R-c1：新增测试 `test_photometric_blackiszero_kept`，产生 4 个键：`[1-default]`、`[L-default]`、`[1-explicit1]`、`[L-explicit1]`。
  - R-c2：新增测试 `test_photometric_compressed`，产生 2 个键：`[1-group4]`、`[L-tiff_lzw]`。
  - 期望映射按现有键格式加 6 个 PASSED 键，共 68 个键；死键不动。
- **验收预期**：

| 候选 | 目标键 | R-c1 键 | R-c2 键 | reward |
| --- | --- | --- | --- | --- |
| gold | PASSED | PASSED | PASSED（两种压缩的私有预核已通过） | **1** |
| C1（替代正对照） | PASSED | PASSED | PASSED（静态预期） | **1** |
| noop | FAILED | PASSED | FAILED | **0** |
| D | PASSED | FAILED | PASSED | **0** |
| C3 | PASSED | PASSED | FAILED | **0** |
| C2（只改标签，按 P4 判为错误解） | FAILED | PASSED | FAILED | **0** |

- **修订后受保护的要求**：两种模式下保留 0（未压缩和压缩都覆盖）；像素往返不变；不指定时默认写 1，显式指定 1 时写 1。
- **还需要**：保存新版本、父版本和触发这次修订的反例（D、C3），并由 Codex 复核。
- **可选，不作前置条件**：R-a（删除两个死键及其测试）；R-f（在题面补一句像素往返的说明）。

## 6. 复核关注点与下一步

- 请独立复核专门核两点：
  1. P4 的判断：只改标签是否有公开依据；
  2. 第 4 步把压缩路径判为"非罕见路径"。
- **唯一优先的下一步**：按附录 B 实施 R-c1 + R-c2，用正式评分跑 gold、noop、C1、D、C3、C2 六个验收。

## 7. 进探针还差什么

按派发说明，我没有读本批 README，所以下表是按 v1 §2 和 §5 列的；协调者可以再对照 README §3 逐条核对。

| 项目 | 状态 | 谁来补 |
| --- | --- | --- |
| 评分条件（新镜像 noop 为 0、gold 为 1） | 原版已满足；修订后要重新验证 | 协调者 |
| 解题侧开发条件（导入、复现、公开测试、libtiff） | 已满足（09-29 devcheck） | — |
| 两个 S1 的修订、验收与 Codex 复核 | 未满足 | 协调者实施，Codex 复核 |
| 修订版本登记（隐藏测试树与期望映射的 sha、父版本） | 未满足 | 协调者 |
| 独立复核（`reviewer_initial.md`、`review.md`） | 未满足 | 复核者 |
| 如果在修订前就进探针：预登记事后审计（默认值与显式 1；压缩保存） | 未满足 | 协调者或探针分析方 |
| 公开命令修正（`public_tiff_tests_v2`） | 可选 | 协调者 |
| 模型实际收到的消息、经 adapter 的链路 | 未验证（通用问题） | A 线 |
