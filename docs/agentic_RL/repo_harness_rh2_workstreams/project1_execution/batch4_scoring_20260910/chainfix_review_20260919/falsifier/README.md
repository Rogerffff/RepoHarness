# 09-19 Falsifier / Simplifier 有界复核

结论：**R6 的原目录→文件/软链反例与 R7 的清理后诊断目标已闭合；保留一个新修复引入的 P2 窄余项：缓存规范化越过排除 namespace。** formal 缓存计数仍未写入持久 audit，是原非阻塞观测缺口；不升级为评分阻塞。安装 ERR trap 维持本轮实测 vendor 命令的控制语义，但不是完整安装命令账本，不能核销后置的 F4 构建归因。

本轮只使用本机临时树、真实 Bash/Git 与维护 FakeDocker。没有 SSH、Docker、GPU、模型/API 调用；没有改生产源码、维护测试、共享记录或旧 evidence。代码指纹见 [source_snapshot.json](source_snapshot.json)。所有新证据在本目录。

## F1 / P2：规范化会删除 `.git/`、`.harness/` 内同名目录

- **当前行为 / 文件：** `rh2/src/repoharness2/grading/manager.py:2543–2549` 只读取 `policy.regenerable_cache_dirs`，从整个 testbed 执行 `find … -type d … -exec rm -rf`；没有像 `baseline_census.py:59–68` 一样先剪掉 `policy.excluded_namespaces`。`manager.py:1682–1688` 已完成 baseline 重建核验后才执行这一删除。
- **违反的不变量：** 一致规范化应只删除该 manifest 政策实际省略的可再生目录。`.git/` 与 `.harness/` 在 census 中单独记 EXCL 路径、进入 `excluded_census_digest`；不是无身份的 cache。当前零改动 delta 也会在核验之后改变这一身份事实。
- **实证：** [probe_results.json](probe_results.json) 的 `namespace_boundary` 使用真实临时 Git 仓库，先 `git checkout -b __pycache__/probe`，再调用真实 `SWEGradingManager.grade`，仅容器生命周期/测试输出为 FakeDocker。census 与生产 normalization 均由真实 Bash 执行。规范化删除 `.git/refs/heads/__pycache__/probe`，真实 `git rev-parse --verify HEAD` 从 **rc=0 → rc=128**（`fatal: Needed a single revision`）；`.harness/__pycache__/private.json` 也消失。scoreable entries 不变，但 excluded digest 和整份 manifest digest 改变。软链、同名普通文件及 testbed 外 sentinel 均保留。
- **可达性 / 限定：** `production_reachable`，入口为 formal/replay → manager frozen-delta → baseline rebuild → normalization；policy v2 时无额外条件。HEAD 失效这个具体影响需要 `image_embedded` 树使用此类当前分支，本探针也使用该模式。`clone_from_readonly_snapshot` 在 `manager.py:2307–2311` 明确 `checkout --detach`，不能声称它删除 ref 后 HEAD 也失效；但排除区 ref/私有文件删除及 digest 改变仍是同一清理错误。没有证据表明当前 SWE 镜像包含这样的分支或已改变真实评分。
- **影响 / 建议分期：** 新步骤会修改其授权范围外的 Git/runtime 私有内容；具体出现频率未知，不升 P1 或扩为安全全审。建议在此规范化修复收口时做一处局部修改，属于本轮新回归例外。它不推翻已通过的普通 R6 重放，也不阻塞其它环境配方工作。
- **最小修法与实测：** 沿现有 `policy.excluded_namespaces` 在 `find` 前部 prune，然后保留现在的类型检查与删除；无新 owner、状态、retry、fallback 或拒绝分支。探针仅对临时树执行这个局部替代命令：合法 HEAD 和 `.harness` 内容保留、scoreable cache 仍被删除、整份 manifest digest 与原始 baseline 相同。命令及结果见 `namespace_boundary.local_alternative`；未修改生产代码。
- **复现：** 从仓库根执行下方独立探针；原脚本会断言当前错误仍存在，最后退出 0 表示观测被复现，不能解释为生产修复通过。
- **验收：** 同一 namespace 反例经生产 helper 后 HEAD/EXCL 内容与 digest 保留；8 组缓存类型/普通 file→dir 对照保持成功；v1 不执行规范化；软链不跟随。无需支持通用目录反向变换。

修复五问：旧 normalization 确在当前真实 manager 入口执行上述删除；prune 直接消除越界删除根因，而非转成 missing；新增状态/owner 数为 0；删除整个 normalization 会重新打开原 R6，fail-stop 会把可正常重放样本无谓拒绝；局部 prune 不改变 scoreable cache 的既定省略和训练准入语义。

## 已闭合项与边界

