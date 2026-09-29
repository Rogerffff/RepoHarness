# pillow `2b061b68`：R-f 题面修订草稿（P2）

2026-09-29，修订执行者（单题闭环试行）。**状态：草稿，未试跑（评分材料不变），待 Codex 复核**。题面修订类（`statement_text_replace`，`rh2/src/repoharness2/envpack/ingest_r2e_subset.py:30-33,243-246,547-570`）本身也还在等 Codex 复核；正式修订单、pins 由协调者落，本文不写。草案文件见同目录 `revision_draft.json`。

路径约定：`PUB/` = `runs/r2e_static_prep_20260924/v3/public/pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8/`，`W/` = `PUB/worktree/`（解题者看到的 `/testbed`），`R1/` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/`，`CX1/` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_actor_review_20260925/`；其余路径相对仓库根。

## 1. 结论

- **模板**：R-f。第 1 类（删改对 base 与公开行为的错误陈述，都有实跑证据）为主，第 3 类（补解题必需、有公开依据的说明）补 4 条 API 约定。隐藏测试、期望映射（55 键：53 PASSED、2 FAILED）都不变。
- **为什么是 P2 而不是 P5**：原题面同时写了 "restrict the supported image formats"（`PUB/user_prompt.txt:7`）和 "Opening an image with the specified formats should work without issues"（`:24`，配 `:14` 的 PNG + `['JPEG']`）。回退读法唯一的依据就是 `:24` 这句，而同一题面的其它主张已证实是错的（§2）。统一标准 v1 §11 已把本题列为"删改与目标测试矛盾的错误陈述、隐藏测试不变"。Codex 首批复核 R3 提醒严格限制读法要版本化（`CX1/README.md:47-53`）：修订后本题只能作"标明版本的自建题"（v1 §5 R-f 验收），不冒充原 benchmark。
- **R-f 做不到的**：它不能消除本题另外两处已有候选证据的 S1（P2 快照回归、P3 `show()` 警告漏测，§6）。所以 **R-f 定稿后本题仍不满足"可以进探针"第 3 条**。v1 §11 把本题列为"R-f 后为训练候选"，与 v1 §4 第 4 步和 Codex 首批复核（`CX1/README.md:66`："修题面……消除不了 P2/P3 漏测"）不一致，需要协调者决定（§6）。

## 2. 逐条修改与依据

