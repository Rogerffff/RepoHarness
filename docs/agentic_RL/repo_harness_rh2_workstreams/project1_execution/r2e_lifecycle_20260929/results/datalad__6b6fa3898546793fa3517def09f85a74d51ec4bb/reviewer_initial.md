# datalad 6b6fa389：独立复核初判（第一步，读主审与公开读者产物之前）

2026-09-29 08:25 +08 / 独立复核（新上下文，未参与主审）。只做静态阅读与已有运行原件核对，没有运行项目代码或容器。

**材料版本**：expected `sha256:15da45ba…`、隐藏测试树 `sha256:8af0fcf7…`、`revisions.json` 为 `[]`（本题无材料修订），派生镜像 `rh2-r2e-derived/datalad:6b6fa3898546-r2e_derive_v1`（image `sha256:acb73dcd…`，无配方修订）。

**路径缩写**（都相对仓库根）：
- `PUB` = `runs/r2e_static_prep_20260924/v3/public/datalad__6b6fa3898546793fa3517def09f85a74d51ec4bb`
- `WT` = `PUB/worktree`
- `PRIV` = `runs/r2e_static_prep_20260924/v3/private/datalad__6b6fa3898546793fa3517def09f85a74d51ec4bb`
- `HT` = `PRIV/hidden_tests/test_1.py`
- `LOG-N1` = `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-d_df2e5fa5.eval.log`
- `LOG-G1` = `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-gold-d_9fbcea90.eval.log`
- `LOG-N2` = `runs/r2e_env_repair_20260924/_rerun2/eval_logs/evallog_replay-r2e-envrepair-rer_bfdadd81.eval.log`
- `LOG-G2` = `runs/r2e_env_repair_20260924/_rerun2/eval_logs/evallog_replay-r2e-envrepair-rer_fb016508.eval.log`

---

## 0. 结论先行

| # | 发现 | 编号 / 严重度 | 证据层级 |
| --- | --- | --- | --- |
| 1 | 隐藏断言 `HT:216-217` 要求 `'example.com/path/sp1:fname'` 解析成 `ssh:implicit`、hostname 为 `'example.com/path/sp1'`。题面没提"冒号前有 `/`"这类输入；base 行为、git 与 scp 的约定都把它当本地路径；上游后来也把这条期望改判成本地路径。按 git 规则实现的合理修复（候选 A）预计得 0 | **T1 误拒（根因 P3）**，待 1 次正式评分确认 | 源码推断 + 同仓他题公开初态（上游后续状态）+ 外部常识 |
| 2 | 扣除第 1 条有争议的实例后，base 上会失败、且有公开依据的核心断言只剩题面示例原样 `'weired_url:/'`（`HT:206`）。如果按第 1 条放宽 `HT:216-217`，必须同时补一个非示例实例，否则"硬编码示例"的退化候选 D1 会得 1 | **S1（T2c）**，按严格 D1；是否成立取决于第 1 条的裁定 | 源码推断 |
| 3 | gold 的规则很宽（任何未转义冒号都当 host:path），会把含冒号的本地路径（如 `'/data/run:1'`、`'sub/dir:x'`）解析成 `ssh:implicit`，`is_url` 由 False 变 True；`install` 正是用 `is_url` 区分本地路径与 URL | **G1 → T3（S2 登记）**，边缘输入 | 源码推断 |
| 4 | 期望 FAILED 的键 `test_get_local_file_url_linux` 是 Python 3.7 的 `quote` 不再转义 `~` 造成的；四次当前运行与两次 M3 运行都稳定。正确修复不会翻转它；只有越界改 `get_local_file_url` 才会翻转并判 0 | **T5 登记**，不需修订 | 日志 |
| 5 | 机械比对漏报：本题修复的核心逻辑以重构后的形式出现在同仓 4 题的公开初态里，其中 2 题的公开测试含本题隐藏断言的 RI 版原样 | **X1 登记** | 同仓他题公开包 |

