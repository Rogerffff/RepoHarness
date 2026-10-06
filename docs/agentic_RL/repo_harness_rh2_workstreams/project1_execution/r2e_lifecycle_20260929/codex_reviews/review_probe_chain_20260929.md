## 结论：**改后可以**

CPU 证据基本成立，但**当前版本不能直接接真实模型**：必须先关闭 root Git 执行面，并落实往返校验、评分停批和清理失败的传播。正式冻结补丁直评问题可以登记后递延，明天仅走回放路径。

本轮仅本地只读；未修改文件、运行容器或连接远端。已重算补丁摘要、比较原始产物，并用全部 I/O 替换为内存桩的方式核验停跑逻辑。

## 按严重度列问题

### 1. P1：root Git 是明天前必修的安全问题，不能只交 A 线排期

**`production_reachable`，已有非正式 profile 下的 uid=0 实证。**

屏障在杀净 agent 进程后，以 root 执行仓库内的 `git status/diff`：[quiescence_barrier.py:58](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/quiescence_barrier.py:58)、[generate.py:2441](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/generate.py:2441)。

正式 profile **不会阻断它**：

- `.git` 随工作树交给 agent；system 配置还设置了 `safe.directory=*`。
- root 保留 `DAC_OVERRIDE` 等能力；`no-new-privileges` 不会把已经是 root 的子进程降权。见 [sandbox_profile.py:1236](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/sandbox_profile.py:1236)、[能力配置:136](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/sandbox_profile.py:136)。

后果包括读取本容器的 root 私有隐藏测试、在“agent 已归零”之后产生 root 写者；**没有证据证明宿主逃逸**。

**两开关修法不完整：**

- `--no-ext-diff` 不关闭 `textconv`。
- 工作树内容比较仍可能调用 `filter.*.clean/process`。
- `core.hooksPath` 还须考虑 index 刷新触发的 hook；不能只检查 commit hooks。
- `include.path` 本身不执行程序，但能引入上述配置；`safe.directory` 是信任许可，不是执行隔离。
- `smudge` 主要属于写回工作树的转换，不应冒称本次 status/diff 已实证触发。
- 实证 Git 为 **2.34.1**，其 `core.fsmonitor=false` 不能直接按新版“布尔禁用”理解；旧版本可能把它当 hook 路径。[本机 Git 文档](/Library/Developer/CommandLineTools/usr/share/man/man1/git-config.1:3264)

**建议与验收：** 删除这个阶段对 agent 仓库的 Git 调用，保留终止／双读流程，使用可信工具、no-follow、沿现有 census 政策的内容指纹；不能只降为 agent 后重新运行可产生后台进程的 Git。正式 profile 下验证植入配置不执行、ignored `.so`／mode／软链变化可检出，再复验普通题和编译题。真实模型禁止打开 `--legacy-gitdiff-compare`。

### 2. P1：D2/D4 的“不一致即停”尚未实现，D1 不只是换入口

[r2e_probe_e2e.py:455](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/r2e_lifecycle_20260929/r2e_probe_e2e.py:455) 只记录 roundtrip；`:474` 只根据残留决定退出码，重评分支同样如此。

**内存替身核验：** 设置 `entries_equal=False`、补丁摘要不等、评分进程退出 **4**，只要 `_clean=True`，实际 `E2E.main()` 仍返回 **0**。

共用派发器也只把**求解侧**清理失败转成 STOP；评分端退出码只返回到结果，连续 infra 计数在评分前就重置：[run_matrix.py:138](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/base_probe_20260922/run_matrix.py:138)、[评分返回:192](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/base_probe_20260922/run_matrix.py:192)。

**明天前补齐：** 缺失／不等的往返证据不得采信分数；评分 fatal、清理未知必须停止新派发。注入这些失败后，验收退出码、STOP 和下一任务未启动。已有成功样例不受此 finding 否定。

### 3. P1：正式直评基线问题成立；影响范围和修法需要收窄

aiohttp 两侧 **124 条基线 entry 完全相同，唯一不同字段是 `excluded_census_digest`**；sanitize 前后路径清单唯一删除 `.git/logs/HEAD`，摘要与直评错误吻合。[直接评分证据:20](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_lifecycle_20260929/probe_proto/runs/aiohttp_618335_small_edit/grade_direct/result.json:20)

正式链会将其升级为 run-halt，文档对此描述准确：[generate.py:5515](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/generate.py:5515)。但不能外推成所有 R2E／SWE 镜像必然首评停批。