| # | 原文（摘要） | 改为 | 类别 | 依据 / 证据 |
| --- | --- | --- | --- | --- |
| 1 | 标题 "TypeError When Handling Warnings After Adding `formats` Parameter to `Image.open`" | "`Image.open` Has No `formats` Parameter to Restrict the Image Formats It Tries" | 第 1 类 | 见 #2、#4：base 没有 `formats`，保存与 `show()` 不抛该 TypeError |
| 2 | 描述："After introducing the `formats` parameter … handling warnings … leads to a `TypeError` … save … deprecation warnings …" | "`Image.open` has no option to restrict which image formats it tries when identifying a file. A `formats` parameter should be added to `Image.open` for this purpose." | 第 1 类 | base 签名 `def open(fp, mode="r")`（`W/src/PIL/Image.py:2839`）；agent 身份实跑 `OPEN_SIGNATURE_HAS_FORMATS False`（`runs/r2e_env_repair_20260924/p4/dev_probe/pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8/agent_probe.log:122`）。"限制格式"这一意图沿用原题面 `:7` |
| 3 | 示例里 `image.save('output.jpg')` 与 `image.show()` 两段 | 删除（只留原有的 `Image.open('hopper.png', formats=['JPEG'])`） | 第 1 类 | base 上保存与无参 `show()` 都正常且无警告：`SAVE_JPEG=ok … warnings=[]`、`SHOW_NOARGS=ok … warnings=[]`、`REPRO_OBSERVED=0`（同一 `agent_probe.log:125-129`）；`show()` 在有查看器时还会拉起外部进程（公开读者 `R1/results/pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8/public_read.md` §3.3） |
| 4a | Expected 第 1 条 "Opening an image with the specified formats should work without issues." | 删除；改为："`formats` is a list or tuple of format names (for example `"JPEG"` or `"PNG"`); only the listed formats are tried when identifying the file." | 第 1 类删错句 + 第 3 类补约定 | 删：与 `:7` 的 "restrict" 矛盾，也与目标断言相反。补："只试列出的格式"来自原题面 `:7`；"list 或 tuple"来自 Pillow 该参数发布后的公开 API 文档（同仓后续版本公开工作树 `runs/r2e_static_prep_20260924/v3/public/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/worktree/src/PIL/Image.py:2938-2940`）；格式名是注册 ID，`register_open` 统一转大写（`W/src/PIL/Image.py:3048`），`'JPEG'` 原题面已有 |
| 4b | （新增）无法识别时的行为 | "If none of the listed formats can open the file, `Image.open` fails as it does for any file it cannot identify, by raising `PIL.UnidentifiedImageError`. In the example, `hopper.png` is a PNG file, so opening it with `formats=['JPEG']` raises `PIL.UnidentifiedImageError`." | 第 3 类 | base 文档 `W/src/PIL/Image.py:2856-2857`（无法识别抛 `PIL.UnidentifiedImageError`）。示例调用原本就在公开题面，只改正它的预期结果；gold 下原例正是抛这个异常（`runs/r2e_actor_20260925/devcheck/pillow__2b061b68dbbf4fb590ab532b6fdffea8/private_gold/private_control.json` 的 `mcve_statement`） |
| 4c | Expected 第 2、3 条（保存"妥善处理警告"、`show()` 是弃用方法应告警） | 删除；新增 "`formats=None` (the default) tries all supported formats, as `Image.open` does today." | 第 1 类删错句 + 第 3 类 | 删：无参 `show()` 未弃用，`W/docs/deprecations.rst:15-20` 只弃用 `command` 参数，公开 `W/Tests/test_image.py:763-773` 断言无参 `show()` 不告警；实跑见 #3。补：`None` 表示全部格式——上述公开 API 文档 `:2940`；"as today"——base `_open_core` 遍历全部 `ID`、失败后 `init()` 再试（`W/src/PIL/Image.py:2893-2920`） |
| 4d | （新增）类型约定 | "A `formats` value that is not `None`, a list or a tuple raises `TypeError`." | 第 3 类 | 公开 API 文档 `…/pillow__2d01f7d0…/worktree/src/PIL/Image.py:2949`。解题必需：不写这句，显式抛 `ValueError`、或把单个字符串包成列表的实现会被目标键拒绝（复核 `R1/results/pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8/review.md` §2.2） |
| 4e | Actual："Saving the image raises … `TypeError: exceptions must be derived from Warning, not <class 'NoneType'>`"；"`show()` … the same `TypeError`" | "`Image.open` does not accept a `formats` argument, so the example fails before any format is tried: `TypeError: open() got an unexpected keyword argument 'formats'`" | 第 1、2 类 | 原例在 base 上以真实 CC、agent 身份实跑：`runs/r2e_actor_20260925/devcheck/pillow__2b061b68dbbf4fb590ab532b6fdffea8/orig/captures/mcve_statement.out:3`；noop 评分日志同一报错 `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-p_90eb28b3.eval.log:40`。原 TypeError 来自 pytest 8.3.4 拒绝 `pytest.warns(None)`，只出现在两个期望 FAILED 的键里（同一日志 `:85,127,185-186`） |

四条 `old` 在来源题面里各出现恰好一次，已在本机按 `_apply_edits` 的规则重放核对：`sha256_before = sha256:8c7172a7…89ec`（与 `PUB/public_bundle.json` 的 `problem_statement_sha256` 相同），`sha256_after = sha256:7aa06898…9c95`（全值见 `revision_draft.json`）。

## 3. 修订后题面全文（`[ISSUE]` 段）