- **暂定处置**：`needs_review`，理由是"题意 / 测试争议"（第 1 条）加上"待修订"（第 2 条）。评分侧环境本身没有问题。
- **唯一最优先的下一步**：在当前材料上用正式评分各跑一次候选 A 与 D1（§5）。确认 A=0（T1 成立）、D1=0；同时核对补丁确实交付、`test_url_samples` 确实执行到 `HT:216-217`。然后按 §7 做 R-b + R-c 修订。

---

## 1. 实际读取范围

- **角色与方法**：复核卡全文；主审卡——Read 工具显示了全文（53 行），只把"R2E 的评分口径""材料""第二批补充规则""单题闭环试行补充"四节当口径；八方面协议、R2E 环境卡、记录模板、统一标准 v1，都是全文。
- **公开包**：`PUB/user_prompt.txt`、`PUB/environment_brief.md`、`PUB/public_bundle.json`、`PUB/worktree_manifest.json`（头部字段）。
- **公开工作树**：`WT/datalad/support/network.py` 全文；`WT/datalad/tests/test_network.py`，与 `HT` 逐行 diff；`WT/datalad/distribution/install.py:105-135, 280-335`；`WT/datalad/tests/utils.py:11-52, 895-935`；`WT/tox.ini`、`WT/run_tests.sh`；对整棵工作树 grep 了 `URL(`、`is_url(`、`ssh:implicit`、`_split_colon` 与 docs 里的 ssh 写法。
- **私有包**：`gold.patch`、`expected_output.json`、`run_tests.sh`、`revisions.json`、`hidden_tests/`（`__init__.py` 为空、`conftest.py`、`test_1.py` 全文）、`grading_bundle.json`、`validation_bundle.json`、`run_refs.json`。
- **运行原件**（`material=current` 四行）：账本 `runs/r2e_rf_20260923/remote/ledger_r2e_all_{noop,gold}.jsonl:14` 与 `runs/r2e_env_repair_20260924/_rerun2/ledger_{noop,gold}.jsonl:14`；四份 eval log 全文或相关段，sha256 都与 `run_refs.json` 一致。独立参考：`runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl:27,75`（前 700 字符）与 `…/logs_r2e/datalad/6b6fa3898546/gold/a{1,2}/test_output.txt` 的摘要段，sha256 一致。
- **跨题**：`runs/r2e_static_prep_20260924/cross_task_{gold,test}_scan.json`，看了 method 与 datalad 相关的对。同仓其它 4 题（16c1ffc3、19f5b450、58ba5165、9ba5de09）只读了公开包：`user_prompt.txt` 前 3 行；对 `WT/datalad/support/network.py` 与 `WT/datalad/support/tests/test_network.py` 做 grep；读了 19f5b450 与 58ba5165 的 test_network.py 在 ssh 注释附近约 30 行、19f5b450 的 `network.py:360-400`、16c1ffc3 的 `network.py:285-312`。
- **没读**：`OUTPUT_DIR` 的任何文件、`history/`、各审查目录、本批 README / board / assignments、`runs/` 下的分析汇总、他题私有包。本步没有拿到 devcheck 目录；今晚 `*_budget1200` 的账本不在 `run_refs.json` 里，也没读。

---

## 2. 公开要求、初始问题与材料一致性

- **题面**（`PUB/user_prompt.txt`）：`URL('weired_url:/')` 应得到 scheme `'ssh:implicit'`、hostname `'weired_url'`、path `'/'`。一般表述是："带 hostname、冒号和 path 的 SSH implicit URL 被误当成 `file:implicit`"。题面没有提冒号前含 `/` 的输入，也没有提字符串重建。
- **公开旧测试**：`WT/datalad/tests/test_network.py:204-206` 里示例断言被注释掉，注释写"FAIL?!!! since schema is not allowing some symbols…"。因此在 base 上跑公开测试文件，`test_url_samples` 会通过，公开测试复现不了问题；求解者要自己写复现，题面的示例代码可以直接跑。
- **初始问题的成因**（源码 + 日志）：Python 3.7 的 `urlparse` 只把由字母、数字和 `+-.` 组成的前缀当 scheme，`weired_url` 含 `_`，所以不被识别。于是走到 `WT/datalad/support/network.py:491-499`：无 scheme、无 hostname，又不含 `@`，就落到 `file:implicit`。
  - `LOG-N1:86-102` 与 `LOG-N2:86-102` 的实际报错是 `URL(path='weired_url:/', scheme='file:implicit') != URL(hostname='weired_url', path='/', scheme='ssh:implicit')`，与题面的 Actual Behavior 完全一致。
  - `'weired:/'`、`'example.com:/'`、`'example.com:path/sp1'` 会被 urlparse 当成 scheme，走 `network.py:483-489` 的已有分支，base 上本来就对。
