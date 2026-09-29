# iterative__dvc-9395：第3类诊断结果（v2，按独立复核修订）

2026-09-29 / Claude（云端，第3类负责人）。原分类为第3类“具体疑点缺辨别实验”。计划做的实验是：在本地 remote 下比较 base 与 gold 的 dry-run、非 dry-run 和无 remote 对照。

**结论：问题和修法已明确，建议转第2类。** 首轮（v1）只修了计数断言；独立复核指出两项阻断，本版全部处理：

- **T1（已确认）**：F2P 精确断言 `checkout` 调用 3 次。行为同样正确的替代实现只因调用 2 次就被判 0。上游 dvc 2.57.0 的同一测试写的是 `== 2`。修法：R-b 删除该断言，并把 `restore` 的“恰好一次”放宽。
- **N1，S1（§4 第 3 步，复核发现）**：F2P 只断言 `reproduce` 的返回值为真。“吞掉错误”的退化补丁 `w_swallow3` 在**原测试**下得 1，而它既没有拉回数据源，也没有生成下游输出。修法：R-c 断言 foo、bar 的内容。
- **N2，S1（§4 第 4 步，主审裁定）**：用户修改过数据源之后运行 `repro --pull`，gold 会出问题：
  - 非交互运行时报 `ConfirmRemoveError`；
  - 交互运行时，用户确认提示后，所做的修改会被旧数据覆盖；
  - base 在这个场景下正常。

  修法：R-c 要求 `--pull` 保留被修改的数据源。gold 过不了这条断言，按 D4 改用替代正对照。
- **修订测试 v2 的私有评分**：
  - 3 个替代实现为 1：主审自写的 `c3_missing_only`，复核者写的 `mine_ondemand`、`mine_retry`；
  - gold、`alt_ds_only`、`gold_guarded`、3 个退化候选和 noop 都为 0。
- **S2 登记**：`--dry` 副作用、未配置 remote、HTTP remote、已存在但无 hash 的输出、依赖已变且旧输出拿不到、`--no-run-cache` 被忽略。
- **证据层级**：全部是私有 pytest 模拟。正式评分需要 dvc_tail_v1 离线安装配方，云端无法完整重建，见 §7。

## 1．公开要求

题面希望 `dvc repro --pull` 拉取复现所需的全部**缺失**文件，包括数据源（只有输出、没有命令的 dvc 文件）；原来只拉取从 run-cache 恢复的输出。帮助文本写的是 “Try automatically pulling missing cache…”。

与本题相关的公开旧行为：

- base 的 `StageCache.restore` 明写 `if pull and not dry:`，即 dry 模式下不拉取；`test_repro_dry` 断言 dry 运行不改变输出；
- “修改数据后 repro”是有公开旧测试的常用行为，见 `tests/func/test_repro.py` 的 `test_repro_changed_data`、`test_repro_data_source`。

gold 做了两处改动，都不检查 `dry`，也都不处理“没有 remote”：

1. 在 `reproduce()` 开头调用 `self.stage_cache.pull(None)`；
2. 在 `_reproduce_stages` 中，对 `stage.changed()` 的 stage 执行 `repo.pull(stage.addressing, allow_missing=True)`。“changed” 既包括数据缺失，也包括用户修改过数据，所以第二处会去 checkout 旧版本。

## 2．候选

| 候选 | 来源 | 做法 |
| --- | --- | --- |
| base（noop） | — | — |
| gold | 参考修复 | 见 §1 |
| `alt_ds_only` | 主审（v1） | 逐 stage 拉取只针对数据源，流水线输出靠 run-cache 恢复 |
| `gold_guarded` | 主审（v1） | gold 加上：dry 时不拉取，无 remote 时跳过 |
| **`c3_missing_only`** | 主审（v2） | 按上游 3.51 的语义，数据源只拉取工作区里缺失的输出；顶层 run-cache 拉取遵守 `dry` 与 `run_cache`，remote 不支持 run-cache 或未配置 remote 时只警告 |
| **`mine_ondemand`** | 复核 | 数据源在 `Stage.run` 中只拉取缺失的输出；run-cache 在 `restore` 找不到记录时才拉取 |
| **`mine_retry`** | 复核 | 数据源部分同上；run-cache 找不到时拉取，再调用一次 `restore` |
| `w_nort` | 复核 | 只有 `mine_ondemand` 的数据源部分，不拉取 run-cache（不完整） |
| `w_swallow` | 复核 | gold 的 run-cache 拉取；`pull=True` 时吞掉 stage 失败，照样计入结果 |
| `w_swallow3` | 复核 | `w_swallow` 加 gold 式预拉取，凑出 3 次 checkout |

