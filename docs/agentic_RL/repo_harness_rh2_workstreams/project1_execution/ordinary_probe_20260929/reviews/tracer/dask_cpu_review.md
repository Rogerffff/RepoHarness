# Dask 6626 CPU 冒烟：Production Tracer 独立复核

日期：2026-09-29。范围限定为实际 `dask6626_v1` 的九个排除区路径差异，以及 CC 激活、工具执行、冻结导出和回放证据。只重读本地回传原件与 `code_v1`；未连接远端、调用 API、重跑 CC、执行候选、重评分或补做单元测试。

**结论：支持为本次 task、固定有序镜像对及已记录 sanitizer 版本登记这九条精确路径。没有发现无法解释的路径，也没有证据表明这是 A 的公共 census 修复新引入的缺陷。** 原运行仍应保留 `matrix_exit=4`、`roundtrip_mismatch`、`roundtrip.ok=false`；独立核对结果是新增的解释与运输验收证据，不能改写为“原运行通过”。本次阻断是既有 actor 清理与 fresh replay 初态之间的已拦截差异，无需升级为新的 P1/P2 缺陷或修改公共 policy。

**该例外仅适用于诊断探针的双侧对账。** 实际路径保留 actor 冻结物，再由宿主渲染文本 diff，交 fresh replay 应用并重新冻结。它没有让 `manager` 直接接收 actor 的 FrozenPatch，也没有修复该正式直评路径中因 `excluded_census_digest` 不同而拒绝的身份问题。后者由对应正式链审查追踪，本报告不核销它。

独立只读脚本与结果：[reconcile_dask_cpu.py](../../../../../../../runs/ordinary_probe_20260929/reviews/tracer/reconcile_dask_cpu.py)、[dask_cpu_reconciliation.json](../../../../../../../runs/ordinary_probe_20260929/reviews/tracer/dask_cpu_reconciliation.json)。22 个证据条件全部成立；这是重算和核对已存在的工件，不是 22 次新运行。

## 1. 真实入口与固定身份

运行：`bp29-97286d2c-stub-dask-6626-a1`，task 为 `swe_gym_lite::dask__dask-6626`。本次 attempt 记录的入口文件摘要与归档 `code_v1` 的 `solve_attempt.py` 完全一致。

| 身份 | 实际值 |
|---|---|
| actor 镜像 | `sha256:a1f28fbc69f233d1beefe1f35e80ad9e3d89199dc22edd6ee9e4aed5b8762dc8` |
| replay/grader 镜像 | `sha256:d3befac6fecbe5083e73cc4373856737f828d457c1b9ea1de3043d63dce1c523` |
| 两派生镜像共同 base ID | `sha256:fd456e2bd2f9452fa48023395f847397998d2309e55258b3f00b957eb40c6ed5` |
| 共同源镜像 repo digest | `xingyaoww/sweb.eval.x86_64.dask_s_dask-6626@sha256:a182a6a7383561f7b7a078585259c6314e60504235b4d86cf00f4fd15ef69503` |
| 本次 sanitizer 源码摘要 | `sha256:5adce65d22a0bb056f4834d4ce94b8f79222a087e70f8d7fef2a4194bc9afb1b`（整个 `sandbox_profile.py`） |

两个 `image.json` 与构建 Dockerfile 证明同源及 `base_layers_preserved=true`。actor 派生层离线安装 `pytest==7.4.4`；grader 派生层仅复制兼容 wheels。两者没有通过派生配方改 `/testbed`。不能仅凭镜像 tag 同名推断同源，本结论使用实际 image ID、base ID 和构建原件。

actor 实际顺序是 `sanitize_and_init` → prep/物化 → baseline census 与基线归档 → CC → 网关撤销/排空 → 公共冻结屏障与 exporter → 宿主补丁渲染。`code_v1` 的 [`sandbox_profile.git_sanitize_script`](../../../../../../../runs/ordinary_probe_20260929/code_v1/rh2/src/repoharness2/adapters/slime/sandbox_profile.py) 在模型前删除 refs、logs 和指定 Git 状态文件，再执行 `git repack -a -d -q` 与 prune。fresh replay 的 [`_candidate_stage`](../../../../../../../runs/ordinary_probe_20260929/code_v1/rh2/src/repoharness2/adapters/slime/replay_grade.py) 在 trusted init、materialize 后直接 census，未执行相同 sanitizer；之后才以 agent UID 应用候选。该不对称是九个差异的实际来源。