- **与 `/` 情形相关的公开依据**：
  - URL 类文档 `network.py:278-279`：这个类既要能拆开 URL，也要能重建字符串。
  - `is_url` 文档 `network.py:616`：`This includes ssh "urls" which git understands.`（外部常识，公开包内没有 git 文档原文：git 规定 scp 式写法只在第一个冒号前没有斜杠时才成立，以此区分含冒号的本地路径；scp 的判断同理。）
  - 公开测试 `test_network.py:270-271`：`nok_(is_url('relative'))`、`nok_(is_url('/absolute'))`。
  - 调用者 `WT/datalad/distribution/install.py:122, 292, 309, 321` 用 `is_url` 区分 URL 与本地路径。
- **材料一致性**：base `2753d472` 与题面一致；来源镜像 digest `edfa364d…`；隐藏测试树 `8af0fcf7…` 与日志里的 `RH2_SETUP_HIDDEN_TESTS_TREE` 一致（`LOG-N1:3`）；`run_tests.sh` 的 `8285765f…` 一致（`LOG-N1:4`）；gold `0ceae269…` 与账本 `patch_sha256` 一致；`initial_diff` 为空（`PUB/worktree_manifest.json`）。
  - 小记：`run_refs` 把第二组标成"09-24"，而账本里 `started_at_utc` 是 `2026-09-23T18:22Z`，按 +08 时区正好是 09-24，不算串题（非 X2）。

---

## 3. 需求—断言双向表

`HT` 收集 18 项，得到 17 个键：
- **目标键 1 个**：`test_url_samples`（noop FAILED，gold PASSED）。
- **回归键 15 个 PASSED**：都是 `network.py` 里其它 helper 的测试。
- **期望 FAILED 1 个**：`test_get_local_file_url_linux`。
- **不成键 1 项**：`test_get_url_straight_filename` 是 yield 测试，pytest 7.4.4 下 `XFAIL [NOTRUN]`（`LOG-N1:145`）。

| 公开要求 / 合理旧行为 | 公开依据 | 测试位置 / 决定性断言 | 覆盖 | 执行证据 / 待做 |
| --- | --- | --- | --- | --- |
| 示例 `'weired_url:/'` → `ssh:implicit` / `weired_url` / `/` | 题面 | `HT:206` → `_check_url`（`HT:112-122`）：字段全等，字符串两向重建 | 覆盖，但只用示例字面值 | noop 在 :206 失败（`LOG-N1:86-102`，`LOG-N2` 同）；gold PASSED（`LOG-G1:62`、`LOG-G2:62`） |
| 一般情形：示例之外的 `host:path`（hostname 不能被 urlparse 当 scheme） | 题面一般表述 | 没有：:204、:207、:208 在 base 上已通过，走的是旧分支 | **缺失 → T2c** | 静态 |
| 冒号前含 `/` 的字符串 | 题面未提；base、git、scp 与上游后续都当本地路径 | `HT:216-217` 要求 `ssh:implicit`、hostname `'example.com/path/sp1'`、path `'fname'` | **冲突 → T1** | 源码推断；noop 在 :206 就已停止，没执行到这里 |
| 转义冒号仍是本地路径 | `_split_colon` 文档 `network.py:595-597`；公开测试 `test_network.py:104`；base 行为 | `HT:209-210` | 覆盖（回归） | gold PASSED |
| 已有 ssh / file / datalad / dl+archive 的解析与重建 | 公开旧测试 | `HT:147-204` | 覆盖（回归） | noop 已通过 :204 |
| `'weired://'` 的警告与原串保存 | 公开旧测试 | `HT:226-234` | 覆盖（回归） | gold PASSED |
| 不含冒号的本地路径不是 URL | 公开旧测试 | `HT:281-282` | 覆盖；含冒号的本地路径未测 | 静态 |
| 字符串重建一致 | URL 文档 `network.py:278-279` | `HT:116-118`（新增的 :116 恒真，因为 `_str` 就是原串，`network.py:524`） | 覆盖 | — |

