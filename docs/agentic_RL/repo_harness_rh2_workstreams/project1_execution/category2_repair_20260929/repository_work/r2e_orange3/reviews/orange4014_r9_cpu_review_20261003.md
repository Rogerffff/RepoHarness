# Orange4014：R9 CPU 实测独立审查（2026-10-03）

当前固定 R9 / r2e-mr-089 的题级诊断 CPU 验收可以封存。八方矩阵与实际 CC v2 的构建、冻结、运输、新 grader 评分链已独立核完，未发现本轮必修问题。结论只支持后续 probe 申请；GPU 未准入或派发，没有本题真实模型成绩，也不审训练资格。

本轮只读本地回收原件，新增本报告及同名 JSON。复用已封公开 brief、材料和静态/fresh 审查，没有重跑 CPU、候选、模型或共用 101 检查，没有修改总账、公用代码、候选或旧报告。

## 原件与固定入口

独立重算矩阵 235 份、实际 CC v2 91 份、启动前失败 v1 12 份原件的大小与 SHA；各回收 request、archive、manifest 与 receipt 全部一致。作者核对仅用于找原件，结论来自 ledger、完整 raw eval、CLI footer、trajectory、原生工件、实际 baseline.tar 和资源快照。

[矩阵原件 manifest](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_4014_matrix_complete_v1/readback_manifest.json)；[CC v2 原件 manifest](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_4014_actor_complete_v2/readback_manifest.json)；[结构化审查与逐方索引](orange4014_r9_cpu_review_20261003.json).

固定镜像 `3307167745d3…`、配方 `9cd596e8a724…`、base commit `9403704f5b98…` 与冻结公开 bundle `dc1d8fda79cd…` 一致。实际 command 使用 R9 `ordinary_probe_20260929/replay_probe.py`，与既已审 wrapper SHA `6b6276342528…` 相同；config 只有 `setup_seconds:1200`。各方 audit 的实际准备预算从 300 改为 1200 秒，测试预算 1800 秒，结果报告未改写。准备预算不是模型求解时限。

## 八方完整结果

| 控制 | 正式 reward | reference match | 原始结果 |
| --- | ---: | ---: | --- |
| noop | 0 | 26/27 | 原首次 low<high；test_1.py:55 |
| gold | 1 | 27/27 | 27 键全通过 |
| C1 | 1 | 27/27 | 不同位置合理去重；27 键全通过 |
| DG | 0 | 26/27 | 原非退化断言；test_1.py:80 |
| C3 | 0 | 26/27 | 新增小量级分区；test_1.py:90、75/100 错 |
| C4 | 0 | 26/27 | 原第二分支 low<high；test_1.py:64 |
| pyx_build | 1 | 27/27 | 包含重编产物；27 键全通过 |
| pyx_only | 0 | 26/27 | 仅改源码未生效；test_1.py:55 |

独立从每份 `Start Test Output` 到 `End Test Output` 抽取全部状态，与 SHA `07f34ad40f87…` 的固定 expected map 逐键比较：每方恰为 27 键，无缺键、额外键、跳过或段外测试；五个负例仅 `TestEqualFreq.test_below_precision` 失败，其余 26 键通过。三种合理修法通过，保留不同实现位置与 Cython 修法的宽容性。

C3 的完整 traceback 先显示原近邻两分支去重与混合值非退化断言，随后才在 `test_1.py:90` 比较 `1e-12` 量级的 100 个值与四组各 25 个 bin。实际显示 bin 1，75/100 不匹配。这是舍入破坏小量级等频分区；不能只写“重复切点被拒绝”。DG 在原 `:80` 非退化保护失败，C4 在原 `:64` 的 `n=8<10` 分支违反 native `low<high`，noop 和 pyx_only 在原 `:55` 首次分支同样失败。均为完整目标断言失败，未发现安装、超时、加载异常替代失败。