补丁在 `rh2/experiments/category3_cloud_20260929/dvc9395/`。复核者的候选原样复制到 `reviewer_cands/`，sha256 与复核附录一致。`c3_missing_only.patch` 的 sha256 为 `ac0a90ac…`，由 `_edit_c3_missing_only.py` 生成。

## 3．私有评分（三版测试）

**方式**：原镜像 `xingyaoww/sweb.eval.x86_64.iterative_s_dvc-9395`，摘要 `sha256:479c3af7…c0e`，与冻结值一致。root、断网、一次性容器。

- 按 09-19 dvc_tail_v1 配方，把 pygit2 固定为 1.14.1（wheel sha256 `230493d4…dd93`，与 PyPI 一致）。复核核实：这个 pin 只影响不计分的 import 测试，29 个参考 ID 装与不装结果相同。
- 应用测试补丁后，对两个测试文件运行 `pytest -rA`，逐 ID 对照参考名单：F2P 2 项、P2P 27 项，全部 PASSED 才记 1。
- 结果见 `evidence/revised_v2/grades.json`。各 `rc.json` 是管道末端命令的退出码，不代表测试结果。

| 候选 | 原测试 | v1（只删计数） | **v2** | v2 失败位置 |
| --- | --- | --- | --- | --- |
| base | 0 | 0 | 0 | 两个 F2P：缺数据源、run-cache 未拉取 |
| gold | **1** | 1 | **0** | 修改过的数据源：`ConfirmRemoveError` → `ReproductionError` |
| `alt_ds_only` | 0（`2 == 3`） | 1 | 0 | 同 gold |
| `gold_guarded` | **1** | 1 | 0 | 同 gold |
| **`c3_missing_only`** | 0（`2 == 3`） | 1 | **1** | — |
| **`mine_ondemand`** | 0（`2 == 3`） | 1 | **1** | — |
| **`mine_retry`** | 0（`restore` 调用 2 次） | 0 | **1** | — |
| `w_nort` | 0 | 0 | 0 | `test_restore_pull`：run-cache 未拉取 |
| `w_swallow` | 0（`2 == 3`） | **1** | 0 | foo 不存在（内容断言） |
| `w_swallow3` | **1** | **1** | 0 | 同上 |

P2P 27 项在所有候选、三版测试下全部通过。

## 4．行为对照

行为对照正在运行，结果与公开回归见后续提交。已有部分如下：

- **主审自写的 8 个场景**（`semantic_v2/`，API 调用）：`c3_missing_only`、`mine_ondemand`、`mine_retry` 修好了题面场景；在“修改过的数据源”“`--dry`”“无 remote”“`--no-run-cache`”“run-cache 恢复”各场景下与 base 一致。gold 在“修改过的数据源”下失败，并忽略 `--no-run-cache`。
- **公开回归**（base 测试文件，198 个结果）：`c3_missing_only`、`mine_ondemand` 与 base 逐测试相同。gold 只有一处不同：公开旧测试 `test_restore_pull`（`== 2`）失败，这印证了 T1。

## 5．判定

- **T1（已确认）**：`checkout` 调用次数是内部实现细节。
  - base 的公开旧测试写的是 `== 2`，隐藏版改成了 gold 实现下的 `== 3`；上游 dvc 2.57.0 与 3.51.0 的同一测试都是 `== 2`（复核核对，只作佐证，不是公开依据）。
  - 三个替代实现结果相同（bar 恢复、命令未执行），只因次数不同被判 0。
  - `restore` 的“恰好调用一次”同样是实现细节：`mine_retry` 在找不到记录时拉取 run-cache 后再调用一次，结果正确，却被判 0（复核 N5）。