---

## 4. R2E 专项

**(a) 非 PASSED 的期望键 `test_get_local_file_url_linux`**
- 失败点：`HT:291`，`'file:///a~' != 'file:///a%7E'`（`LOG-N1:110-122`、`LOG-G1:30-42`、`LOG-G2:30-42`）；M3 两次同样（`test_output.txt:55`）。
- 成因：Python 3.7 起 `quote` 不再转义 `~`（标准库变化，与日志现象吻合）。
- 为什么正确修复不会翻转它：`get_local_file_url` 经 `_set_from_fields`（`network.py:644`），不走 `_set_from_str`；题面相关的修复，包括更完整的修复，都不碰这条路径。
- 风险：公开 `test_network.py:277-281` 是同一个测试，在 base 上恒失败。求解者跑公开测试时会看到这个与题无关的失败。如果他"顺手修"，让 `~` 编成 `%7E`，这个键就变 PASSED，整题判 0。这属于越界改动，不算误拒；探针分析时应单独标注。

**(b) 题面报错是否出现在 noop 目标键里**：出现，逐字段一致，见 §2。

**(c) 题面是否泄漏修法**：不泄漏，题面只给症状和期望字段。公开测试注释点出成因线索（scheme 不允许某些字符），但那是仓库公开内容，不构成 P1。

**(d) 测试支撑、搬迁伪影与撞键**
- 与公开文件相比，`HT` 只改了导入（相对导入改成绝对导入）并新增了断言。
- 依赖 base 版的 `datalad/tests/utils.py`：其中 `eq_` 等是 nose 的再导出（`utils.py:37-42`）；`get_most_obscure_supported_name` 带 `@with_tempfile`（`utils.py:912-931`）。
- `conftest.py` 是 R2E 注入的（每个测试用临时 HOME 并写 git config），本测试不依赖它的 `path` fixture。
- 只有一个测试文件，不会撞键。
- 候选能改 `datalad/tests/utils.py`，这是 R2E 的通用问题。本题的 FAILED 键恰好让"把 `eq_` 改成空操作"这类改法得 0。

**(e) 时间、随机、资源敏感的键**：没有发现。`rfc2822` 用固定时区；obscure name 取决于 `/tmp` 所在的文件系统，但结果稳定；整体测试只跑 1–2 s。

**(f) 材料修订**：无（`revisions.json` 为 `[]`），不适用。

**链路备注**（协调者提供，未核）：今晚那台机器上，`chown -R` 在 300 s 时限内会超时，正式评分放宽到 1200 s，账本记为 `*_budget1200`。这属于 E3 链路问题，评分语义不变。`run_refs.json` 没有列出这些行，我没有读到。

---

## 5. 候选（可直接改成补丁，协调者实跑）

**候选 A：合理替代解，预期 0，用来确认误拒**
- **改法**：保留 `gold.patch` 的全部改动，只把 gold 在 `URL._set_from_str` 里新增的条件（`gold.patch:40`）
  - 从 `if fields['path'] and '@' in fields['path'] or len(parts) > 1:`
  - 改为 `if fields['path'] and '@' in fields['path'] or (len(parts) > 1 and not set(parts[0]).intersection(set('/\\#'))):`