七个补丁均与固定计划及输入 SHA 一致，成功 `git_apply`，无测试/fixture/conftest 改动；noop 为空 delta。逐方 baseline / FrozenPatch canonical digest 与 projection 一致，decoded 内容 digest 重算一致；六个文本补丁在内存逐 hunk 验证与原 baseline 上下文及 frozen 字节一致。历史 pyx_build 与 pyx_only 的改后 `.pyx` 同为 `2da1103793b4…`，前者额外含 C、两份 `.so`、`.o`。这组成对结果说明本次已冻结产物生效，但矩阵本身不替代真实重编。

所有 test segment 完整。wrapper exec exit 均为 0，内部 pytest rc 为负例 1、正例 0；各方 driver 0、stop_reason null。candidate ledger 均 `removed:true / rm:ok`；各 grader CLI footer 单独确认 created/removed=1/1、open/supply/cleanup_failures 空。远端矩阵 job 正常结束 0；没有把测试失败、进程退出和运输回收混成同一结果。

## 实际 CC v2：真实构建与新 grader

[完整 trajectory](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_4014_actor_complete_v2/actor/attempt/trajectory.jsonl)；[完整新 grader 日志](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_4014_actor_complete_v2/actor/grade_cc/eval_logs/evallog_replay-orange-4014f248-r_41e05082.eval.log)；[原生冻结工件](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_4014_actor_complete_v2/actor/attempt/frozen/frozen_patch.json).

v1 的禁用 `legacy_gitdiff_compare` 在 argparse 处被 R9 拒绝，未启动 CC、候选或评分，observer 0 样本；job 1 与原摘要 `solve_cleanup_not_confirmed` 保留。这不是任务测试失败，也不是实际容器残留证据。v2 仅移除该选项；六项步骤内容逐字相同，场景名称及迁移说明/来源 SHA 相应更新。

v2 实际 `stub_script` CC 2.1.205 以 uid 54321 在 `/testbed/.venv` 完成六次 Bash、六份完整结果，job 0、ran/completed、harness exit 0。没有 trusted root exec rewrite，pip freeze 不变。决定性证据为：

- trajectory 第 19 行（`toolu_587f28168412d186`）给出构建前磁盘 `.so` SHA `9ee458d033a2…`。
- 第 28 行确认 `.pyx` 编辑；第 39 行（`toolu_a58b89a90bb4a0fe`）完整输出 Cythonizing、cc 编译、link、inplace copy，`BUILD_RC=0`、`is_error=false`。build 显式 `exit "$orange_build_rc"`，外层后置 `RH2_STEP_RC:build` 不执行是预期，不能据缺 marker 判结果丢失。
- 第 48 行（`toolu_e31912c04ccb65ac`）给出新 `.so` SHA `f1d05c0f51a1…` 与实际 `RH2_EXT=/testbed/Orange/preprocess/_discretize.cpython-37m-x86_64-linux-gnu.so`。这里证明 actor 的新扩展来源。
- 第 57 行（`toolu_fae89c0151e70aa7`）实际 m=4/m=5 均为 list、unique=True、increasing=True。脚本会捕获 AssertionError 后继续，因此只读 repro rc0 不足；本轮核的是完整输出。

独立只读实际 pre-solver `baseline.tar`：1594 项内容及 Git 规范化模式全部与 baseline manifest 一致。原生冻结五项 decoded digest 与 grader 及矩阵 pyx_build 一致；运输 patch 共 909261 字节、SHA `372f4982da9d…`。在内存逐项核两个文本 hunk、三份二进制 forward/reverse literal、Git blob ID 与旧 baseline，结果逐字等于 native FrozenPatch。没有执行补丁或候选。

actor / grader baseline manifests、原 census 均一致。原生 FrozenPatch 的 excluded_pathset_changed=true，而 replay=false，不能写成“两边都 false”；原 census 排除证据无路径差异，roundtrip 允许该状态差异，实体 entries 与运输 digest 全等，projection 没有忽略任何本次五项改动。