- **N1：S1，§4 第 3 步**。`w_swallow3` 在原测试下得 1，但数据源没有拉回，下游也没有生成。复核用 CLI 复现：rc 0，foo、bar、dvc.lock 都不存在。这违反题面的核心要求。
- **N2：S1，§4 第 4 步（主审裁定）**。
  - 依据有三：
    - 题面只要求拉取**缺失**的文件，被修改的文件不属于缺失；
    - “修改数据后 repro”是有公开旧测试的常用行为，`--pull` 又是题面希望默认使用的开关；
    - 交互运行时，确认提示之后用户修改会被静默覆盖，后果严重。
  - 反方理由（复核提出）：上游 2.57 到 3.50 期间，`Stage.run` 对 changed 数据源也执行 pull 与 checkout，持续约一年，直到 3.51.0 才改成“除缺失数据外无其它变化时才拉取”。这一点只看了源码，未实跑，说明这条路径可能不常被踩到。
  - 裁定理由：按 D1 严格版，已有构造候选在主路径上违反公开要求即判 S1。上游最终也按“只拉取缺失数据”修正，与本裁定一致。
- **S2（登记，不补断言）**：

  | 编号 | 现象 | 判 S2 的理由 |
  | --- | --- | --- |
  | G1-dry | `--pull --dry` 下 gold 会下载 run-cache 或取回数据，dry 的报告也失真 | 组合不常见；三个替代实现都没有这个问题 |
  | G1-noremote | 未配置 remote 时 gold 报 `NoRemoteError`，即使没有要拉取的内容 | base 在“无 remote 且走 run-cache 恢复”时本来也报错，gold 扩大了失败面；上游到 3.67.1 也没有加保护 |
  | N3 | HTTP remote 上 gold 报 `run-cache is not supported`，连 base 原有的 run-cache 恢复也失败 | HTTP 是有文档但非主流的 remote 类型；上游 2.58.2 前已修 |
  | N4-B5 | 已存在但内容不在缓存的输出，gold 试图删除，报 `ConfirmRemoveError` | 边缘状态 |
  | N4-B9 | 依赖已变、旧输出拿不到时，gold 报错，而本可以重算 | 边缘状态 |
  | N4-B6 | `--no-run-cache --pull` 仍下载 runs | 参数组合少见；上游 2.58.x 已改 |

- **P3 风险（登记）**：修改后的 `test_restore_pull` 要求在本地 runs 缺失时从 remote 拉取 run-cache。题面依据只有 “all missing files” 加上 `--pull` 原本就服务于 run-cache，依据中等，只修数据源的实现（例如 `w_nort`）会因此得 0。复核建议登记、不修订，本页同意。
- 题面清楚，不需要 R-f。

## 6．修法：R-b＋R-c v2（交第2类）