- **含义**：只有第一个未转义冒号前不含 `/`、`\`、`#` 时，才按 host:path 处理。这就是 git 的 scp 式规则，也是上游后来采用的写法（同仓 19f5b450 公开初态 `datalad/support/network.py:382`）。
- **预期**：`test_url_samples` FAILED，停在 `HT:216-217`，经 `HT:115` 的 `eq_(URL(url), url_)` 报 `URL(path='example.com/path/sp1:fname', scheme='file:implicit') != URL(hostname='example.com/path/sp1', path='fname', scheme='ssh:implicit')`；其余 16 键与期望一致，reward 0。
- **为何合理**：
  - 满足题面的示例和一般表述；
  - 保留 base 对 `a/b:c` 的旧行为；
  - 符合 `is_url` 文档所指的 git 语义；
  - 不引入 §0 第 3 条那种 gold 回归；
  - `HT:147-210` 在 A 下逐条通过（源码推断：A 只改无 scheme 分支，转义冒号的输入经 `_split_colon` 后长度为 1）。
- **说明**：上游后来的状态只用来判断 A 是否合理，不算本题求解者能看到的公开依据。

**D1：退化候选（v1 第 3 步，只凭 gold 的修改位置写出）**
- **改法**：在 base 的 `WT/datalad/support/network.py:492`，把 `if fields['path'] and '@' in fields['path']:` 改为 `if fields['path'] and '@' in fields['path'] or url == 'weired_url:/':`，其余不动。这样示例串会走 505-521 的已有 ssh 分支，由 `_split_colon` 拆出 hostname 和 path。
- **违反的公开要求**：题面的一般要求。例如 `URL('host_name:path/sp1')` 仍是 `file:implicit`，hostname 为空。类别是"只对示例字面值成立的硬编码"。
- **预期（当前材料）**：`HT:206` 通过，`HT:216-217` 失败，得 0。也就是说，**当前拒掉 D1 的唯一断言，恰好是有争议的 :216-217**。
- **预期（按 §7 修订后）**：在新增的 R-c 实例上失败，得 0。

**B：部分实现（可选，用于 R-b 验收）**
- **改法**：`gold.patch` 只保留 `_set_from_str` 那一段（`gold.patch:26-46`），不改 `__str_ssh__`。
- **预期（当前材料）**：`HT:216-217` 里的 `eq_(url, str(url_))` 失败，因为字符串被重建成 `'example.com:path/sp1/fname'`，得 0。按 §7 修订后，往返断言仍应让它失败。

---

## 6. 严重度（v1 §4 五步）

1. **核心要求有无直接断言**：有（`HT:206`），不命中。
2. **核心断言是否只用题面示例的字面值**：base 上会失败的核心断言只有两条——
   - `HT:206`：示例字面值；
   - `HT:216-217`：不是示例，但期望值没有公开依据，本身就是 T1 的来源。

   按严格 D1，我判 **命中 S1（T2c）**：唯一有公开依据的核心断言是示例字面值，:216-217 不能当正面覆盖证据。若协调者认为 :216-217 算非示例实例，第 2 步就不命中，但 T1 仍在。两种算法下结论相同：只要按 T1 处理 :216-217，就必须同时补 R-c。
3. **退化探测**：D1 在当前材料上预计得 0，不命中，待正式评分确认。修订后必须复测。
4. **已有候选是否违反公开要求**：gold 在"含未转义冒号的本地路径"上违反"本地路径不是 URL"（公开测试 :270-271 的精神，以及 `install` 的用法）。这是边缘输入，只判 **S2（T3）**，不升级。另外，gold 的 `__str_ssh__` 按 hostname 长度切片，从包含用户名的 netloc 开头算起，在"用户名 + 含 `/` 的主机"这种极端组合下会重建错误。这属于边缘情况，只登记。
5. 已有 S1，第 5 步不适用。

**小结**：S1（T2c，取决于 T1 裁定）+ T1 误拒（待候选 A 实跑）；T3、T5、X1 登记。

---

## 7. 修订建议（v1 §5，由协调者实施与实测，经 Codex 复核后生效）

**R-b（首选，把无依据的分类要求放宽为有依据的往返要求）**：把 `HT:211-217` 换成：

