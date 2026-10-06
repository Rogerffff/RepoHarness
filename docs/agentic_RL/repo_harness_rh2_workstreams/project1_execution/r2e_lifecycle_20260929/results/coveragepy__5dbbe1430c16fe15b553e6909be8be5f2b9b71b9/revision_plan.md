# coveragepy `5dbbe143` 修订方案：P5 决定包（附已试跑的模板内 R-c）

2026-09-29 · 修订执行者（Claude，单题闭环试行，统一标准 v1）。

**状态：需要用户做一轮决定（P5）。**
- 选项 A 的 R-f 题面补句草稿和配套的 R-c 已经备好。
- R-c 已在新派生镜像上试跑，结果符合预期。
- R-f 按任务要求不试跑评分，因为评分材料不因题面修订而改变。

路径约定（均相对仓库根）：
- `PUB` = `runs/r2e_static_prep_20260924/v3/public/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9/`，其中 `PUB/worktree/` 就是解题者的 `/testbed`；
- `PRIV` = 同题的 `v3/private/` 目录；
- `CANDS` = `runs/r2e_actor_20260925/grader_cands/`；
- `trials/` = 本目录下的试跑结果。

## 0. 结论

- **找到了支持"按 slug 去重"的公开依据**：
  - 文档把 slug 定义为警告的名字；
  - 现有的抑制机制按 slug 工作；
  - 题面示例用的是同一 slug、不同消息。
- **但"按消息去重"同样有公开依据**：
  - 题面 "duplicate warnings" 的字面意思；
  - 仓库里已有"同一 slug 的警告按文件名去重"的先例；
  - 标准库 `warnings` 的 "once" 语义。
- **所以这是任务目标选择，需要用户决定**：按 v1 §3 P5 和 §5 R-f 的边界，不能用 R-f 自行定案，也不能把两种输出用"或"并起来。
- **建议选 A**：采用按 slug 的读法。它与来源提交的意图、gold 和现有隐藏测试一致。做法是 R-f 补一句题面，再用 R-c 补上"不同 slug 各显示一次"的断言。
- **CE4 的漏测与这一选择无关**：只要不选 C（不修订、只作问题定位），CE4（第一次 once 之后所有 once 警告都不显示）都需要这条 R-c 才能关住。Codex 首批复核也指出过："仅修题面不会补上'不同警告首次都应显示'的保护"（`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_actor_review_20260925/README.md:64`）。
- **试跑结果**：
  - 新派生镜像 `sha256:828436b9…`，配方 `r2e_derive_v1+sysconfig_v1`。当前材料下 noop 为 mismatch、gold 为 match，环境正常。
  - 加上 R-c 之后：gold 得 1、CE3 得 1、noop 得 0；CE4 由 1 变为 0；CE1 仍是 0，只在原目标键上失败，这正是 P5 的争议点。

## 1. 公开依据核对

### 1.1 支持按 slug 去重

1. `PUB/worktree/coverage/control.py:337-343`：
   - `_warn` 的 docstring 写 "For warning suppression, use `slug` as the shorthand."；
   - 紧接着的 `if slug in self.config.disable_warnings: return` 说明抑制以 slug 为键。
   - 限度：这里说的是 `disable_warnings` 这一种抑制，不是 once。base 里还没有 once。
2. `PUB/worktree/doc/config.rst:156-158`：`disable_warnings` 条目说 slug 是 "the name of the warning"。
   - 在本仓的术语里，"一条警告"是以 slug 命名的；
   - 所以题面的 "displayed only once each" 可以读作"每个（以 slug 命名的）警告只显示一次"。
3. `PUB/worktree/doc/cmd.rst:134-187`：警告清单里的每一条，都是"含可变部分 XXX 的消息模板 + (slug)"，例如 `Module XXX was never imported (module-not-imported)`。第 182 行写 "Individual warnings can be disabled with the disable_warnings ..."。
   - 可见同一条警告可以带不同的消息文本。