导出后从相同固定镜像创建新 candidate / grader，在正式原有入口完整取得 27/27、reward 1、pytest rc0；log SHA `690799718708…` 与 ledger 一致，实际预算仍 1200/1800。solve cleanup、gateway drain、端点 stopped rc、grader footer 与残留检查分别完结：active_requests=0、containers/networks 空，没有 cleanup failure。

加载结论有明确边界：矩阵和实际 CC 的新 grader 观测只有 `Orange/__init__.py`、包版本与 runner SHA，没有直接快照 grader 进程中的 `_discretize.__file__` / SHA。本报告以 actor 实际构建/加载路径、native 字节导出与运输往返、同镜像 fresh grader 正式通过、pyx_only 成对失败共同支持构建产物生效；不会改写成 grader 扩展 SHA 已直接实测。该证据组合足够封本轮开发/构建/评分诊断验收。

## 实际资源与清理边界

矩阵 118 个有限快照覆盖 16 个 candidate / grader 容器，所有八方都覆盖两种角色。原 HostConfig 均为 2CPU、4GiB、pids512、memoryswap=memory、network none、无 bind；可读 cgroup 均 `cpu.max=200000 100000`、`memory.max=4294967296`、`memory.swap.max=0`、`pids.max=512`。ledger.resource_facts 仍 null，不能把 policy 声明当实测。

| 控制 | candidate 样本 | grader 样本 |
| --- | ---: | ---: |
| noop | 3 | 7 |
| gold | 7 | 7 |
| C1 | 7 | 8 |
| DG | 8 | 7 |
| C3 | 7 | 8 |
| C4 | 9 | 8 |
| pyx_build | 8 | 8 |
| pyx_only | 8 | 8 |

C4 有两次应保留的删除状态：candidate 在 `21:54:46.522238Z`，grader 在 `21:56:47.351008Z` 为 removing、exit137、Pid0、OOMKilled=false，cgroup unavailable。candidate 删除后才创建 grader；grader 在完整测试结束 `21:56:44.167347Z` 后删除。137 与清理时间相符，未替代目标断言结果，但采样不能证明全程 OOM0，也不能把该 137 直接叫作测试 OOM。清理结论取自 ledger 与 CLI footer；observer receipt 明确不承诺评分或清理。

CC v2 25 个快照覆盖四个容器：main10、relay11、replay candidate7、grader7。主容器与后续 candidate/grader 是实际 2CPU/4GiB/512/swap0；relay 是 256MiB/64/swap0、cpu.max=max100000、无2CPU配额。actor main 使用专用网络，relay bridge，后续评分两容器 network none。有限样本未见 OOMKilled=true；不扩展成全时资源证明。完整时间、容器 ID、峰值和原快照索引见 JSON。

## 公开交付与当前用途

首 HTTP request 与实际 `prompt.txt` 逐字相等：原 ISSUE SHA `efdb68c7ab45…`，全 prompt 含 repo/commit 前缀 SHA `df2b684d5c3c…`，与冻结题面绑定一致。本次没有交付新独立 public_development_brief，不能宣称其已有实际 HTTP 交付或 fresh 阅读验证。

[已封公开 brief 窄核](orange4014_9b_public_briefs_review_20261003.md)仍有效，4014 brief SHA `a7f74bbe44d8…` 未变；其构建入口现在由本次真实 agent 构建补证。该 brief 的公开 selector 命令本轮没有作为独立公开 pytest 命令跑；27-key 私有评分不能包装成这些命令已执行。后续模型公开材料应继续只给必要环境、构建/公开测试入口与验证边界，不提供候选、私有评分键或修法；若附 brief，另保留实际交付字节证据。

本次 endpoint 确定性给出固定修法步骤，验证的是 CPU 上真实 CC 开发与原生工件链。没有本题真实模型成绩、稳定性、并行能力或训练准入结论。无需为本轮继续重复实验；可提交题级诊断 CPU 验收，并作为后续 probe 申请依据。
