# 历史对照：pillow__4bc6483564ae1a254911e98280b9a501f047a2e0

- 私有主审，2026-09-29 07:42 +08。本稿写于 `analysis_before_history.md`（前稿）封存之后。
- 读了 `runs/r2e_static_prep_20260924/v3/history/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/refs.json` 所列的全部 8 项。
- 没有读独立复核的 `reviewer_initial.md`。协调者转述的要点见 §3。
- 路径缩写：
  - `HIST/` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/`
  - `LIFE/` = `runs/r2e_lifecycle_20260929/`
  - `DEV/` = `LIFE/devcheck_rev/unrev/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/`
  - `INV/` = `LIFE/inv/pillow_4bc6/`
  - `PRIV/` = `runs/r2e_static_prep_20260924/v3/private/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/`
  - `wt/` = `runs/r2e_static_prep_20260924/v3/public/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/worktree/`

**历史范围**：09-24 的 R2E 环境审查（P4 包），只判"环境资格"。旧记录自己写明 `scope` 是"环境资格（不含题目质量 / 训练准入）"（`HIST/tasks/pillow__4bc64835…/screening_record.json` 的 `disposition`）。所以旧记录没有对测试强度下过结论。下表的"推翻"只针对旧记录在题目质量上可能被误读的地方，不是说旧记录在环境范围内判错了。

## 1. 旧主张逐条对照

| # | 旧主张（出处） | 判定 | 新的决定性证据 |
| --- | --- | --- | --- |
| 1 | 分类 `solver_condition`（venv 无 pip），处置 `environment_qualified`，"环境无缺口"（`findings.md:3, 13-14`） | **确认**（在新镜像上） | 解题身份下 `No module named pip`（`DEV/orig/captures/env.out`）；devcheck 13 项检查全真，含 R2E 预检三项（`DEV/devcheck.log`）；新机正式复验 noop 0 / gold 1（`LIFE/env_verify/ledger_l1_{noop,gold}.jsonl:11`） |
| 2 | 旧 issue：公开提示写 "`pip` … already point at it"，与无 pip 矛盾（`screening_record.json` 的 `issues[0]`，状态 open） | **过时（已解决）** | 当前公开提示改为 "There is no network access and `pip` may be unavailable"（`runs/r2e_static_prep_20260924/v3/public/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/public_bundle.json:15`） |
| 3 | R03 / E09：提示是 conda 措辞，正式链的解释器前缀默认 conda，会拒绝 R2E（`decisions.md` E09） | **过时** | 正式链已按 `.venv` 启动：`ACT_EXPECTED_PREFIX=/testbed/.venv`、`ACT_SYS_PREFIX=/testbed/.venv`（`DEV/orig/activation_check.json`）；提示已是 R2E 措辞 |
| 4 | R05：`python` 为 `/testbed/.venv/bin/python` 3.9.21；pytest 8.3.4；`.pth` 指向 `/testbed/src`；`Image.core` 是树内编译的 `.so`；gcc / make / git 可用 | **前四项确认；gcc / make 未核实** | `DEV/orig/captures/env_pil_import.out`：PIL 与 ImageOps 在 `/testbed/src/PIL/`，core 是 `/testbed/src/PIL/_imaging.cpython-39-x86_64-linux-gnu.so`，jpg / zlib / libtiff 均可用，packaging 24.2。本轮没有查编译器（本题不需要构建） |
| 5 | R07：agent 可写 `/testbed`；`.venv` 的 site-packages 在 chown 后也可写，属于反作弊面、另议 | **未核实** | 本轮没有查。这是平台面问题，不是本题特有 |
| 6 | R08：候选代码生效（导入 `/testbed/src/PIL`，gold 24/24） | **确认并加强** | 4 个构造候选在同一镜像上行为各不相同，且与补丁一致（`INV/pcheck_canon_{D1,A1,W1}.json`）；评分侧 `RH2_OBS_IMPORT_PATH=/testbed/src/PIL/__init__.py`（`INV/ledger_*.jsonl`） |
| 7 | R09：公开 `Tests/test_imageops.py` 24 passed；公开复现 `REPRO_OBSERVED=1` | **确认** | 解题身份、正式启动路径下：`pytest_imageops` 24 passed，`pytest_tiff_photometric` 2 passed，`repro_issue_example` 以 `OSError: not supported for this image mode` 退出 1（`DEV/orig/captures/*.out`） |
| 8 | R10 / R11：不需要网络，也不依赖外部服务 | **确认**（就本题需求而言） | 评分 `network=deny_all` 下全部正常；公开命令都不需要网络。正式链的出网面（隔离网络加 relay）本轮没有测，属于 A 线 |
| 9 | R12：内存峰值 509 MB / 4 GiB；评分准备约 24 s | **内存确认；耗时过时** | 新机内存峰值 510–513 MB；新机评分的可信准备约 82 s（`ledger_l1_*.jsonl:11` 的 `phases`），是机器差异，不是本题问题 |
| 10 | R13：noop、gold 同条件各 2 次一致 | **确认并扩展** | 新镜像再各 1 次，键级结果相同：noop 只有 `test_sanity` 不匹配；gold 24/24 |
| 11 | R14：每次评分都是 fresh 容器；镜像自带的 `__pycache__` 来自 base；工作区行数 2→2 | **确认** | 新账本 `omitted_cache_count` 为 7/7 不变；devcheck 结束后 `RH2_GIT_STATUS_LINES=2`（`DEV/orig/post_run_facts_root.txt`） |
| 12 | R15：与 M3 独立 runner 逐键对账一致 | **未重做** | 旧证据仍适用于旧镜像；新镜像没有独立 runner 对照 |
| 13 | R16：目标键 `test_sanity` 名称泛化，但 noop 原因行正是题面报错；gold 后无残留不符键 | **事实确认；不能再当成"目标键验证了修复"** | 该键对本题只做 `ImageOps.invert(hopper("1"))` 冒烟，不检查输出。退化候选 D1 实跑 1.0（24/24，`INV/ledger_D1.jsonl`），而它的输出等于输入（`INV/pcheck_canon_D1.json`，`AssertionError: b'\xa5'`）。新增 S1，见 card |
| 14 | R17：派生镜像不含修复；HEAD 无子提交；没有 refs、remote、reflog 或补丁残留 | **确认** | 正式链 `git_sanitize`：`REFS_REMAINING=0`、`REMOTES=0`、`REFLOG_ENTRIES=0`、`UNREACHABLE_OBJECTS=0`，HEAD 仍为 base；`RH2_PREFLIGHT_GIT_HISTORY=ok`（`DEV/orig/attempt.json`） |
| 15 | R06：期望 24 键全是 PASSED，没有非 PASSED 键 | **确认** | `PRIV/expected_output.json`（sha256 与评分面一致） |
| 16 | 建议"不需要配方或材料修订"（`findings.md:17`） | **在题目质量层面推翻；环境层面仍成立** | 需要一次测试层修订（R-c），因为 D1 与 W1 都实跑 1.0。环境与配方仍不需要改 |
| 17 | 配方 `r2e_derive_v1`（sha256 `0da821a1…`），镜像 `28c11ac2…`（`facts.json` 的 `identity`） | **过时（身份变化，结论不变）** | 新机是 `r2e_derive_v1+sysconfig_v1`（sha256 `e2e17bf1…`），镜像 `d6de4045…`；隐藏测试树仍是 `7e15b739…`；noop 与 gold 在键级与旧机一致 |
| 18 | P4 包总结："12 题环境层面都能支持解题与评分"（`packages/p4/README.md:7`） | **本题确认** | 同第 1 行 |
| 19 | 复现脚本按题面示例原样调用，记录 `INVERT=raised OSError`（`HIST/repros/pillow__4bc64835….py`） | **确认，并补一个旧稿没有看的事实** | 同一示例在 gold 下不报错，但原始值为 254、`tobytes()` 不等于全黑、`convert("L")` 的极值是 (255, 255)，按 1-bit 语义仍是全白（`DEV/private_control.json` 的 `results.repro_issue_example`）。定性见 §2 |

## 2. 与前稿相比，我改了哪些判断，为什么

1. **T2b：从"待实跑"变为"已确认"**。
   - D1（对 mode "1" 返回 `image.copy()`）正式评分 1.0，`keys_equal=True`，`included_paths=['src/PIL/ImageOps.py']`（`INV/ledger_D1.jsonl`）。
   - 日志第 27 行 `test_sanity` PASSED，24 passed（`INV/logs_D1/…a13fcfcb.eval.log`）。
   - 私有行为检查在脚本第 8 行失败，输出 `b'\xa5'` 等于输入。
   - 补丁已交付，目标测试已执行，结果完整，满足 v1 §4 对退化探测证据的要求。
2. **W1：从"与第 3 步同根、预计得 1"改为"第 4 步命中，S1"**。
   - W1 正式评分 1.0，私有检查在第 9 行失败：调用者的输入图被原地改掉（`INV/pcheck_canon_W1.json`）。
   - 依据是有文档、常用的公开行为："操作返回新图，原地修改要特别注明"：
     - `Image.thumbnail` 的 docstring 专门注明它会原地修改（`wt/src/PIL/Image.py:2418-2421`）；
     - `ImageOps.exif_transpose` 写明即使不变也 "return a copy of the image"（`wt/src/PIL/ImageOps.py:575-576`）；
     - `ImageOps.invert` 的唯一内部调用方（TIFF 保存）直接把用户的图传进去（`TiffImagePlugin.py:1666-1675`）。
   - 影响不是边缘路径：凡是反相后还继续用原图的调用都会受影响。
   - 它与 T2 同根（测试不检查 `invert` 的输出与副作用），用同一个 R-c 修。
   - 如果复核认为这条依据不足，S1 结论仍由 D1 单独成立，只需删掉 R-c 里"输入不变"那一行。
3. **gold 对题面原例的输出：从静态推断变为实测，定性维持"登记（P4 / G1，S2）"，不列为第 4 步 S1**。
   - 事实：gold 把原例的每个像素从 1 变成 254；所有按 1-bit 解读的视图都显示仍为全白。
   - 不列为 S1 的理由：
     - 只有原始存储值不规范（1，不是 255）时，两种读法才会分歧，而这两种读法在公开材料里都有依据：
       - "按存储字节取反 `255 - v`"：与 L 模式的 invert 一致；`ImageChops.invert` 文档写 `MAX - image`，对 "1" 也得到 254；
       - "按 1-bit 值取反"：文档写 1-bit 像素取值为 0–1；打包、转 L、逻辑运算都把非零当白。
     - 题面的期望行为只强调 "without raising an error"，没有给出输出像素。
     - 断言任何一种读法都等于在任务目标上二选一（P5 范畴）；断言后一种还会判上游 gold 为 0。
   - 现行测试与 R-c 草案都不对非规范值断言，两类实现都得 1（gold 与 A1 均为 1.0），不产生误拒或漏判。
   - 处理：登记，并在"待用户决定"里给出可选项，建议维持现状。
4. **解题侧条件：从"待 devcheck"变为"已验"**。
   - 导入路径、解释器、`.venv` 激活、R2E 预检三项、公开命令 8/8 都符合预期（`DEV/`）。
   - 最小公开验证是亚秒级：`pytest_imageops` 0.54 s；整次 devcheck 求解段 19.3 s。
5. **处置状态：从 `needs_review` 改为 `needs_repair`**。材料缺陷已有执行证据，修法在预授权模板（R-c）内，等待实施与验收。
6. **能力比较的条件收窄**。环境与开发条件已验，剩下的条件只有：预登记事后审计（对得 1 的补丁跑公开命令 `check_mode1_invert_canonical`，原始 reward 与审计结果分列），或者改用 R-c 后版本。
7. **T1（误拒合理解）：从静态判断变为执行证据**。
   - A1（按 1-bit 语义归一）与 A2（放宽 `_lut`）都是 1.0。
   - 公开读者给出的两条主要路线都不会被现行测试误拒。

## 3. 与独立复核初判的关系（协调者转述，未读原文）

- 复核同样判 S1（T2a），并预测 D1 得 1。这一点现在已坐实，没有分歧。
- 复核指出：按 base 的 C 源码推断，gold 对题面原例其实没有反相。本稿用私有对照的实测输出确认了这一事实（§1 第 19 行）。
- 在定性上，本稿判为登记（P4 / G1，S2），理由见 §2 第 3 条。它不改变处置与修订内容，只影响问题登记的归类。若复核坚持判第 4 步 S1，就需要用户决定是否把"非规范值按 1-bit 语义反相"定为要求（card"待用户决定"一项）。