```python
    # With a '/' before the first unescaped colon the issue does not specify
    # host:path vs local path (git/scp treat it as a local path); only require
    # that whatever is parsed rebuilds to the same string.
    s = 'example.com/path/sp1:fname'
    eq_(str(URL(**URL(s).fields)), s)
```

- 依据：URL 类文档 `network.py:278-279`（拆开后能重建），以及 `_check_url` 注释"reconstruct it EXACTLY"。
- 源码推断：gold 与 A 都通过这条，B 失败。
- 退路：如果协调者更倾向最小改动，可改用 R-a，直接删除 :211-217；但那样 B 这类重建不一致的实现也会放行（边缘问题，T3）。

**R-c（修订后必需，补一个非示例实例）**：在 `HT:206` 之后加一行：

```python
    _check_url('host_name:path/sp1', scheme='ssh:implicit', hostname='host_name', path='path/sp1')
```

- 依据：题面一般表述"hostname 后接冒号和 path"。
- 这个实例的 hostname 与示例不同，path 是相对多段路径，会走 gold `__str_ssh__` 里 `':'` 那一支。base 上它是 `file:implicit`，会失败；gold 与 A 都通过（源码推断，已逐步跟踪 urlparse、`_split_colon` 与 `__str_ssh__`）。

**验收计划**：
- gold 得 1，noop 得 0（仍停在 `HT:206`）；
- 候选 A 得 1（误拒已纠正）；
- D1 得 0（在 R-c 行失败）；
- B 得 0（在 R-b 行失败，可选）；
- 键集仍是 17 个，`expected_output.json` 不改，确认无 missing、无 unexpected；
- 修订后仍受保护的公开要求：示例（:206）、一般情形（R-c 行）、旧行为（:147-210 与其余 15 个回归键）、重建一致（R-b 行）。

**不建议**：
- 用 R-f 给题面补一句"冒号前有 `/` 也算主机"：这没有公开依据，而且等于把隐藏测试细节写进题面。
- 把 :216-217 翻转成 `file:implicit`：会误拒 gold 式实现，同样没有依据。

**待用户决定**（只在协调者不同意 T1 归类时才需要）：如果把 `/` 情形看成任务目标层面的两种读法（P5），按 v1 应暂挂为问题定位。我不建议这样归类：题面的目标（示例与一般 host:path）两种读法都满足，分歧只出在题面没有提到的输入上。

---

## 8. 八方面覆盖与未查项

1. **公开需求**：已查题面、公开旧测试、URL 与 `is_url` 文档、调用者。未查：模型实际收到的完整消息（环境卡记为未知）。
2. **材料与初始问题**：一致，初始问题已由日志证实（§2）。
3. **测试是否测到要求**：目标键已逐条追到断言与 helper。**漏测**：一般情形只有示例（T2c）；含冒号的本地路径未测。
4. **是否误拒合理解**：**发现 T1**，待候选 A 实跑确认。
5. **回归与 gold 完整性**：gold 修到了示例，没有无关改动（另删了一个空行）。有边缘回归（T3）；隐藏测试反而强制了一个有争议的行为（即 T1）。15 个回归键覆盖同模块其它 helper。未查：全仓里含冒号本地路径的其它测试。
6. **开发条件**（`PUB/environment_brief.md`，镜像层面实测）：
   - `python` = `/testbed/.venv/bin/python` 3.7.9；无 pip，无网；agent uid 54321 可写 `/testbed`；无 git 身份。
   - 只需改 `datalad/support/network.py`，无构建、无新依赖。
   - 最小验证：`cd /testbed && python -c "from datalad.support.network import URL; u=URL('weired_url:/'); print(u.scheme, u.hostname, u.path)"`；以及 `python -m pytest datalad/tests/test_network.py -q`，在 base 上预期只有与题无关的 `test_get_local_file_url_linux` 失败。
   - 工作树里的 `run_tests.sh` 指向求解者看不到的 `r2e_tests`，直接跑会报路径不存在，影响很小。
   - **真实 actor 启动：actor 待验**（本步没有 devcheck）。
   - **开发缺口**：未见阻断性缺口。
