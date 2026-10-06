# MONAI5932：公开开发与私有行为阶段结果

2026-09-29，`mixed-v1`。**原镜像的真实 actor 可复现引用替换顺序错误，公开解析器回归 18 项通过；私有 gold 修好两种顺序，简单反转顺序的候选只修一边、破坏另一边。** 未见需要新增环境修复的证据，本题未构建派生镜像。此为题主读回，独立复核未做。审查快照中正式 noop 在途且无终态 ledger，gold/退化正式结果未知；步骤 rc=0 不代表正式评分通过。

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

## 用途与剩余项

当前支持原镜像下的公开开发条件及目标/反例行为诊断；不提前称退化候选已被正式拒绝或误奖。正式在途结果完成后，仍须核候选实际投影、安装、完整测试、逐参考状态、parser、资源和两层清理，再接受独立审查。本批未做完整 pip_check，不能宣称全镜像依赖健康。真实 CC 消息仍为 Devcheck 控制文本；正式题面/public_hints 交付、自主模型及模型/GPU/预算/训练资格不在本阶段证明范围。

本轮只读已有原件，未重跑、改输入或操作远端。[机器结果与原件 SHA 索引](result_partial.json) 固定本次已完成证据快照。