| 项 | 新证据与结论 |
| --- | --- |
| R6 原反例 | 真实临时树 + census/export/classifier/projection/manager + 真实重放 Shell：既有 `.pytest_cache/`→普通文件、`__pycache__/`→软链、嵌套 cache→文件均 resolved；原本不存在的同名文件、原本普通文件的修改、原本软链→普通文件均保留。v1/v2 普通 `config` 文件→目录都成功，共 8 组。 |
| 调用时机 | formal/replay 都归到 manager 的同一 frozen 路径，真实执行顺序为 `census → normalization → delta`；v1 没有 normalization。scoreable cache 本来不进 v2 身份，所以移除它们不要求二次生成 baseline；F1 则因排除区仍进入身份而破坏这一论证。这里不把“同一 manifest 基线”扩成“两棵物理树必须处处相同”。 |
| R7 | 普通、单引号、双引号、反斜杠路径，经真实正式编排拒绝 → receipt → workspace 清理 → 正式 `write_execution_audit_record` 的 flush/fsync → 磁盘 JSON 重读，均可恢复祖先/子路径及 add/delete、regular 类型，并仍为 `DROP_GROUP`、未评分。四份 [audit](conflict_audit_0.json) 与 [receipt](conflict_receipt_0.json) 按同一 `physical_attempt_id` 对齐。 |
| R7 的准确持久化位置 | `PatchExportError.conflict` 是结构化上下文；receipt 保存 child 与 prefix_conflict，完整双方操作在持久 execution audit 的 `unsafe_artifact_reasons`。§8.3 原要求为“在现有 audit/receipt 保留冲突路径、操作与原因”，现有做法已满足诊断目的。建议把实施记录 §10.1 的“receipt 沿既有字段持久化”改成准确的 audit/receipt 分工；不要求扩公共 receipt 字段。 |
| 旧 §14.2 三余项 | 本轮维护测试实跑通过：正常评分后 `eval_log_partial is None`；派生镜像 inspect 期间取消落 `cancelled:derived_image_inspect`；后观测期间取消仍引用已持久完整日志，`partial=False`。其中候选执行期间取消的部分日志路径也通过。 |
| formal 缓存计数 | **原非阻塞项仅部分完成。** 两次 `omitted_sink` 现在填入 `audit.omitted_cache_counts`；独立 formal 探针注入 census 计数 baseline=2/3、post=4/5，内存值完整，真实写盘 audit 没有该字段。`bringup.py:726–743` 仍未序列化它。grader 字段已明确为 fresh baseline 来源。最小后续处理是在现有 audit record 加这个诊断字段，或文档明确未持久化；不新增训练 gate。 |

R7 四组的 baseline/post 计数是刻意给维护 census 替身的固定值，用来验证运输，不是实际 SWE 目录计数。持久结果及局部 Git 反例都在 [probe_results.json](probe_results.json)；FakeDocker 的 resolved 仅证明控制链未拒绝，不能当成真实候选测试正确性证据。

## 安装 ERR trap：实测语义保持，观测有明确范围

从固定 registry 读取全部 **33 仓库、808 spec、33 种 install 字符串（含无 install）**，见 [vendor_install_inventory.json](vendor_install_inventory.json)。从真实 renderer 取出安装段，只将外部 `python/pip/bokeh/sed` 换成不联网叶命令替身；当前 DVC/Bokeh/Hydra 的 install 字符串原样交给 Bash。对照基线与新增 trap 后的叶命令顺序、文件字节及 `RH2_INSTALL_RC`，7 组均相同。

- DVC 的 `cython … && pyyaml …` 左侧失败、`pip … || true` 左侧失败都不产生 ERR 行。这不是逐条失败命令清单。
- DVC 无条件安装失败后又成功，记录一条 rc=7，但段末仍为 0；DVC 3.10 最末安装失败时，前后段末均为 7，trap 不吞退出码。
- Bokeh 的 `printf … | python setup.py develop` 末项失败，记录该 pipeline 的 ERR，后续 bokeh 成功后段末仍为 0。
- Hydra 的 `{ tail … | grep … && echo …; } >> requirements` 空尾行分支没有 ERR 行；新增 trap 没把诊断文字写进 requirements 文件，前后文件一致。
- 一个额外解释性对照覆盖 `set -E`：函数内失败可见；`(false)` 同时留下内部和外部事件；`false | true` 在 pipefail 下记录 rc=1，但 `BASH_COMMAND` 是末项 `true`。这表明“事件中的 cmd”未必就是失败叶命令。当前 vendor 没有该额外组合，不把它变成新的支持要求或 finding。
- 各组在段末 `trap - ERR; set +E` 后再次 `false` 都不产生安装错误行；当前脚本路径没有残留 ERR handler。没有验证或要求恢复任意外部预设 trap/errtrace 状态。

建议文档将“每条失败简单命令”收窄成“安装段观察到的 ERR 事件”；保留已登记的 F4：关键构建命令结果、产物生效与候选归因仍待后续切片。不要凭空构建通用 Shell 平台，也不根据 ERR 行新增评分/拒绝规则。

## 验证与停止条件

维护测试（在 `rh2/`）：

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/contracts/test_f2_2b_b2_exporter.py \
  tests/adapters/test_replay_grade.py \
  tests/adapters/test_w1b_prepared_task_face_v2.py \
  tests/grading/test_w3b_grader_profile_unit.py -m 'not docker'
```

结果：**87 passed in 9.62s**，见 [maintenance_tests.txt](maintenance_tests.txt)。不是全仓或 Docker 验证。

独立探针（仓库根）：

```sh
PYTHONDONTWRITEBYTECODE=1 rh2/.venv/bin/python \
  docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/batch4_scoring_20260910/chainfix_review_20260919/falsifier/probe_falsifier.py
```

结果：exit 0；8 组类型重放、4 组持久冲突、7 组安装语义对照，以及 namespace 原反例/最小局部替代均完成。见 [probe_stdout.txt](probe_stdout.txt)。

停止条件：F1 沿既有 namespace 政策剪枝并复跑对应反例与原 R6 控制组，即可收口本子审的代码边界；R7、原 R6 与三条旧余项不再重开。formal 计数及文档用语留作非阻塞记录；F4 构建归因和用户尚未决定的反作弊范围不借此扩大。主审继续承接 P-A、资格入口及真机对账，本子审不替这些范围作结论。