7. **交付与评分边界**：gold 只改 `network.py`（账本 `projection.included_paths`）；R2E 按字节差导出，无构建产物；测试支撑可被候选修改（通用问题，见 §4(d)）。
8. **题目关系与用途**（**X1**）：
   - **16c1ffc3、9ba5de09**：公开初态的 `datalad/support/network.py:302` 有相同的 `len(parts) > 1` 条件；公开 `datalad/support/tests/test_network.py:266` 是 `_check_ri('weired_url:/', SSHRI, …)`，`:276` 是 `_check_ri('example.com/path/sp1:fname', SSHRI, hostname='example.com/path/sp1', path='fname')`，即本题隐藏断言的 RI 版原样。
   - **19f5b450、58ba5165**：`network.py:382` 已加上 `/\#` 限制；公开测试（19f5b450:340-341, 362, 367；58ba5165:335, 340）写着上游 2019-05-16 的更正——"这看起来是一个完全合法的路径"——并把 `'e.com/p/sp:f'`、`'f/s:1'`、`'f/s:'` 改判为 PathRI。
   - **机械比对为何漏报**：gold 扫描要求逐字 ≥80%，上游重构后对不上；测试扫描只看新增的 test 函数名，而本题隐藏测试没有新函数名，结构上就不可能命中。
   - **方向**：本题修复包含在这 4 题的初态里。反向（它们的修复在本题初态里）：本题 base 最早（`network.py` 663 行，另 4 题是 934–1216 行），没有发现，但没有读它们的 gold。
   - **题面泄漏**：未见 P1。
   - **材料错配**：无。

---

## 9. 用途初判（v1 §2 四项）

| 用途 | 结论 | 还差什么 |
| --- | --- | --- |
| `problem_localization` | yes | — |
| `capability_comparison` | conditional | (1) 候选 A 正式评分确认 T1 之后，要么先完成修订，要么在比较里把"只因 `HT:216-217` 判 0"的失败单列为规格争议，原始 reward 保留；(2) actor 开发条件缺 devcheck 证据；(3) 今晚 budget1200 运行的 gold 1 / noop 0 未在 `run_refs` 中核到 |
| `training_candidate` | no（当前材料） | 有未处理的 S1（T2c）与 T1。R-b + R-c 验收、Codex 复核后可重评；另需登记 X1，训练时控制与同仓 4 题的重复采样 |
| `heldout_candidate` | no | 修订后只能作"标明版本的自建题"；同仓 4 题的公开初态已含本题答案，按 D3 划分时 datalad 必须整体放在同一侧 |

`intended_use` 仍是 `development_diagnostic`（由主审记录）。

---

## 10. 探针就绪差距

本批 README §3 按指示未读；以下按 v1 §2 与环境卡列出，请协调者对照 README §3 补齐。

**已满足**：
- 当前材料上 noop=0、gold=1：同一派生镜像，各两次（账本 :14 四行）；M3 独立 runner 在来源镜像上 gold=1 两次；
- 题面症状在 noop 日志里复现；
- 期望 FAILED 的键已解释清楚；
- 无材料修订需要核支撑；
- 核心要求到断言的映射已完成（§3）。

**未满足，与负责方**：
1. 候选 A、D1 的正式评分，并核对交付与执行位置——协调者；
2. R-b + R-c 的实施、验收与 Codex 复核——协调者 / Codex；
3. 真实 actor 的开发核对（devcheck）——协调者；
4. 今晚机器 `*_budget1200` 的 gold 与 noop 行补进本题 `run_refs`——协调者；
5. X1 关联登记进训练采样约束——协调者。

---

## 11. 疑点与未知

- 候选 A 得 0 是源码推断，失败位置我有把握，但还没有实跑证据。
- gold 在 `is_url('/data/run:1')` 上的回归同样是源码推断（逐步跟踪了 Python 3.7 的 urlsplit、`_split_colon` 与 gold 的 `__str_ssh__`），未实测。它只影响边缘输入，不影响处置。
- git 与 scp 对冒号的约定是外部常识，公开包里没有它们的文档原文；公开依据只有 `is_url` 文档里指向 git 的那一句。