## 2. 九条路径的逐条归因

actor raw EXCL 有 24 条、replay 有 25 条，精确差集为 actor-only 4 条、replay-only 5 条。下表方向来自双侧原始 census，未使用“所有 `.git/**` 均忽略”的规则。

| 仅出现于 | 精确路径 | 归因与证据强度 |
|---|---|---|
| actor | `.git/info/refs` | `git repack` 未加 `-n`，默认更新 server info；与下一条共同出现。源码操作归因。 |
| actor | `.git/objects/info/packs` | 同上，为 repack 更新的 pack 列表。源码操作归因。 |
| actor | `.git/objects/pack/pack-c0f0b7d15cedc10cd8ef990fb8da13e06083bfd0.idx` | 清除 200 个 refs 后 `repack -a -d` 产生的新 pack 索引。源码操作与成对路径归因。 |
| actor | `.git/objects/pack/pack-c0f0b7d15cedc10cd8ef990fb8da13e06083bfd0.pack` | 与上一条配对的新 pack。源码操作与成对路径归因。 |
| replay | `.git/ORIG_HEAD` | sanitizer 的 `rm -rf` 明确删除此文件；replay 未执行 sanitizer。直接源码证据。 |
| replay | `.git/logs/HEAD` | sanitizer 明确删除整个 `.git/logs`。直接源码证据。 |
| replay | `.git/logs/refs/heads/main` | sanitizer 明确删除整个 `.git/logs`。直接源码证据。 |
| replay | `.git/objects/pack/pack-72547b22db4b67a12b5ac44a7a71ad4a5b59ba43.idx` | 共同源镜像的旧 pack 索引；actor 的 `repack -a -d` 替换旧包。源码操作与成对路径归因。 |
| replay | `.git/objects/pack/pack-72547b22db4b67a12b5ac44a7a71ad4a5b59ba43.pack` | 与上一条配对的旧 pack。源码操作与成对路径归因。 |

实际 actor 的 `sanitize_and_init` 成功：HEAD 前后均为 `56cd4597630feb1b01501c16d52aa862dd257a83`，history 前后均为 6097；删除 refs 200 条，剩余 103 条，remote/reflog/unreachable 均为 0。sanitize 在 `08:27:39.383764Z` 完成，baseline census 在 `08:27:41.490450Z` 完成，网关首个模型请求为 `08:28:02.261Z`。因此这里比较的是模型前的初态差异，候选执行没有造成这些 baseline 差异。

**证据限度：** raw EXCL 只记录排除路径名，没有保存这些 pack 的字节或对象清单。可以依据实际预处理成功记录、共同源镜像及上述具体操作归因九个路径；不能声称独立证明了新旧 pack 对象等价，也不能认为新 pack 名在其他 Git 版本/镜像中必然相同。新出现的 pack 文件名必须重新核对，不能用通配符自动放行。

## 3. 工作树、冻结物和运输的独立核对

双侧 414 个 baseline entries 逐项完全相等，包括 path、type、mode、内容/软链摘要。actor `baseline.tar` 为 7,720,960 字节；本轮未解包，仅逐成员读取并独立核对 414 个归档成员的类型、执行位和原始字节摘要，无重复或额外成员。

双侧完整 baseline manifest **并不相同**：差异仅为已声明的 `runtime_image_digest` 与 `excluded_census_digest`。两个 raw EXCL 摘要分别重新计算为：

- actor：`sha256:10d208ea081419ec222f45682014bd9168085bcf418d7541a18c14159b8c00ea`
- replay：`sha256:f9e8e0153745dd87329bc4875b4ee6be7e314093df171fb6a197f11e8919f8c1`

两者分别与各自 manifest 一致；不能在 reconciliation 中替换成同一个摘要。`identity_equal.image_ids=true` 表示符合配置中的有序镜像对，不表示两张镜像 ID 相同。

双侧 frozen patch 的 entries（含 inline 字节）完全相等，各自绑定自身 baseline digest；完整 artifact digest 因身份/谱系不同而不同。本次候选只有新增普通文件 `rh2_probe_transport.py`，mode `100644`，原始内容 `CHECK = 1\n`，内容摘要 `sha256:857df28f3a55130652fc96fdee50fcb0cc9304ba97e3939738ff92bdcb0258fb`。两侧 `excluded_pathset_changed=false`。