```
[ISSUE]
**Title:** `Image.open` Has No `formats` Parameter to Restrict the Image Formats It Tries

**Description:**
`Image.open` has no option to restrict which image formats it tries when identifying a file. A `formats` parameter should be added to `Image.open` for this purpose.

**Example Code:**
    from PIL import Image

    # Open an image with restricted formats
    image = Image.open('hopper.png', formats=['JPEG'])

**Expected Behavior:**
- `formats` is a list or tuple of format names (for example `"JPEG"` or `"PNG"`); only the listed formats are tried when identifying the file.
- If none of the listed formats can open the file, `Image.open` fails as it does for any file it cannot identify, by raising `PIL.UnidentifiedImageError`. In the example, `hopper.png` is a PNG file, so opening it with `formats=['JPEG']` raises `PIL.UnidentifiedImageError`.
- `formats=None` (the default) tries all supported formats, as `Image.open` does today.
- A `formats` value that is not `None`, a list or a tuple raises `TypeError`.

**Actual Behavior:**
- `Image.open` does not accept a `formats` argument, so the example fails before any format is tried:
    TypeError: open() got an unexpected keyword argument 'formats'
[/ISSUE]
```

（上面为便于阅读把代码围栏换成了缩进；实际文本以 `revision_draft.json` 的 edits 重放结果为准，保留原题面的 python 代码围栏与报错代码块。）

## 4. 护栏逐行核对（v1 §5 R-f 边界）

- **没有复制隐藏测试细节**：不写目标测试里的 `formats=123`、`("JPEG",)`、`Tests/images/hopper.jpg`，也不写任何断言文案。唯一与目标断言同形的是 `hopper.png` 配 `['JPEG']`，这个调用原题面就有，本次只改正它的预期结果。
- **没有答案内容**：不提 `ID`、`_open_core`、`preinit` / `init` 等实现位置，不给代码。
- **没有无依据的新要求**：四条 Expected 都能指到原题面、base 文档或 Pillow 该参数的公开 API 文档（§2）。
- **按复核的两条护栏**（`R1/results/pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8/review.md` §2.4）：不写大小写不敏感、不写按需 `init()`（上游后来才加，本题 gold 不满足）；示例只用预载格式。
- **不因 gold 做不到而收窄题面**（`CX1/semantics_b/review.md:91`）：gold 对调用时尚未注册的格式名抛 `KeyError`——小写名，或新进程里 `preinit()` 未载入的 `'TIFF'`（`OPEN[i]` 查找的 `KeyError` 不在 `_open_core` 捕获的异常元组里，`W/src/PIL/Image.py:2894-2913`）。题面没有为此排除 TIFF 或写"只支持预载格式"，而是把它登记为参考实现限度（G1，隐藏测试不覆盖，静态推断，未实跑）。

## 5. 验收计划（v1 §5 R-f 验收）

| 项 | 做法 | 预期 | 状态 |
| --- | --- | --- | --- |
| 新公开读者 | 一个没看过隐藏测试与 gold 的新会话只读修订后题面与公开包，写需求表 | 推出"只试列出格式；不匹配抛 `UnidentifiedImageError`；`None` 全部；list/tuple；其它类型 `TypeError`"，与目标断言一致；不需要猜 `formats=123` 之类细节 | 待协调者安排 |
| 逐行核对 | 按 §2、§4 对照 | 无隐藏细节、无答案 | 本文已做，待 Codex 复核 |
| 评分材料不变 | 不改隐藏测试与期望 | 现有 current 证据继续有效：gold 55/55（`runs/r2e_rf_20260923/remote/ledger_r2e_all_gold.jsonl:37`、`runs/r2e_env_repair_20260924/_rerun2/ledger_gold.jsonl:37`），noop 54/55 | 不需试跑 |
| 触发反例 | P1：不匹配时回退到全部格式（`runs/r2e_actor_20260925/grader_cands/pillow_2b06_P1_fallback_to_all_formats.patch`） | 现材料上已实测 0（54/55，`TestImage.test_open_formats` 报 DID NOT RAISE；`R1/grader_candidates.md:29`）。修订前它"遵循冲突示例"（Codex R3），修订后它违反新题面第 1、2 条，0 分有公开依据 | 已有证据 |
| 版本 | 新题面摘要 `sha256:7aa06898…9c95`，父版本 `sha256:8c7172a7…89ec` | 走 `statement_text_replace` 修订单 | 协调者落 |
| Codex 复核 | — | — | 待 |