4. `PUB/user_prompt.txt:13-14`：示例刻意用同一个 slug `"bot"` 和两条不同的消息来演示 once。
   - 如果按消息去重，示例的输出与"只接受参数、完全不去重"一模一样，once 在示例里就看不出任何效果。
   - 限度：题面没有写出示例的期望输出。

### 1.2 支持按消息去重

1. `PUB/user_prompt.txt:18`："displayed only once each, preventing duplicate warnings from appearing"。示例里两条消息不同，按日常字义不算 "duplicate"。
2. `PUB/worktree/coverage/inorout.py:345-360`：`warn_already_imported_files` 对同一个 slug `already-imported` 按文件名去重，每个文件各报一次。
   - 也就是说，仓库里现成的"不重复报同一警告"，是按具体对象（也就是按消息）去重的。
3. `PUB/worktree/tests/test_api.py:510-516`：`test_warnings` 期望同一 slug `module-not-imported` 的两条不同消息都显示。
   - 这是非 once 路径，但说明在本仓里，同 slug、不同消息的两条被当作两条警告。
4. 标准库 `warnings` 的 "once" 动作按消息文本（及类别）只显示一次。仓库的 `PUB/worktree/tests/conftest.py:26` 正在使用 `warnings.simplefilter("once", DeprecationWarning)`，而新参数也叫 `once`。

### 1.3 判断

- 按 slug 一方的依据更成体系：文档术语、API 的抑制机制、示例结构。但这些依据都没有直接说明 once 怎么判断"重复"，因为 base 里还没有 once。
- 按消息一方的依据，是题面措辞本身和仓库里的先例。
- 两方都不是凭空推测，所以属于 P5。

与 09-25 各方结论一致：
- 公开读者在隔离阅读下判为"无法裁决"（`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/results/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9/public_read.md:24-27`）；
- 主审、复核和 Codex 首批复核都把它记为歧义。

本次核对没有找到能推翻这一结论的新公开材料。

### 1.4 非公开的来源意图（只供用户决定时参考，不能当作公开依据）

- gold 的 docstring 写着 "If `once` is true, only show this warning once (determined by the slug.)"（`PRIV/gold.patch:23-24`）。
- 09-25 复核核对过来源原始行：R2E 题面生成器的输入里有 "(determined by the slug.)" 这句话，但生成出来的题面漏掉了。
- 同仓后来的版本里唯一的 once 调用，消息是固定的 `"Conflicting dynamic contexts"`（`runs/r2e_static_prep_20260924/v3/public/coveragepy__97997d2cd6801d0335e3fa162b719d6f8c160266/worktree/coverage/control.py:589`）。这个调用本身区分不了两种读法。

## 2. 决定包

| 选项 | 做什么 | 评分材料 | 各候选得分 | 代价与影响 |
|---|---|---|---|---|
| **A（建议）：按 slug** | R-f：在期望行为后补一句（见下方草稿）。R-c：补 `test_warn_once_each_slug`（§3） | 76 键（+1） | gold 1、CE3 1；CE1 0（此时它违反了修订后的题面，属于正确拒绝）；CE4 0 | "题面文本替换"修订类已实现并经 Codex 复核通过（`codex_reviews/review_code_A_B_20260929.md`，09-29 协调者更正）。题面版本改变后，本题只能作"标明版本的自建题"。R-f 验收要找一位没看过隐藏测试和 gold 的新公开读者复读题面 |
| B：按消息 | R-f：补一句"按消息判断重复"。改隐藏测试 `test_warn_once`：把 `assertNotIn("Warning, warning 2!")` 改为 `assertIn`，并补"同一消息重复时只显示一次"的断言。同时保留 §3 的 R-c | 76 或 77 键 | gold 0；按 v1 D4，要改用经独立核实的 CE1 作正对照；CE3 0 | 偏离来源提交的意图和 gold，相当于重新定义题目。不建议 |
| C：不修订 | 保持现状，本题只作问题定位，不进探针、能力比较和训练 | 不变（75 键） | CE1 0（有争议）；CE4 1（漏测） | 成本最低，代价是少一道简单题 |
| 不可选 | 把两种输出用"或"并起来 | — | — | v1 §3 P5 明文禁止 |

