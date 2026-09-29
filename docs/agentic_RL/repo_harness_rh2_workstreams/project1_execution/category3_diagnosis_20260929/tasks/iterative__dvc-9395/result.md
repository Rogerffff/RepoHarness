# iterative__dvc-9395：第3类诊断结果（v4，经两轮独立复核）

2026-09-29 / Claude（云端，第3类负责人）。原分类为第3类“具体疑点缺辨别实验”。计划做的实验是：在本地 remote 下比较 base 与 gold 的 dry-run、非 dry-run 和无 remote 对照。

**结论：问题和修法已明确，建议转第2类。** 本页经过两轮独立复核：首轮复核（2 项阻断）→ 主审 v2 → 聚焦复核（又 2 项阻断）→ 主审 v4。同一题连续两轮出现新阻断，已触及协作协议的“修复循环熔断”。因此本版按“最小充分”收口：采纳复核已私测的 v3 断言，只补一个 §4 第 2 步要求的非示例实例，其余问题登记，不再扩大修订范围。第2类或 Codex 若仍发现新问题，建议先裁定范围，不要继续叠加断言（见 §8）。

问题与处置：

| 编号 | 问题 | 判定 | 处置 |
| --- | --- | --- | --- |
| T1 | F2P 精确断言 `checkout` 调用 3 次，`restore` 恰好调用一次；行为同样正确的实现被判 0 | 已确认 | R-b 删除计数，放宽 `restore` 断言 |
| N1 | F2P 只断言返回值为真；吞掉错误的退化补丁 `w_swallow3` 在**原测试**下得 1 | S1（§4 第 3 步） | R-c 断言数据与下游内容，并要求拿不到数据时报错 |
| N2 | 用户改过数据源后 `repro --pull`：gold 在非交互时报 `ConfirmRemoveError`，交互时确认后**用旧数据覆盖用户修改** | S1（§4 第 4 步，主审裁定） | R-c 要求修改保留，包括“对提示一律回答是”的路径 |
| N7 | F2P 只测题面示例形态（`dvc add` 的数据源）；`dvc import` 也是数据源，缺失时同样应拉回 | S1（§4 第 2 步严格版） | R-c 补 import 实例 |

**修订测试 v4 的私有评分**（16 个候选）：
- 得 1：`c3_frozenfix`（新主正对照）、`up351_port`（第二正对照，上游 3.51 移植）、`c3_missing_only`；
- 得 0：gold、`alt_ds_only`、`gold_guarded`、`up257_port`、`mine_ondemand`、`mine_retry`、6 个错误候选和 noop。

**证据层级**：全部是私有 pytest 模拟与私有行为对照。正式评分需要 dvc_tail_v1 离线安装配方，云端无法完整重建。

## 1．公开要求

题面原文要求 “Make that `dvc repro --pull` pulls all missing files”。它指出原来只拉取从 run-cache 恢复的输出，“sources (i.e. dvc files having only output and no command at all)” 缺失时不会被拉取，并提议改成 “pull whatever is missing and necessary for this repro”。帮助文本写的是 “Try automatically pulling missing cache…”。

相关的公开依据：

- base 的 `Stage.is_data_source` 文档字符串写明 “Whether the DVC file was created with `dvc add` or `dvc import`”，判定条件是 `self.cmd is None`，所以 `dvc import` 的文件也是数据源。test_patch 自带 `test_repro_pulls_mising_import`：base 失败，gold 通过。它不在参考名单里，推测是 SWE-Gym 环境的 pygit2 版本让 import 测试在运行期失败，未查证。
- base 的 `StageCache.restore` 明写 `if pull and not dry:`；`test_repro_dry` 断言 dry 运行不改变输出。
- “修改数据后 repro”是有公开旧测试的常用行为：`tests/func/test_repro.py` 的 `test_repro_changed_data`、`test_repro_data_source`，后者断言数据源更新为新 hash。

