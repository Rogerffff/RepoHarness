# iterative__dvc-9395：第3类诊断结果

2026-09-29 / Claude（云端，第3类负责人）。原分类为第3类“具体疑点缺辨别实验”。计划做的实验是：在本地 remote 下比较 base 与 gold 的 dry-run、非 dry-run 和无 remote 对照。

**结论：问题和修法已明确，建议转第2类。**

- **gold 回归已实测确认**：
  - `--dry` 下仍会下载 run-cache 或取回数据；
  - 未配置 remote 时 `repro --pull` 报 `NoRemoteError`，即使没有任何需要下载的内容。

  这些回归发生在不常见的组合路径上，按 S2 登记即可。
- **意外确认 T1 误拒**：修改后的 F2P 精确断言 `checkout` 被调用 3 次，一个行为同样正确的替代实现只因调用次数为 2 被判 0。修法是 R-b，删除这条计数断言。
- **证据层级**：以上评分结果都来自私有 pytest 模拟。正式评分需要 dvc_tail_v1 离线安装配方，云端无法完整重建，见 §6。

## 1．公开要求

题面希望 `dvc repro --pull` 拉取复现所需的全部缺失文件，包括数据源（只有输出、没有命令的 dvc 文件）；原来只拉取从 run-cache 恢复的输出。帮助文本写的是“Try automatically pulling missing cache…”。

与本题相关的公开旧行为有两条：

- base 的 `StageCache.restore` 明写 `if pull and not dry:`，即 dry 模式下不拉取；
- `test_repro_dry` 断言 dry 运行不改变输出。

gold 做了两处改动：

1. 在 `reproduce()` 开头调用 `self.stage_cache.pull(None)`；
2. 在 `_reproduce_stages` 中，对已变化的 stage 执行 `repo.pull(stage.addressing, allow_missing=True)`。

两处都没有检查 `dry`，也都不处理“没有 remote”的情况。

## 2．实测结果

原镜像 `xingyaoww/sweb.eval.x86_64.iterative_s_dvc-9395`，摘要 `sha256:479c3af7…c0e`，与冻结值一致。实验方式为 root、断网、一次性容器；每个场景新建 git＋dvc 临时仓库，比较调用前后工作区与 `.dvc/cache` 的文件快照。

**（1）行为对照**（`repo.reproduce` API）

| 场景 | base | gold |
| --- | --- | --- |
| 缺数据源，本地 remote，`pull=True` | `ReproductionError`（缺陷复现） | 成功，取回 `foo` 并运行（修好） |
| 同上，`pull=True, dry=True` | `ReproductionError` | **取回 `foo` 与缓存到工作区**（dry 下有副作用） |
| run-cache 已推送、本地清空，`pull=True, dry=True` | 无文件变化（遵守 dry） | **下载 run-cache 条目**（dry 下有副作用，属回归） |
| 未配置 remote、无缺失，`pull=True` | 正常运行 `copy-foo` | **`NoRemoteError`**（回归） |
| 未配置 remote、无缺失，`pull=True, dry=True` | 正常 | **`NoRemoteError`**（回归） |
| run-cache 场景，`pull=True` | 正常恢复 | 正常恢复 |

**（2）私有 F2P/P2P 判分**

对 F2P 2 项、P2P 27 项所在的两个测试文件，应用 test_patch 后以 `pytest -rA` 运行，并逐 ID 对照参考名单。按 09-19 dvc_tail_v1 配方，pygit2 固定为 1.14.1：wheel 为 `pygit2-1.14.1-cp39-…manylinux2014_x86_64.whl`，sha256 `230493d4…dd93`，从 PyPI 下载。

| 候选 | 原测试 | 说明 |
| --- | --- | --- |
| base | 0 | 两个 F2P 都失败：缺 `bar`、`MissingDataSource` |
| gold | 1 | 与 09-19 正式评分一致（gold 1） |
| `alt_ds_only`：逐 stage 拉取只针对数据源 stage，流水线输出靠 run-cache 恢复 | **0** | 行为与 gold 相同（上表各场景），`test_restore_pull` 的其它断言都满足，**唯一失败**是 `assert mock_checkout.call_count == 3`（实际为 2） |
| `gold_guarded`：gold 加 dry 时不拉取、无 remote 时跳过 | 1 | 修好题面场景；dry 无副作用；无 remote 正常，与 base 一致 |

## 3．判定

- **T1（已确认）**：`checkout` 调用次数是内部实现细节。base 的公开旧测试写的是 `== 2`，隐藏版改成 gold 实现下的 `== 3`。按需拉取的合理实现结果相同（`bar` 恢复、命令未执行、`restore` 以 `pull=True` 调用一次），只因次数不同被判 0。
- **G1（已确认）**：gold 在 `--pull --dry`、未配置 remote 两条路径上有回归，公开测试不覆盖。这些组合不常见，按 §4 第 4 步判为“边缘路径”，登记 S2/T3，不阻塞。如第2类或 Codex 认为 dry 语义属于核心公开行为，可以补断言，并改用 `gold_guarded` 作正对照（D4）。
- 题面清楚，不需要 R-f。

## 4．修法（交第2类）

**R-b 修订草案 v1**：[`revised_test_v1.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/dvc9395/revised_test_v1.patch)，sha256 `d868cc6e…`；原 test_patch 为 `1252952e…`。

- 删除 `test_restore_pull` 中的 `mock_checkout.call_count` 计数断言，原 `== 2` 不再改成 `== 3`。
- 保留全部结果断言：`restore` 调用一次且带 `pull=True, dry=False`、命令未执行、`bar`、`foo`、`dvc.lock` 存在。
- 测试编号与参考名单不变。

私有复验结果：base 0，gold 1，`alt_ds_only` 1，`gold_guarded` 1。退化方向（运行命令而非恢复、什么都不拉）仍会被上述结果断言拒绝。

**交接给第2类**：

1. 在 dvc_tail_v1 配方的正式评分中复验上表；该配方需要一套完整的离线 wheel，云端无法完整重建；
2. 经 D6 测试补丁替换切片形成版本；
3. 登记 G1 为 S2；
4. Codex 复核。

## 5．当前用途

原版只作问题定位。T1 误拒会让合理实现得 0，所以不能进能力比较或训练分母。R-b 落地并验收后，重新评估是否转第1类。

## 6．未做与证据

- **没有正式评分**。dvc_tail_v1 配方用 `--find-links=/opt/rh2/compat-wheels` 离线安装 `.[all,tests]`，需要 09-19 构建的 compat-wheels 派生镜像，云端没有它的 wheel 清单。本页的 0/1 都是用同一组测试文件、同一份参考名单的私有模拟。计数断言是确定性的，与安装环境无关，但仍需正式复验。
- 真实 actor 开发条件未验；没有模型求解证据。
- 独立复核待做。
- 证据：[evidence/](evidence/)
  - `semantic_v1/`：行为对照
  - `refs_v1/`：原测试私有判分与四版本行为
  - `revised_v1/`：修订版私有判分
  - `evidence_manifest.json`

  补丁与脚本在 `rh2/experiments/category3_cloud_20260929/dvc9395/`。
