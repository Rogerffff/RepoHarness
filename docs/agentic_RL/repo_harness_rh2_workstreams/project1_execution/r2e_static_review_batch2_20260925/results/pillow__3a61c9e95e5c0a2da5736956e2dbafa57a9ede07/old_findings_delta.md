# pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07：旧结论核对

- 本文写于 `analysis_before_history.md` 之后，前稿不改。2026-09-25，R2E 私有主审。
- **读了哪些历史材料**：`runs/r2e_static_prep_20260924/v3/history/<iid>/refs.json` 列出的 8 份。它们是 `r2e_env_repair_20260924/` 下的 `tasks/<iid>/{findings.md, screening_record.json, facts.json}`、`known_issues.json`、`decisions.md`、`results_20260924.md`、`repros/<iid>.py` 和 `packages/p4/README.md`。
- **为核对旧主张另开的原始证据**：
  - `runs/r2e_env_repair_20260924/p4/dev_probe/<iid>/agent_probe.log`
  - `runs/r2e_env_repair_20260924/p4/targeted_public_tests/<iid>/agent_probe.log`
  - `runs/r2e_env_repair_20260924/p4/image_readout/<iid>.txt`
  - 当前摄入面 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest/public_bundles_v0.jsonl` 第 39 行
- **刻意没读的**：`runs/r2e_rf_20260923/reconcile_all/`（汇总文件）、`dev_probe.json`（工具派生的摘要）、首批审查目录和 Codex 复核目录。
- **历史的范围**：这是 09-24 P4 的环境资格审查，记录里的 `disposition.scope` 写明"不含题目质量 / 训练准入"，没有做需求到测试的映射。

## 1. 逐条核对

| # | 旧主张（出处） | 判定 | 新的决定性证据 |
| --- | --- | --- | --- |
| H1 | 分类 `solver_condition`，处置 `environment_qualified`（`screening_record` 的 disposition；findings.md） | 确认（限环境层） | 评分侧：current 4 行都是 noop 0、gold 1。解题侧：DEV 在真实 Claude Code 链上以 agent 身份运行，env 和 pr1–pr5 全部 rc 0。环境资格和本审的题目质量结论可以并存，不冲突 |
| H2 | R01 镜像身份：容器镜像等于派生镜像 `0fb6caf2…`，HEAD 等于 base | 确认；但对当前 actor 镜像不完整 | 4 行账本的 `image_id_actual` 都是 `0fb6caf2…`。DEV `orig/prelaunch.json` 用的镜像却是 `305f39cc…`（检查项 `image_is_overlay_derived_id: true`），HEAD 相同。`305f39cc` 上的 noop/gold 评分不在任何给到的证据里。另有一个计数小差异：R01 说复核 21 项，facts.json 的 `checks_total` 是 20；不影响结论 |
| H3 | R02/R13/R16：noop 0 只因 `TestImage.test_remap_palette` 失配，gold 71/71，两次一致，目标键与题面一致 | 确认，并补上失败位置 | 两份 noop 日志都在 `r2e_tests/test_1.py:614` 的字节比较处失败（`At index 3 diff: b'\x03' != b'\x04'`），`:613` 的索引比较通过。失败的正是题面描述的症状，不是收集或导入错误 |
| H4 | R03：题面示例可以运行，公开复现在 base 上成立（REPRO_OBSERVED=1） | 确认 | DEV pr1（真实 Claude Code、agent 身份）输出 `same_palette_bytes: False`、`palette_len: 1024 768`。另外还观察到 C 层问题：`rgba_render_equal: False` |
| H5 | R04：hygiene 文件与 gold 触碰的路径不相交；解题不必改测试辅助 | 确认 | 隐藏 `helper.py` 与公开 `Tests/helper.py` 的 diff 为空；gold 只改 `src/PIL/Image.py`。补充一点：根目录 `conftest.py` 以插件方式加载仓库里的 `Tests.helper`，评分时不重置（R2E 通用情况） |
| H6 | R05：解释器与 pytest 8.3.4 正常，没有 pip，`.pth` 路径项指向 `/testbed/src`，gcc、make、git 都在 | 确认 | 原始 `agent_probe.log` 里有 `WHICH_gcc=/usr/bin/gcc`、`WHICH_make=/usr/bin/make`、`PIP_VERSION=/testbed/.venv/bin/python: No module named pip`；DEV `env.out` 与之一致。补充：install.sh 用的是 `uv pip install -e . --no-build-isolation`（就地可编辑安装），而评分时 `RH2_INSTALL_SKIPPED=1`，不会重建 C 扩展。由此推断：只改 C 源码的候选在评分时不会生效。本题不需要改 C |
| H7 | R06：期望 71 键全是 PASSED；1 个 SKIPPED 不成键 | 确认 | 见 `expected_output.json`；各次日志都有 `SKIPPED [1] r2e_tests/test_1.py:165: jpg_2000 not available`。被跳过的是 `test_pathlib`：它执行到 `.jp2` 时才跳过，之前的打开和保存已经执行了 |
| H8 | R07：site-packages 和 `.venv/bin` 位于 `/testbed` 内，agent 可写；"反作弊面另议" | 确认；仍开放，属 R2E 通用问题 | 原始日志 `WRITE_SITE=ok`、`WRITE_VENV_BIN=ok`。正式链的 DEV 没有单独探测 `.venv` 的写权限；评分侧会不会投影被 git 忽略的 `.venv` 改动，也没核实 |
| H9 | R09：公开 `Tests/test_image.py` 71 passed / 1 skipped | 确认，并补上了我前稿的一个缺口 | `targeted_public_tests/<iid>/agent_probe.log`：以 agent 身份在 `/testbed` 运行，`T1_RC=0`，`71 passed, 1 skipped in 0.29s`（探针条件，镜像 `0fb6caf2`）。这份文件和隐藏文件只差 RGBA 块，所以解题者在本地就能看到 70 个键的等价结果 |
| H10 | R10/R11：无网络、无外部服务 | 确认，证据更强 | DEV 走的是正式链：`DNS_EXTERNAL=DENIED`，4 个 forbidden 目标和 upstream 直连都是 DENIED，只有 relay 为 CONNECTED。历史用的是 `--network none`，E02 说明它对 relay 可达性不下结论 |
| H11 | R12：内存峰值 510 MB，测试约 1 秒 | 确认 | 账本 `resource.mem_peak_mb` 为 510.0–510.1 |
| H12 | R14/R17：镜像自带的 pyc 由 base 源码编译 | 确认 | `image_readout` 里 `Image.cpython-39.pyc` 的 `pyc_src_size=125678`，正好等于公开工作树 base `Image.py` 的字节数；如果是 gold 版源码，会多 329 字节 |
| H13 | R17：看不到未来修复（fix_present=no；HEAD 无子提交；refs、reflog、remote 都为空；install.sh 是通用脚本、不含修复；run_tests.sh 只暴露目录名和命令） | 题内确认；题间没有覆盖 | `image_readout` 里有 install.sh 全文（sha `c272ac91…`），只做 uv venv 和 pip install。DEV `attempt.json` 的 git 净化计数都为 0，预检 ok。**题间**：本题 gold 13/13 行逐字出现在 `pillow__f9d3ee0f…` 的公开初态里，测试块也在。历史对 f9d3ee0f 和 a682ceaf 都记为 environment_qualified，没有记录这层包含关系 |
| H14 | issue：venv 没有 pip，而公开提示写着 "`pip` already points at it"（另有 conda 措辞，见 E09）；status open | **过时**：没有 pip 的事实仍成立，但与提示的矛盾已经消除 | 当前 `public_bundles_v0.jsonl:39`（sha `af9aa35e…`，和本题公开包一致）写的是 "`pip` may be unavailable"，不再提 conda。旧版有归档目录 `s2_r2e/ingest_history/material_v3_conda_hints_20260925/`，本审只见其名、没有打开。DEV 再次确认没有 pip。本题不需要装包，所以这一条对解题没有影响 |
| H15 | known_issues 的 `solver_hints:conda_wording_and_activation_prefix` 族（E09，open） | 对本题过时 | DEV `activation_check.json` 显示 `ACT_EXPECTED_PREFIX=/testbed/.venv`、`RH2_ACTIVATION_PROBE_OK=1`，R2E 预检三项都 ok。环境卡 §2 把这条标为"待 A 线审查" |
| H16 | facts.json 的 `public_hints_mention_conda: true` | 过时 | 同 H14 |
| H17 | R15：与独立 runner 对账一致（5 次参考 reward） | 部分核实 | M3 的原始日志 a1、a2 都是 71 passed / 1 skipped，和 RH2 的 gold 结果一致；`reconcile.json` 是汇总文件，没读 |
| H18 | findings："环境无缺口；不需要配方或材料修订" | 确认（限环境层） | 同上。本审新发现的是题目质量层的问题（测试偏宽、未测回归、题间包含），不属于环境缺口。是否补断言属于测试标准修订，需要用户决定 |
| H19 | known_issues 的 `prompt_quality_candidates` 族没有列本题 | 确认 | 题面示例就是目标断言本身。只有两处措辞不准（"Fails"、"byte arrangement"），不影响定位 |
| H20 | 复现脚本写于读隐藏测试和 gold 之前（E06） | 未核实（这是流程声明） | 不影响结论 |

## 2. 历史没有覆盖、本审新增的发现

1. **测试偏宽**：隐藏测试只检查恒等映射、Python 层字节和像素索引。W1、W2、W3 预计都能得 1。这是静态推断，待正式评分确认。
2. **未测回归**：GIF optimize 会显式传入 RGB `source_palette`，这条路径没有测试（对应 W1）。
3. **题间包含**：
   - f9d3ee0f 包含本题 gold 13/13 行和测试块。
   - a682ceaf 包含 10/13 行和测试块；机械比对只命中 77%，低于 80% 阈值，所以漏报了。
   - 反方向：2b061b68、2d01f7d0、4bc64835 的修复出现在本题初态里；其中 4bc64835 已凭公开包核对。
4. **gold 的低优先边缘情况**：GIF `palette=` 分支里，Python 调色板的 mode 与字节格式对不上。这是静态推断。
5. **镜像不一致**：当前 actor 用的镜像 `305f39cc` 和评分证据所用的 `0fb6caf2` 不是同一张。

## 3. 我的判断有没有改变

- **处置不变**：仍是静态候选，用途 development_diagnostic，state 为 needs_review。理由有两条：静态候选还待 actor 验证；测试偏宽还待 CPU 反例确认。历史给的 environment_qualified 只覆盖环境层，与此不矛盾。
- **前稿 §7/§9 的三个缺口已由历史原始证据补上**：
  - install.sh 已读，是通用安装脚本，不含修复。
  - 编译器存在。
  - 整份公开 `Tests/test_image.py` 已以 agent 身份跑通（探针条件）。
- **新增一条推断**：评分时跳过安装，改 C 源码不会被重新编译。本题不需要改 C。
- **历史给出的旧 issue 过时**："提示与无 pip 矛盾"已随 v3 提示消除。
- **下一步不变**：用正式评分实跑 W1、W2，C1 作对照，W3 可选；同一批里在 `305f39cc` 上补跑 noop 和 gold 各一次。