gold 做了两处改动，都不检查 `dry`，也都不处理“没有 remote”：

1. 在 `reproduce()` 开头调用 `self.stage_cache.pull(None)`；
2. 在 `_reproduce_stages` 中，对 `stage.changed()` 的 stage 执行 `repo.pull(stage.addressing, allow_missing=True)`。“changed” 也包括用户修改过数据，所以会去 checkout 旧版本。

## 2．候选

| 候选 | 作者 | 做法 |
| --- | --- | --- |
| base（noop） | — | — |
| gold | 参考修复 | 见 §1 |
| `alt_ds_only`、`gold_guarded` | 主审 | gold 的两种变体：逐 stage 拉取只针对数据源；dry 与无 remote 加保护 |
| `c3_missing_only` | 主审 | 数据源（`cmd is None`，含 import）只拉取工作区里缺失的输出；顶层 run-cache 拉取遵守 `dry` 与 `run_cache`，remote 不支持 run-cache 或未配置 remote 时只警告 |
| **`c3_frozenfix`** | 主审＋复核（一行） | `c3_missing_only` 把跳过条件改成 `if stage.cmd and not stage.frozen`，于是冻结的命令 stage 缺失的输出也会拉取 |
| **`up351_port`** | 复核 | 按上游 3.51.0 移植：只有“除缺失数据外无其它变化”的 stage 才执行 pull 与 checkout |
| `up257_port` | 复核 | 按上游 2.57.0（到 3.50.x 一直沿用）移植：`Stage.run` 对无命令或冻结的 stage 执行 pull 与 checkout |
| `mine_ondemand`、`mine_retry` | 复核 | 数据源在 `Stage.run` 中只拉取缺失的输出，run-cache 在 `restore` 找不到时拉取；不处理 import |
| `w_nort` | 复核 | 只有数据源部分，不拉取 run-cache |
| `w_swallow`、`w_swallow3` | 复核 | gold 加“吞掉 stage 失败”；后者再凑出 3 次 checkout |
| `w_gold_catch`、`w_gold_swallow` | 复核 | gold 的预拉取包 `try/except`，或加 stage 级吞错误 |
| `w_mine_swallow` | 复核 | `mine_ondemand` 加吞错误 |

补丁在 `rh2/experiments/category3_cloud_20260929/dvc9395/`，复核者的候选原样复制在 `reviewer_cands/`，sha256 与复核附录一致。`c3_missing_only.patch` 为 `ac0a90ac…`；`c3_frozenfix.patch` 为 `94d44848…`，与前者只差上述一行。

## 3．私有评分（四版测试）

**方式**：
- 镜像：原镜像 `xingyaoww/sweb.eval.x86_64.iterative_s_dvc-9395`，摘要 `sha256:479c3af7…c0e`，与冻结值一致；root、断网、一次性容器。
- 环境：按 09-19 dvc_tail_v1 配方，把 pygit2 固定为 1.14.1（wheel 为 `230493d4…dd93`，与 PyPI 一致）。复核核实，这个 pin 只影响 import 类测试，29 个参考 ID 装与不装结果相同。
- 判分：应用测试补丁后，对两个测试文件运行 `pytest -rA`，逐 ID 对照参考名单（F2P 2 项、P2P 27 项），全部 PASSED 才记 1。
- 结果文件：`evidence/revised_v2/grades.json`、`evidence/revised_v4/grades.json`。v3 是复核的草案，由复核者私测，主审未单独跑。

