# MONAI5932：最终 CPU 结果

2026-09-29，`mixed-v1`。**原镜像无需新增修复；正式 noop=0、gold=1、仅反转匹配顺序的退化=1。退化破坏 base 原本通过的长名在前表达式，却通过全部正式参考，确认 S1 评分覆盖缺口。** 题主已核完整原件，root冻结parser及传输对账已一致，[跨包最终独立复核](../../reviews/monai5932_result_review.md)已完成。历史 `result_partial.md/json` 保留，当前结论以本文件为入口；CPU 完成不代表模型或训练资格。

## 原镜像与真实 actor

源 manifest `84a4d4afe3f663633da40359ddb8ff5c0e951144e103bed27b907481f9cee6f4`，实际 config ID `833da815aeee5132d737c83e3af72b822b5a2e0498368287014919cef084dd49`，base `3c8f6c6b94ba26f8c9df5b7c96089494de6f69cb`。CC 2.1.205、uid 54321、Python 3.8.20 从 testbed 激活并从 `/testbed/monai/__init__.py` 导入。numpy 1.24.4、torch 1.13.1、parameterized 0.9.0、pytest 8.3.3 实际可用，源码目录和 `/tmp` 可写。

初态已有 `M requirements-dev.txt`，MONAI 版本带 `.dirty`；这是 actor 启动前就存在的状态，不能称为 pristine checkout 或 actor 改动。历史 recovery 材料记录删除 MetricsReloaded URL；本次 actor 原件只列路径，没有新采完整 diff，不能单凭该行断言当前所有 diff 字节。结束 status 行数仍为 1、agent 进程为 0；实际目标源码的 base SHA 另在私有准备中确认。

| 公开命令 | 实际结果 | 解释 |
| --- | --- | --- |
| identity | rc=0 | 身份、激活、导入、版本和 base 可追溯 |
| short_first | rc=1，目标 SyntaxError | 短名先出现时，长名被错误变成 `__local_refs['training#num_epochs']_per_validation`，在 ConfigParser 的 ast.parse 处失败 |
| long_first | rc=0，`CONFIG_RESULT 4` | 交换两个加数后正常解析，实际数值断言通过 |
| public_existing | rc=0，18 passed、26 warnings | reference_resolver 4 项、config_parser 14 项完成，无 import/collection failure 或 skip |

[完整 actor 输出](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/Project-MONAI__MONAI-5932/mixed-v1/actor_original/captures) 显示短名失败确实进入目标表达式替换路径，不能把此 SyntaxError 归因于缺包或任意命令非零。旧回归中的 Pdb 提示是已完成的 `test_pdb` 输出，不是挂起；终态明确通过。共 4 条 Bash 调用完整，prelaunch/activation 正常，容器/网络/relay/stub 清理无残留。

## 私有对照与实际补丁

[私有原件](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/Project-MONAI__MONAI-5932/mixed-v1/private_behavior) 在同一镜像以 root 执行，只证明行为，不替代 actor 权限。base、gold、退化先验目标 `monai/bundle/reference_resolver.py` SHA；gold/退化分别 check、实际 apply 后再验完整文件 SHA，均成功。三者源码 hash 分别为 `c3c197d8…`、`fc848148…`、`bd0d4a13…`，完整值和每个准备步骤见 JSON。

| 变体 | short_first | long_first |
| --- | --- | --- |
| base | 目标 SyntaxError | 4 |
| gold：按引用长度递减排序 | 4 | 4 |
| 退化：仅 `result.reverse()` | 4 | 目标 SyntaxError |

退化在原例修好的同时，使 base 原本通过的交换顺序例子失败，错误表达式同样残留 `_per_validation` 后缀；属于引用替换顺序的真实回归。两个命令各自独立执行，不是首个失败后推定后一个结果。三变体共 6 个行为命令均到达目标路径，全部准备完成，逐容器 rm/query 无残留。该矩阵没有执行私有旧模块，也不能据此声称其它引用形式都已验证。

## 正式评分与实际导出

[三组正式原件](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/Project-MONAI__MONAI-5932/mixed-v1) 均实际执行 `pip install -r requirements-dev.txt`、`python setup.py develop`，再运行 `pytest -rA tests/test_config_parser.py`。安装没有跳过、失败命令或未结束段，test 段完整。导入仍来自 `/testbed/monai/__init__.py`，三组 runner digest 前后相同；没有将安装/采集故障算作目标失败。

| 项目 | noop | gold | 退化 reverse |
| --- | --- | --- | --- |
| 正式 reward / test rc | 0 / 1 | 1 / 0 | 1 / 0 |
| F2P `test_substring_reference_0` | FAILED | PASSED | PASSED |
| 14 个 P2P | 全通过 | 全通过 | 全通过 |
| 完整 pytest | 1 failed, 14 passed | 15 passed | 15 passed |
| 安装 / 测试段秒数 | 9.882 / 34.229 | 9.689 / 27.447 | 9.578 / 27.782 |