**修订测试**：[`revised_test_v2.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/dvc9395/revised_test_v2.patch)，sha256 `93cfea5d…`。

- 版本链：原 test_patch `1252952e…` → v1 `d868cc6e…` → v2。
- 由 `_edit_revised_test_v2.py` 在应用原 test_patch 的工作树上生成。
- 测试 ID 与参考名单不变。

| 位置 | 改动 | 模板与依据 |
| --- | --- | --- |
| `test_restore_pull`（F2P） | 删除 `mock_checkout.call_count` 断言（原 `== 2` 不再改成 `== 3`） | R-b，T1 |
| 同上 | `mock_restore.assert_called_once_with` → `assert_called_with` | R-b，复核 N5 |
| 同上 | `bar` 从“存在”改为内容等于 `"foo"` | R-c，复核 N1 |
| `test_repro_pulls_mising_data_source`（F2P） | `reproduce(pull=True)` 之后断言 foo、bar 内容都为 `"foo"` | R-c，N1：缺失的数据源被拉回，下游确实执行 |
| 同上 | 接着把 foo 改成 `"modified"`，再次 `reproduce(pull=True)`：断言 foo 仍为 `"modified"`，bar 也为 `"modified"` | R-c，N2：被修改的数据不是缺失，应保留并参与复现 |

**正对照（D4）**：gold 在 v2 上失败（N2 断言），需要改用替代正对照。

- **`mine_ondemand`（主正对照）**：由复核者编写，主审独立核实，满足 D4 “经他人独立核实”：
  - 满足题面：F2P 两个场景都通过；行为对照中缺失的数据源被拉回，run-cache 恢复正常；
  - 不破坏旧行为：§4 各场景与 base 一致；公开回归结果见 §4；
  - 设计合理：与上游 3.51.0 的“只拉取缺失数据”语义一致，改动局部。
- **`c3_missing_only`（第二正对照）**：由主审编写，**需要他人独立核实**，交复核者聚焦复核。
- `mine_retry` 在 v2 上也得 1，可作补充对照。

**交接给第2类**：

1. 在 dvc_tail_v1 配方下做正式评分：原测试、v1、v2 三套测试，各跑 noop、gold、`alt_ds_only`、`gold_guarded`、`w_swallow`、`w_swallow3`、`mine_ondemand`、`c3_missing_only`，建议加 `mine_retry`、`w_nort`。其中原测试下 `w_swallow3` 的正式结果，就是 §4 第 3 步要求的那 1 次正式评分确认。
2. 经 D6 测试补丁替换切片形成版本。
3. 准入卡写明：gold 在修订版上失败，正对照改为 `mine_ondemand`（第二正对照 `c3_missing_only`，待独立核实）；S2 与 P3 按 §5 登记。
4. 在训练价值备注中写明：修订后 gold 式实现得 0，难度上升。
5. Codex 复核。

## 7．当前用途

原版只作问题定位：T1 误拒合理实现，N1 让退化补丁得满分，N2 回归未覆盖。能力比较与训练在修订落地并验收前为 no。

## 8．独立复核

复核者先封存初判 [review_initial.md](review_initial.md)（sha256 `29b5a480…`），结论见 [review.md](review.md)。

- **总判断：部分同意**。T1 成立；dry、无 remote 两项可记 S2；v1 的数字属实；证据层级的说明诚实；pygit2 pin 没有问题。
- **阻断项 1（N1，R-b 需同轮补 R-c）**：已在 v2 处理。`w_swallow`、`w_swallow3` 在 v2 下为 0。
- **阻断项 2（N2 须裁定，并补登 N3、N4）**：主审判 N2 为 S1，按 D4 改用替代正对照；N3、N4 登记为 S2（§5）。
- **非阻断意见的处理**：
  - N5 已放宽；
  - “`alt_ds_only` 行为与 gold 相同”“`gold_guarded` 无 remote 时与 base 一致”两句已删；v1 页的这两句只在当时测过的场景内成立；
  - `gold_guarded` 不作通用正对照；
  - `refs_v1/summary.json` 被覆盖的问题：新增 `summarize_runs.py`，按各候选目录重建 `summary.json` 并抽取 `grades.json`，已应用到 `refs_v1`、`revised_v1`、`revised_v2`；
  - pygit2 的环境坑已按复核结论改写（§3）。
- **v2 聚焦复核**：待进行，重点是独立核实 `c3_missing_only` 能否作第二正对照，以及 N2 断言的宽严。

## 9．未做与证据

- **没有正式评分**。dvc_tail_v1 配方用 `--find-links=/opt/rh2/compat-wheels` 离线安装 `.[all,tests]`，需要 09-19 构建的 compat-wheels 派生镜像，云端没有它的 wheel 清单。本页所有 0/1 都来自同一组测试文件和同一份参考名单的私有模拟。
- S3、SSH 等其它 remote 类型，`exp run --pull`，目录型数据源与部分缺失的情形，都未查。
- 真实 actor 开发条件未验；没有模型求解证据。
- 证据：[evidence/](evidence/)
  - `semantic_v1/`、`refs_v1/`、`revised_v1/`：v1 阶段；
  - `revised_v2/`：10 个候选 × 三版测试；
  - `behav_v2/`：复核者的 17 个行为场景 × 7 个候选；
  - `semantic_v2/`：主审自写的 8 个行为场景 × 5 个候选；
  - `public_v2/`：公开回归；
  - `evidence_manifest.json`。