| 候选 | 原测试 | v1 | v2 | **v4** | v4 失败原因 |
| --- | --- | --- | --- | --- | --- |
| base | 0 | 0 | 0 | 0 | 缺数据源；run-cache 未拉取 |
| gold | **1** | 1 | 0 | 0 | 模拟对提示一律回答“是”后，foo 被还原，第二次 repro 返回空 |
| `alt_ds_only` | 0 | 1 | 0 | 0 | 同 gold |
| `gold_guarded` | **1** | 1 | 0 | 0 | 同 gold |
| **`c3_missing_only`** | 0 | 1 | 1 | **1** | — |
| **`c3_frozenfix`** | — | — | 1（复核测） | **1** | — |
| **`up351_port`** | — | — | 1（复核测） | **1** | — |
| `up257_port` | — | — | 0（复核测） | 0 | foo 被还原为旧内容 |
| `mine_ondemand` | 0 | 1 | 1 | 0 | import 数据未拉回（`MissingDataSource`） |
| `mine_retry` | 0 | 0 | 1 | 0 | 同上 |
| `w_nort` | 0 | 0 | 0 | 0 | run-cache 未拉取 |
| `w_swallow` | 0 | **1** | 0 | 0 | foo 不存在 |
| `w_swallow3` | **1** | **1** | 0 | 0 | 同上 |
| `w_gold_catch` | — | — | **1**（复核测） | 0 | 同 gold |
| `w_gold_swallow` | — | — | **1**（复核测） | 0 | 同 gold |
| `w_mine_swallow` | — | — | **1**（复核测） | 0 | import 数据不存在 |

P2P 27 项在所有候选、所有版本下全部通过。v4 的所有失败都落在 F2P `test_repro_pulls_mising_data_source`；base、`w_nort` 另有 `test_restore_pull` 失败。

## 4．行为对照

**（1）复核者的 17 个行为场景**（`behav_v2/`）
- 做法：用复核者的 `behav.py`，经真实 CLI、非 TTY 运行；每个场景新建临时 git＋dvc 仓库和本地 remote，HTTP 场景在容器 loopback 上起只读 `http.server`。候选由主审重跑，比较场景结果与 base 是否相同，汇总在 `diff_vs_base.json`。
- **与 base 只差两处的候选**：`c3_missing_only`、`mine_ondemand`、`mine_retry`，两处都是改进：
  - B7：题面场景修好；
  - B4：HTTP remote 下也能拉回缺失的数据源，而 base 与 gold 都失败。

  `c3_frozenfix` 同样只差这两处；`up351_port` 另外在 6 个 dry 与无 remote 场景上与 gold 类似，属于已登记的 S2，见 §9。
- **gold 与 base 的主要差别**：

| 场景 | base | gold |
| --- | --- | --- |
| B3：foo 被用户修改，非 TTY | rc 0，foo.dvc 更新 | rc 255，`ConfirmRemoveError` |
| B3t：同上，在 TTY 中回答 y | 无提示，结果正确 | 出现删除提示；回答 y 后 **foo 被还原为旧内容**，rc 0 |
| B1、B1b、B1c：`--pull --dry` | 工作区与缓存不变 | 写回文件，下载缓存与 runs |
| B2、B2b：未配置 remote | 正常 | rc 251 |
| B4b：HTTP remote 下从 run-cache 恢复 | 成功 | rc 255 |
| B5：已存在但无 hash 的输出 | 正常 | rc 255 |
| B6：`--no-run-cache --pull` | 不下载 runs | 下载 runs |
| B9：依赖已变、旧输出不可得 | 重新计算 | rc 255 |

**（2）主审自写的 10 个场景**（`semantic_v2/`、`semantic_v3/`，API 调用，脚本 `behavior_v2.py`、`behavior_v3.py` 由主审独立编写）

| 场景 | base | gold | `c3_missing_only` | **`c3_frozenfix`** | `mine_ondemand` | **`up351_port`** |
| --- | --- | --- | --- | --- | --- | --- |
| 数据源缺失（题面） | 失败 | 成功 | 成功 | 成功 | 成功 | 成功 |
| import 数据缺失 | 失败 | 成功 | 成功 | 成功 | **失败** | 成功 |
| 冻结的命令 stage 输出缺失 | 失败 | 成功 | **失败** | 成功 | 成功 | 成功 |
| 数据源被用户修改 | 保留 | **失败** | 保留 | 保留 | 保留 | 保留 |
| `--no-run-cache --pull` | 不下载 | **下载 runs** | 不下载 | 不下载 | 不下载 | 不下载 |
| `--pull --dry`（数据源缺失） | 报错，无副作用 | **拉取并执行** | 同 base | 同 base | 同 base | **拉取并执行** |
| 无 remote（普通与 dry） | 正常 | **`NoRemoteError`** | 正常 | 正常 | 正常 | **`NoRemoteError`** |
| run-cache 恢复（普通与 dry） | 正常 | 正常 | 正常 | 正常 | 正常 | 正常 |