**D6 漏了一个迁移条件：** 若只给 grader 加 sanitize，当前未 sanitize 的回放候选基线反而会失配。修复必须同步 **rollout、回放候选、grader** 的初始化顺序；不能仅修改 [replay_grade.py:334](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/replay_grade.py:334) 之外的一侧。

可递延至正式直评启用前。验收须直接消费原求解侧冻结产物，不得用回放重建基线替代；真正的内容／身份不一致仍须 fatal。移除 `.git` 摘要比较确实属于契约变更，不能顺手绕过。

## 求解入口与端到端证据

**入口基本正确。** 覆盖表与任务面绑定、按 image ID 启动、census 后以 agent 做预检，随后调用正式 `export_frozen_patch` 和分类器，顺序正确。[r2e_solve_attempt.py:279](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/r2e_lifecycle_20260929/r2e_solve_attempt.py:279)、[冻结导出:520](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/r2e_lifecycle_20260929/r2e_solve_attempt.py:520)

需要准确区分交付层次：

- `.gitignore` 不参与 census 排除，orange3 两个 `.so`、`.c`、`.o` 确实被导出。
- `.git/`、`.harness/`、`.venv/` 及政策指定的两类缓存目录被排除；`build/*.o` **不是该政策认定应排除的缓存**。[baseline_manifest.py:122](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/contracts/baseline_manifest.py:122)
- 原始冻结补丁不保证完全没有控制面改动：official 测试／入口由评分投影剔除，隐藏测试目录另被可信 setup 整体恢复。这与正式语义一致，不能混称“原始导出已全部过滤”。[r2e_grading_scripts.py:79](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/r2e_grading_scripts.py:79)

| 核验项 | 判断 |
|---|---|
| aiohttp 6183 | 支持结论：3 条冻结 entry 与回放完全一致，候选及 noop 都是 0、45/47；**不是整个 manifest 摘要相等**。[证据:536](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_lifecycle_20260929/probe_proto/runs/aiohttp_618335_small_edit/summary.json:536) |
| orange3 4014 | 支持这道题的新构建产物生效：两候选 `.pyx` 字节相同，build 多出的只有构建产物，新 `.so` 摘要 `f1d05c0f…` 往返一致；评分确为 **1／0／gold 1／noop 0**，只翻转同一个失败键。 |
| “grader 加载新产物” | **构成有力的配对因果证据**，不只是四个分数；但 grader 内没有直接记录扩展的 `__file__`＋摘要，因此不是精确加载路径的直接观测。gold 本身也不是加载该扩展的证明。 |
| 预算包装 | 只替换 `env_reset_timeout_seconds`，未改补丁、投影、测试脚本、解析器或计分规则。[包装:34](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/experiments/r2e_lifecycle_20260929/replay_grade_budget.py:34) 但它同时放宽 checkout、census、可信 setup、控制面保护和前后观测，不只是 `chown`；候选阶段 1800 秒是另一项参数。 |

## D1–D6 的补充条件与停止线

| 项目 | 明天前必须落实／可递延 |
|---|---|
| **D1** | 接入口和覆盖表之外，还要接完整性校验、评分停批；固定题包／覆盖表／代码版本，只选当前题卡允许用途的题，使用新输出目录避免复用旧结果。 |
| **D2** | 比较评分树 entry、内容、mode 和任务／镜像／policy 身份。已知 sanitize 排除区差异单列，不能要求当前整体摘要相等，也不能因此放过其它差异。 |
| **D3** | 在目标机测通大环境题并明确传入预算；仅“降低并发”不能保证低于 300 秒。超时保持 `reward=None`，不算模型失败或悄悄移出统计分母。 |
| **D4** | 降并发只适用于已定位的资源／耗时问题；契约、安全、清理未知必须停。 |
| **D5** | 搬运后核对 **tag→ID**，不只核 ID——回放先 inspect 覆盖表中的 tag。资格也不会自动生效：当前原型未传 `--qualification-ledger`，账本为 `absent`；部分模型语法错误因此会落入未归因 infra，能力统计前应补接或明确单列。[资格判定:3745](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/grading/manager.py:3745) |
| **D6** | root Git **现在修**；正式直评基线修复、正式 generate 的 R2E 预检接入可登记至正式链启用前，不挡已修安全边界的原型回放探针。 |

**停止条件：** 安全修复和失败传播验收通过、目标机普通题＋编译题小规模冒烟通过，即可扩大明天的探针；无需等待正式直评修复或全题池性能优化。这不是正式训练放行。