参考 nodeid 前缀为 `tests/test_config_parser.py::TestConfigParser::`。直接从完整 test 段逐项核对来源 grading.json 的 1 F2P+14 P2P，共45个状态，恰好覆盖全部测试，无缺失、重复、skip、参考外失败或段外状态。三组均有25个 warnings：NumPy/scipy/torch 弃用、允许缺失引用测试的预期警告和 LoadImaged 默认值弃用；Pdb 提示来自已通过的 `test_pdb`，没有挂起。noop traceback 指向错误替换后 `__local_refs['training#A']_B` 的 SyntaxError。

两份 candidate.patch 均与原输入逐字节一致。解码正式 frozen_patch 的完整源码后，gold SHA 为 `fc8481487a9ddc33e1b7ff718b240866ae5e891af3c2f5eefa286f7d263c9b6d`，退化为 `bd0d4a13404a980ac00822601d2245cb73d003238c599c83a8771d793a21bc0a`，均等于私有实际 apply 后值；与 base 比较只有既定排序/反转增量。两者仅投影 `monai/bundle/reference_resolver.py`，mode100644，excluded_pathset_changed=false；noop entries为空。三份完整 eval.log SHA 与 ledger 匹配，详见 JSON；不能仅凭 apply或脚本 rc=0认定候选已生效。

[root冻结parser重放](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/monai5932_final_v1.json) 与题主直接读回的45个状态完全一致。[传输SHA对账](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/evidence_manifest_monai5932_v1.json) 确认远端/本地88份原件、1,373,282 bytes无差异。

候选容器每次 removed=true；从各原始 driver log 尾部再核 manager close，created=removed=1，containers_open、supply_open、cleanup_failures均为空，最终退出0，和 checked receipt一致。两层清理均确认。

## 为什么这是公开要求内的漏判

[公开题面](../../../../../../../runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-5932/user_prompt.txt) 描述的是“同一表达式中具有相同前缀的引用不能解析”，没有限定短名必须在前。原例两个整数引用分别为1和2，再加1；只交换前两个加数，仍是同一对已定义引用，期望仍为4。[公开 base 方法](../../../../../../../runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-5932/base/monai/bundle/reference_resolver.py) 的 `update_refs_pattern` 文档要求按引用ID替换内容，也没有这种顺序限制。更直接的动态依据是 base 已通过交换顺序例子；因此这里要求保留现有正常行为，不是仅用 gold 支持的新断言扩张题义。

base 的 `findall` 按出现顺序收集引用，随后 `str.replace` 会把短ID在长ID内也替换掉。gold 按长度递减处理，二种顺序均正常。退化只 `result.reverse()`：短名在前时恰好先处理长名；长名在前时反而先处理短名，产生同一种目标 SyntaxError。

[来源 test.patch](../../../../../../../runs/swegym_quality_expansion_20260925/private/Project-MONAI__MONAI-5932/test.patch) 新增的唯一参数是 `A=1, A_B=2` 与 `$@training#A + @training#A_B + 1`，只覆盖短名在前。14个旧 P2P 未包含同前缀长名在前表达式，故 reverse通过全部15项。实际导出源码、正式1分和私有长名在前失败形成完整证据链，问题是断言覆盖不足，不是 parser误计或环境故障。本结论限于这两个整数加法顺序，不声称任意表达式、引用次数或嵌套形式都已验证。

## 资源边界、用途与剩余项

三次正式均2 CPU / 4 GiB，诊断 setup/reset预算由300升至900秒，test维持1800秒、whole1800秒；trusted setup依次722.174、505.765、476.790秒，不能称旧300秒条件已通过。三组 ledger peak均4096 MiB，resource_facts均null。

[03:12只读快照](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/diagnostics/host_memory_pressure_0312.json) 通过noop report后缀8426cf4b匹配容器：当时仍在chown，memory.current=4,294,946,816 bytes，其中file=4,035,452,928、anon=1,216,512；累计写入6,114,652,160 bytes，pgscan_direct/pgsteal_direct均496,960，memory.events.max=1942，oom/oom_kill和pids拒绝计数均0。这支持准备阶段copy-up和文件缓存回收压力；4 GiB峰值不等于OOM，也不证明测试进程必需4 GiB。该快照不覆盖全程，不能外推gold/退化全部事件；不补造完整资源健康证明。

[root按真实评分容器后缀匹配的采样汇总](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/resource_monai_pair_v1.json) 覆盖noop/gold/退化51/36/34个样本，memory.events.max分别3660/3634/3626，三组采样均未观察到OOM/oom_kill或PID拒绝。采样非完整生命周期，ledger resource_facts=null和未采到的终止事实仍保留未知；这些统计包括准备开销，不能作为测试独占需求。

当前可用于原镜像开发条件、目标行为和评分覆盖诊断。交换顺序对照可作后续D6修订草案；本批没有改正式测试或评分，在覆盖缺口处理前不进入无条件正确性比较或训练奖励。跨包最终独立复核已确认本卡与原件一致；D6处置及新版本验证另按决定推进。本批未做完整pip_check，正式题面/public_hints真实交付、自主模型、模型/GPU/预算/训练资格也未由本批证明。

[机器结果与原件 SHA 索引](result.json) 保存45个逐参考状态、真实安装、实际导出、日志、资源及两层清理；历史partial保持原快照。本轮只读取本地同步原件，没有重跑、修改输入或操作远端。