`up351_port` 忠实保留了上游在 dry 与无 remote 下的行为，这两项在本题登记为 S2。v4 不测这两项，所以不影响它作正对照。

**（3）公开回归**（`public_v2/`）
- 范围：用 base 自带的测试文件，不应用 test_patch，共 8 个文件、198 个结果。
- 结果：
  - base：195 passed、3 xpassed；
  - `c3_missing_only`、`mine_ondemand`、`mine_retry`：与 base 逐测试相同；
  - gold：只有公开旧测试 `test_restore_pull`（`== 2`）失败，这印证了 T1；
  - `c3_frozenfix`、`up351_port`：与 base 逐测试相同。

## 5．判定

- **T1（已确认）**：
  - `checkout` 调用次数是内部实现细节。base 的公开旧测试写的是 `== 2`，隐藏版改成了 gold 实现下的 `== 3`；上游 2.57.0 与 3.51.0 的同一测试都是 `== 2`（只作佐证）。
  - `restore` 的“恰好一次”同样是实现细节：`mine_retry` 找不到记录时拉取后再调用一次，结果正确。
- **N1：S1，§4 第 3 步**。`w_swallow3` 在原测试下得 1，但数据源没有拉回，下游也没有生成（复核用 CLI 复现：rc 0，foo、bar、dvc.lock 都不存在）。
- **N2：S1，§4 第 4 步（主审裁定，复核同意）**。
  - 依据：
    - 题面只要求拉取**缺失**的文件；
    - “修改数据后 repro”是有公开旧测试的常用行为；
    - 交互运行时，确认提示之后用户修改会被静默覆盖。
  - 反证已实测：按上游 2.57.0 做法移植的 `up257_port`，在修订测试下同样覆盖修改，得 0。也就是说，gold（上游 PR 的写法）和上游首个发布版本的写法，在修订后都得 0；上游到 3.51.0 才改成“只拉取缺失的数据”。这不推翻裁定：上游最终的写法与裁定一致。
- **N7：S1，§4 第 2 步严格版（主审裁定）**。F2P 只测了题面举例的 `dvc add` 数据源。按 base 公开的 `is_data_source` 定义，`dvc import` 也是数据源；test_patch 本身也带 import 测试。所以补这一个非示例实例。
- **范围裁定：冻结的命令 stage 登记为 T3，不补断言**。
  - 它不属于题面定义的数据源（有命令），但属于 “all missing files … necessary” 的一般表述。
  - 登记为 T3 的理由有三：冻结命令 stage 在拉取场景中较少见；已经触及熔断，按最小充分原则不再扩大范围；新的正对照 `c3_frozenfix` 与 `up351_port` 都覆盖这一类。
  - `c3_missing_only` 在 v4 下得 1，但漏掉这一类，这一点要登记。
- **S2（登记，不补断言）**：

| 编号 | 现象 | 判 S2 的理由 |
| --- | --- | --- |
| G1-dry | `--pull --dry` 下 gold 会下载或写回数据，dry 的报告失真 | 组合不常见；主正对照没有这个问题 |
| G1-noremote | 未配置 remote 时 gold 报 `NoRemoteError` | base 在“无 remote 且走 run-cache 恢复”时本来也报错；上游到 3.67.1 也没有加保护 |
| N3 | HTTP remote 上 gold 连 base 原有的 run-cache 恢复也失败 | HTTP 是有文档但非主流的 remote；上游 2.58.2 前已修 |
| N4-B5、B9 | 已存在但无 hash 的输出、依赖已变且旧输出拿不到时，gold 报错 | 边缘状态 |
| N4-B6 | `--no-run-cache --pull` 仍下载 runs | 参数组合少见；上游 2.58.x 已改 |