**建议选 A 的理由**：
- 按 slug 一方的公开依据更成体系（§1.1），与来源提交的意图一致，gold 可以继续作正对照。
- 与 B 相比，A 不需要改动原有的隐藏断言。
- 与 C 相比，A 保留了一道能直接检验"once 真正去重"的题。

**A 的 R-f 草稿**（即 `revision_draft.json` 的 `statement_edits`）：

- old（`PUB/user_prompt.txt:18`）：
  > Warnings marked with `once=True` should be displayed only once each, preventing duplicate warnings from appearing.
- new：
  > Warnings marked with `once=True` should be displayed only once each, preventing duplicate warnings from appearing. As with `disable_warnings`, a warning is identified by its `slug` (the short name shown in parentheses after the message): once a `once=True` warning has been displayed, later `once=True` warnings with the same slug are not displayed, even if their message text is different. `once=True` warnings with different slugs are each still displayed once.
- 备选写法（信息量相同，更像 issue 里描述期望输出的写法；09-25 复核 N5 也提过）：
  > In the example above, only `Warning, warning 1!` should be displayed; `once=True` warnings with different slugs are each still displayed once.

**逐行核对草稿**：
- 新句没有隐藏测试的精确文案或测试输入。第二个测试里的字符串 "Hello from the first warning" 等没有出现在题面里。
- 没有给出实现细节，例如没有提列表、`_no_warn_slugs` 或快照。
- "the short name shown in parentheses" 描述的是公开格式：`control.py:347` 与 `doc/cmd.rst` 的警告清单。
- 最后一句只是复述题面的 "only once each"，两种读法下都成立。
- R-f 的验收（新公开读者复读、Codex 复核）由协调者安排。

## 3. 模板内的 R-c：不同 slug 各显示一次（选 A 或 B 都需要，选 C 不需要）

- **缺口**：目标测试只覆盖"同一 slug、不同消息"这一种情形。
  - CE4（第一次 once 之后，所有 once 警告都不显示）得 1（`runs/r2e_actor_20260925/grader/ledger_cov_CE4.jsonl`）。
  - 按 v1 §4 第 4 步，同一核心要求 "only once each" 的另一个实例（不同 slug）被违反，判 S1。
- **公开依据**：`PUB/user_prompt.txt:18` 的 "displayed only once each"，即每条警告都要显示一次。
  - 不同 slug、不同消息的两条 once 警告，在两种读法下都应该各显示一次，所以这条断言与 P5 无关。
- **改动**：
  - 目标文件 `r2e_tests/test_1.py`，父版本 sha256 为 `b95edf2e…`。
  - 修订类别 `hidden_test_text_replace`。`old` 是原文件第 548–549 行的两条断言，这段文本在文件中恰好出现一次。
  - 在 `test_warn_once` 之后新增下面的方法。按草案生成的文件 sha256 为 `05bcd489…`。
  - `r2e_tests/test_2.py`（09-25 已登记的 R04 搬迁伪影）不动。

```python
    def test_warn_once_each_slug(self):
        # R2E revision (2026-09-29): "displayed only once each" -- once=True
        # warnings with different slugs (and different messages) are each shown.
        cov = coverage.Coverage()
        cov.load()
        cov._warn("Hello from the first warning", slug="first-slug", once=True)
        cov._warn("Hello from the second warning", slug="second-slug", once=True)
        err = self.stderr()
        self.assertIn("Hello from the first warning", err)
        self.assertIn("Hello from the second warning", err)
```

- **期望映射的变化**：新增 `ApiTest.test_warn_once_each_slug: PASSED`，由 75 键变为 76 键，其余键不变。
  - 父版本 `PRIV/expected_output.json` 的 sha256 为 `c65a3c08…`。
  - 完整映射见 `revision_draft.json` 的 `expected_after`。
- **试跑**：
  - 镜像 `sha256:828436b9958c00f49b6162dd487fa95e8329c992e0a8c09eab3cc40686a742da`，配方 `r2e_derive_v1+sysconfig_v1`；
  - 以评分用户 uid 54322 运行，不联网；
  - 每个候选跑 1 次，测试段约 7–11 秒。