实际 239 字节 diff 的 SHA 为 `sha256:4297514b0325a9985be7a5cae9a3a17285c13f2b705178e3114906a3ac1ad694`，与 attempt、grader ledger 一致，回放实际 `candidate.patch` 字节也完全相等。宿主 renderer 自检成功。因候选只有 add，`baseline_paths_fetched=0`；这次真实冒烟不能替代 dirty/prep 后旧字节修改、binary/mode/symlink 等之前核心测试的覆盖。

## 4. CC 激活、工具和收口事实

真实 Claude Code 版本为 `2.1.205`，harness 退出 0，轨迹完整、无 stderr；两轮对话，一次 Bash 调用，工具错误数为 0。初始化与首个模型请求的工具集均为 `Bash / Edit / NotebookEdit / Read / Write`，无 MCP 工具。以 `prompt.txt` 原始字节解码比较，完整 prompt 确实进入首请求；不能用会归一化 CRLF 的读法替代该比较。

激活和实际 Bash 回执均为 `uid=54321(agent)`、cwd `/testbed`、Python `/opt/miniconda3/envs/testbed/bin/python`；环境记录含 `CONDA_DEFAULT_ENV=testbed`、`BASH_ENV=/rh2/bash_env`。两个 miniconda 前缀对 agent 不可写，工作树/home/tmp 可写。Bash 实际完成身份/目录/Python 检查并写出该新增文件，回执 `is_error=false`。

此轮模型是 scripted `slime-actor` stub，网关两次均 HTTP 200 且完整 SSE，无 stream error；最后回复明确没有尝试修复 Dask。它证明真实 CC 与运输接线可执行，不是 DeepSeek 能力评测。summary 记录 `paid_api=false`，不将轨迹中的模拟计费字段记成真实 API 支出。

网关 `session_close` 与 attempt 的 drain 记录完全一致：`revoked=true`、`active_requests=0`、`drained=true`。停止 agent 进程后的 residual 为 0，屏障双次 census 稳定，消费 `baseline_policy_v2`。solve 的容器/网络清理 `cleanup_ok=true`，grader 候选容器 `removed=true`。

grader driver 退出 0、ledger 无 stage error，最终 reward 0、`tests_failed / unresolved`，F2P 为 0/1、P2P 失败为 0/14，符合该候选没有修题的事实。trusted setup 约 479 秒，测试约 8.7 秒；独立核对没有发现需要重复此评分的证据。

## 5. 最小处理与停止条件

建议仅修改本批 Dask 条目的诊断 roundtrip 兼容登记：绑定 task、上表有序 immutable 镜像对及 `code_v1` sanitizer 身份，登记九个**精确**路径；保留基线 entries、政策、HEAD/身份、冻结 patch entries、实际 diff SHA 和清理等现有核对。独立证据另记录 actor-only/replay-only 方向和两侧 raw digest，不改公共 policy，不放宽其他任务、镜像或排除路径，不把该登记接入正式 `manager` 的 baseline 身份校验。

原 `roundtrip.json`、STOP、退出 4 和原日志应保持原件；后续以单独 reconciliation 说明固定差异被接受。当前原 checker 正确停止了派发，没有把 0 分或运输不一致伪装成成功。该处理仅核销这次固定初态的运输差异，不核销初轮报告中其他尚未集成验收的发现。

在固定范围内，本项复核可以结束，无需重复 CC 或十分钟评分。出现以下任一事实则停止继续派发并重新核对：镜像/源码身份改变、额外路径或方向改变、raw digest 与原件不符、baseline/patch 内容不符、diff 字节不符、网关未排空或清理不明。这里未新增全局长期准入机制。

原件入口：[CPU run](../../../../../../../runs/ordinary_probe_20260929/remote/cpu_smoke/dask6626_v1/)、[actor attempt](../../../../../../../runs/ordinary_probe_20260929/remote/cpu_smoke/dask6626_v1/attempts/dask__dask-6626/stub/a1/attempt.json)、[原始 roundtrip 失败](../../../../../../../runs/ordinary_probe_20260929/remote/cpu_smoke/dask6626_v1/attempts/dask__dask-6626/stub/a1/grading/roundtrip.json)、[镜像构建原件](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/dask__dask-6626/followups_v1/)。逐文件 SHA 已保存在独立 reconciliation JSON。