## 6. R-f 之外仍未处理的 S1（需协调者决定，不在本包）

按 v1 §4 第 4 步（已有候选得 1、却破坏有文档或常用的公开行为 → S1），本题还有两处，R-f 都消除不了：

1. **P2：`formats is None` 时取 `list(ID)` 快照**（`runs/r2e_actor_20260925/grader_cands/pillow_2b06_P2_snapshot_list_id.patch`）得 1（55/55，`R1/grader_candidates.md:30`），但新进程里默认 `Image.open` 任何图片都抛 `UnidentifiedImageError`（`runs/r2e_actor_20260925/grader/pillow_fresh/P2.json`；gold 对照 `pillow_fresh/gold.json` 为 PNG、TIFF 正常）。评分测不到，因为目标测试里第一次默认打开发生在 `init()` 之后；解题者本地跑 pytest 也测不到，因为 `Tests/conftest.py` 的报告头会先调 `features.pilinfo()` 载入全部插件（复核 `R1/results/pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8/review.md` §2.1）。这破坏最常用的公开行为。**可行修法（R-c）**：隐藏测试加一个子进程用例，在新解释器里不带 `formats` 打开 `Tests/images/hopper.png` 与一个非预载格式（如 `Tests/images/hopper.tif`），断言能打开；依据是 base 旧行为（向后兼容）。gold 应过、P2 应败。
2. **P3：gold 再让无参 `show()` 发 `DeprecationWarning`**（`runs/r2e_actor_20260925/grader_cands/pillow_2b06_P3_gold_plus_show_warning.patch`）得 1（`R1/grader_candidates.md:31`），违反 `W/docs/deprecations.rst:15-20` 与公开 `W/Tests/test_image.py:763-773`。原因是两个期望 FAILED 的键在 `pytest.warns(None)` 处就失败（pytest 8.3.4），后面的断言不执行。R-f 去掉了题面对这种改动的诱导，但评分仍不保护。**可行修法（R-c 复用公开测试的意图，同时改两个键的期望状态）**：把这两处 `pytest.warns(None)` 换成与 pytest 8 兼容的记录写法（`warnings.catch_warnings(record=True)` 加 `simplefilter("always")`），两个键的期望由 FAILED 改为 PASSED。这也消除期望映射对 pytest 大版本的依赖（复核 `review.md` §2.3）。改期望状态要有独立的环境证据（v1 §5 R-a）：pytest 8.3.4 在构造 `WarningsChecker(None)` 时就抛 TypeError（noop 日志 `evallog_replay-r2e-rf-all-noop-p_90eb28b3.eval.log:73-85`）。

**建议**：R-f 与上面两处 R-c 合并成同一轮修订后再验收；否则本题 R-f 定稿后记为"只作问题定位"（能力比较须附 P2/P3 事后审计），不进训练候选。

## 7. 探针就绪差距（对照本批 README §3）

1. noop 0 / gold 1：现材料已满足（§5）；本机新派生镜像上的复验待协调者。
2. 真实解题身份的开发命令：首批 devcheck 已跑通（`R1/actor_devcheck.md:39`），新机器上待复验。
3. S1：P2 题面冲突由本 R-f 处理（待 Codex）；§6 两处 S1 未处理。**未满足**。
4. 公开包泄漏预检：题面修订后需重新生成公开包并跑 R2E rollout 预检。
5. 题卡：四项用途待修订定稿后更新。当前建议：`problem_localization=yes`；`capability_comparison=conditional`（R-f 经 Codex 复核并版本化，且附 P2/P3 事后审计）；`training_candidate=no`（§6 未处理）；`heldout_candidate=no`。