| 候选 | 补丁 | 应得分 | 应失败的键 | 试跑结果 | 文件 |
|---|---|---|---|---|---|
| 环境确认：noop（当前材料） | — | 0 | 原目标键 | mismatch，只有 `ApiTest.test_warn_once` 失败（`TypeError: _warn() got an unexpected keyword argument 'once'`） | `trials/env_noop_current.json` |
| 环境确认：gold（当前材料） | `PRIV/gold.patch` | 1 | — | match，75/75 | `trials/env_gold_current.json` |
| gold（正对照） | `PRIV/gold.patch` | 1 | — | match，76/76 | `trials/rev_gold.json` |
| noop | — | 0 | 原目标键加新键 | mismatch，正是这 2 个键，都是 TypeError | `trials/rev_noop.json` |
| CE3：按 slug 的另一种实现（独立集合） | `CANDS/coveragepy_5dbb_CE3_dedupe_by_slug.patch` | 1 | — | match，76/76 | `trials/rev_CE3.json` |
| CE4：第一次 once 后全部静默（原先得 1） | `CANDS/coveragepy_5dbb_CE4_first_once_silences_all.patch` | 0 | 新键 | mismatch，只有新键（AssertionError） | `trials/rev_CE4.json` |
| CE1：按消息去重（P5 对照，原先得 0） | `CANDS/coveragepy_5dbb_CE1_dedupe_by_message.patch` | 0（选 A 时）| 原目标键 | mismatch，只有 `ApiTest.test_warn_once`；新键通过 | `trials/rev_CE1.json` |

**对照 v1 §5 的 R-c 验收**：
- 正对照为 1、noop 为 0：满足。
- 要纠正的误判已被纠正：CE4 由 1 变为 0。
- 合理替代没有被误拒：CE3 得 1。
- CE1 在新键上通过，说明这条 R-c 没有暗中替 P5 做出选择。
- Codex 复核（`codex_reviews/review_revision_coveragepy.md` §3）：R-c 可单独落正式修订单；决定包总体公允，只需更正"题面修订机制尚待实现／复核"这一过时说法（已改）。推荐 A 的理由是来源意图与改动成本，不能据此说按消息实现违反当前公开要求。

## 4. 与正式评分的差别、未做的事

- **试跑工具与正式评分的差别**（见 `rh2/experiments/r2e_lifecycle_20260929/trial_grade.py` 文件头）：不做基线重建比对、不核对隐藏测试树与入口摘要、权限布置经过简化。用户选定 A 或 B 之后，要按正式材料重跑正式评分的 gold、noop 与 CE4。
- **R-f 的前提**：R-f 依赖的"题面文本替换"修订类已实现并经 Codex 复核通过（09-29 协调者更正）。选 A 之后仍需新公开读者验收题面与正式评分；在用户选定之前，本题只落与读法无关的 R-c（第 2 轮正式修订单），整题保持 P5 待决、不进探针。
- **本次不处理的既有项**：
  - gold 的三个副作用 G1–G3：快照 `disable_warnings`、once 与非 once 共用抑制列表、`slug=None` 也被记入列表（见 09-25 审查卡附录）；
  - R04：base 版测试辅助里的假 `_warn` 不接受 `once`，只影响超出题面要求的改动。
  - 它们都不受上述任一选项影响。
- **稳定性**：每个候选只跑了 1 次。新测试不依赖时间或网络。
- **进探针的条件**：
  - 选 A：需要正式材料（R-c 加 R-f）、正式评分的正负对照和 Codex 复核都完成；
  - 选 C：本题标"只作问题定位"。

## 5. 边界自查

- **没有自行选择任务目标**：P5 交用户决定；R-f 草稿只作为选项 A 的一部分提交。
- **R-c 与 P5 无关，只针对一个窄问题**：它没有扩大需求，也没有把两种读法用"或"并起来。
- **没有为保住 gold 而放宽**：原断言 `assertNotIn("Warning, warning 2!", err)` 保持不变。
- **没有越界改动**：没有改生产代码，也没有写 `s2_r2e` 下的正式修订单和 pins。
