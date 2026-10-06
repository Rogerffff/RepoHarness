# Git初始化表示确定性：非作者复核

2026-10-03。实现者为总协调指派的`git_init_determinism`，本记录由总协调独立复核。结论：**窄修已进入GPU冻结版本code_v3，并通过Moto/SWE与NumPy/R2E两来源真实非空工件的完整往返验收。旧FrozenPatch不可改绑；此结论不等于所有题目或候选语义通过。**

GPU执行线程报告两种实际Moto镜像各两轮完整初态一致。新运行`gpu1003-moto5134-coder-a3`于2026-10-03 01:50（新加坡时间）完成评分；总协调已直接回读`result.json`、`grading/status.json`、`report.json`与`projection.json`：`source=original_frozen_patch`、`baseline_rebuild_passed=true`、reward=1、2/2 F2P及12/12 P2P通过，评分管理器自有容器1建1清，`cleanup_ok=true`。执行线程随后通过CPU检查确认候选混合字符串与exists列表的语义回归，已按其原题目归属开始窄修订，不修改原评分，也不归因于Git修复。

R2E运行`gpu1002-numpy18b7-coder-a1`于同日01:53完成。总协调直接回读其`result.json`和`grading/status.json`，确认同为`source=original_frozen_patch`、`baseline_rebuild_passed=true`，正式10/11、reward=0、`failure_category=tests_failed`，无基础设施失败，评分容器1建1清、`cleanup_ok=true`。执行线程报告公开自测与正式评分在同一`p!=None`断言失败；其非作者核查覆盖Moto35项与NumPy36项，255份远端/本地原件SHA一致。总协调本次复核的是已回收结果文件，不声称自己重跑了两次模型求解或全部清单核验。

本次GPU原件：`runs/ordinary_gpu_probe_20261002/remote/queue_v4/results/`内的`gpu1003-moto5134-coder-a3/`与`gpu1002-numpy18b7-coder-a1/`。原Moto a2工件保留，两个新运行均使用各自baseline与FrozenPatch；部署身份见[GPU部署记录](gpu_deployment_20261002.md)。

## 范围与证据

复核了共享函数、两份生成脚本、新测试的精确diff，以及参数矩阵、双容器原件、作者测试日志和边界说明。生产变化仅为`git repack -a -d -q -F --threads=1`和解释注释；保留可达对象选择、prune/fsck与失败拒绝，不改评分、manifest、excluded比对或技术超时。两份生成脚本只同步该参数。

独立重算4个实施文件及176个证据文件的大小/SHA，均匹配作者清单。直接读取六份真实完整manifest并逐对象比较，actor继承镜像ENV、grader经env-i各三轮完全一致；各自1613个评分条目均等于原输入，六次未来对象canary检查返回0，收尾无自有容器。当前生成sanitize快照与实际验收脚本逐字节相同。未重新执行作者已完成的18轮参数实验或完整测试套件。

六臂对照否定仅固定线程数或仅禁对象复用的修法；Moto中的`-f --threads=1`虽稳定，但跨预压缩级别的公开构造仓库仍不收敛，因此`-F`有额外实证依据。新测试在旧源码先失败于表示收敛断言，修后与原有隔离/调用顺序/失败清理测试合计59项通过；Ruff和限定路径diff检查通过。旧快照未同步时的失败日志保留，最终结果使用`tests_final.log`。

## 成本与剩余边界

本次Moto重复sanitize约从12.5秒增至23秒，既有600秒超时未变。这是固定镜像、Git2.34.1、2CPU/4GiB下的结果，不保证所有仓库、Git/zlib版本或Git配置组合均有相同pack字节。对象集合与评分文件不变，旧版与新版的完整基线身份仍可能不同。

统一探针线程已完成上述新宿主/冻结字节检查和两来源非空工件直评。后续题目复用共同修复及已完成参数实验，不机械重复18轮。旧候选、原基线和原attempt保留；若需要在新版本验证旧补丁，应形成明确区分的验证记录，不能把新基线改绑为旧FrozenPatch的原始身份。CPU第五版已精确包含该修复，已有作业不热换。

## 复核绑定

| 文件 | SHA256 |
| --- | --- |
| `rh2/src/repoharness2/adapters/slime/sandbox_profile.py` | `313bfd7691c5dca775aa0e9992f13561e20936f062ddfa3d269892b6bf4895ee` |
| `rh2/scripts/sandbox_probes/git-sanitize.sh` | `46c627f7924277715f0cc4bc8477d6ae91d769f887035a42a99562e81dece125` |
| `rh2/scripts/sandbox_probes/git-future-probe.sh` | `dc85cd9f0f7837b34aa8e38196be049652ee54c1debd0293844bf464a020a20b` |
| `rh2/tests/adapters/test_git_sanitize_determinism.py` | `0b1b574dd2c7679cff6afd58f2ce6b94248b5f43b0439396eec695e298cfbb31` |

原件：`runs/category2_repair_20260929/git_init_determinism_20261003/`内的`HANDOFF.md`、`implementation.diff`、`implementation_files.json`、`evidence_manifest.json`、`matrix_v1/`、`acceptance_v1/`和`tests_final.log`。原故障入口见[诊断交接](git_pack_baseline_handoff_20261003.md)。这些记录不含机器凭据。