- **P3 风险（登记）**：`test_restore_pull` 要求本地 runs 缺失时从 remote 拉取 run-cache，题面依据中等。复核建议登记、不修订，本页同意。
- **歧义（登记为 P5 类，不补断言）**：目录中删掉一部分文件时，算“缺失”还是“修改”？gold 会拉回缺的文件，c3、mine、`up351_port` 和 base 都把它当作修改。
- 题面清楚，不需要 R-f。

## 6．修法：R-b＋R-c v4（交第2类）

**修订测试**：[`revised_test_v4.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/dvc9395/revised_test_v4.patch)，sha256 `2f6ac1be…`。
- 版本链：原 test_patch `1252952e…` → v1 `d868cc6e…` → v2 `93cfea5d…` →（复核草案 v3 `a85cf11a…`）→ v4。
- 生成方式：在应用原 test_patch 的工作树上依次执行 `_edit_revised_test_v2.py`、`_edit_revised_test_v4.py`。
- 测试 ID 与参考名单不变。

| 位置 | 改动 | 模板与依据 |
| --- | --- | --- |
| `test_restore_pull` | 删除 `mock_checkout.call_count` 断言 | R-b，T1 |
| 同上 | `assert_called_once_with` 改为 `assert_called_with` | R-b，T1 |
| 同上 | `bar` 从“存在”改为内容等于 `"foo"` | R-c，N1 |
| `test_repro_pulls_mising_data_source` | 拉取后断言 foo、bar 内容都为 `"foo"` | R-c，N1 |
| 同上 | 把 foo 改成 `"modified"`，并 mock `dvc.prompt.confirm` 一律返回 True 后再次 `reproduce(pull=True)`：foo 保留，bar 为 `"modified"`，`dvc.status()` 为空 | R-c，N2（交互路径与提交状态取自复核 v3） |
| 同上 | 从外部 dvc 仓库 `dvc import` 一个文件，push 后删除工作区文件与缓存，`reproduce(pull=True)` 后内容恢复；函数签名加 `erepo_dir` fixture | R-c，N7；测试体取自 test_patch 自带的 import 测试 |
| 同上 | 从未 push 的数据源缺失时，`reproduce(..., pull=True)` 必须抛 `ReproductionError` | R-c，N1 的另一面（取自复核 v3） |

**正对照（D4）**：gold 在修订版上失败，改用替代正对照。

| 正对照 | 作者与核实 | 覆盖与局限 |
| --- | --- | --- |
| **`c3_frozenfix`（主）** | 主体由主审编写，复核按 D4 独立核实（首轮 17 场景、C 系列新场景、公开回归）；冻结条件那一行由复核者写，主审核实（冻结 stage 场景与 v4 评分） | 覆盖 `dvc add` 与 `dvc import` 数据源、冻结命令 stage、修改保留、dry、无 remote、`--no-run-cache`、HTTP |
| **`up351_port`（第二）** | 复核者编写，主审核实（自写 10 个场景、v4 评分） | 忠实于上游 3.51；保留上游在 dry 与无 remote 下的行为，这两项已登记 S2 |
| `c3_missing_only` | 主审编写，复核核实 | v4 得 1，但不拉取冻结命令 stage 的输出（T3）；可作补充对照，不作主正对照 |

`mine_ondemand` 与 `mine_retry` 因为不处理 import，在 v4 下得 0；按本页的范围裁定，这是正确的拒绝。它们在 v2 页中曾被列为主正对照，已撤回。

**交接给第2类**：

1. 在 dvc_tail_v1 配方下做正式评分：
   - 测试版本：原测试、v1、v4；
   - 候选：noop、gold、`alt_ds_only`、`gold_guarded`、`c3_frozenfix`、`up351_port`、`c3_missing_only`、`mine_ondemand`、`up257_port`、`w_swallow`、`w_swallow3`、`w_gold_catch`、`w_gold_swallow`、`w_mine_swallow`；
   - 原测试下 `w_swallow3` 的正式结果，就是 §4 第 3 步要求的那 1 次正式确认。
2. 经 D6 测试补丁替换切片形成版本。
3. 准入卡写明：
   - gold 在修订版上失败，正对照为 `c3_frozenfix`（第二正对照 `up351_port`）；
   - 两者的作者与核实分工；
   - T3、S2、P3 以及目录歧义，按 §5 登记。
4. 在训练价值备注中写明：修订后，gold 式实现与上游首个发布版本的写法都得 0，难度明显上升。
5. Codex 复核，重点确认 N7 的范围裁定和冻结 stage 的 T3 登记。

## 7．当前用途

原版只作问题定位：T1 误拒合理实现，N1 让退化补丁得满分，N2、N7 未覆盖。能力比较与训练在修订落地并验收前为 no。

## 8．独立复核

复核者先封存初判 [review_initial.md](review_initial.md)（sha256 `29b5a480…`），两轮结论都在 [review.md](review.md)。

- **首轮：部分同意，2 项阻断**。
  - 阻断 1：R-b 需要同轮补 R-c（N1）；
  - 阻断 2：N2 需要裁定，N3、N4 需要登记。

  两项已在 v2 处理。
- **v2 聚焦复核：部分同意，2 项阻断**。
  - v2 的私有评分逐项复现一致；
  - `c3_missing_only` 按 D4 **有条件通过**，条件是冻结命令 stage 这一缺口；
  - 阻断 1：N2 只保护了非交互路径，3 个错误候选得 1。已按复核的 v3 草案采纳，见 v4；
  - 阻断 2：更正正对照描述，裁定 import 与冻结 stage 的范围。已裁定：import 补断言（N7），冻结 stage 登记 T3。正对照改为 `c3_frozenfix` 与 `up351_port`，描述已更正；
  - 非阻断意见的处理：“按 3.51 语义”的说法已删除；`mine_ondemand` 的 import 局限已写明；N2 反证已改为“已实测”；交接清单已补新候选。
- **v4 本身没有再复核**。按熔断原则，交第2类时由 Codex 一并确认，不再由本线追加复核轮次。

## 9．未做、补充说明与证据

- **没有正式评分**。dvc_tail_v1 配方用 `--find-links=/opt/rh2/compat-wheels` 离线安装 `.[all,tests]`，需要 09-19 构建的 compat-wheels 派生镜像，云端没有它的 wheel 清单。
- 其它 remote 类型（S3、SSH）、`exp run --pull`、目录部分缺失的两种读法，都未查。
- 真实 actor 开发条件未验；没有模型求解证据。
- **`c3_frozenfix`、`up351_port` 的公开回归与 17 场景重跑**：
  - 公开回归：两者都与 base 逐测试相同（195 passed、3 xpassed）；
  - 17 个场景：`c3_frozenfix` 只在 B4、B7 两处与 base 不同，都是改进；`up351_port` 在 8 处不同，除 B4、B7 外，其余 6 处是继承自上游的 dry 副作用（B1、B1b、B1c）与无 remote 报错（B2、B2b、B2c），都已登记 S2。
- **证据**：[evidence/](evidence/)
  - `semantic_v1/`、`refs_v1/`、`revised_v1/`：v1 阶段；
  - `revised_v2/`、`revised_v4/`：私有评分；
  - `behav_v2/`：复核者的 17 个场景；
  - `semantic_v2/`、`semantic_v3/`：主审自写的场景；
  - `public_v2/`：公开回归；
  - `evidence_manifest.json`。
