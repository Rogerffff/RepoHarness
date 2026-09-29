# Moto5406：最终 CPU 结果

2026-09-29，`mixed-v1`。**正式noop=0、gold=1、恒East2退化=1；同一实际导出退化使East1新探针和原公开East1测试失败，确认S1评分覆盖缺口。** 原镜像无需新增依赖修复，题主已核完整正式证据，[跨包独立复核](../../reviews/moto_pair_result_review.md)及最终卡窄对照已完成。历史partial保留；当前用于环境和评分覆盖诊断，不授予无条件正确性比较或训练资格。

本题沿原baseline01的make init条件，未构建派生镜像，不能误记为install_wave1。源manifest `727caa5dba157d41b1e839a5044106f0ad7ea1fe824c9a5f562e2f74113339d6`；actual image `808c60d962cb94330e499404720a0813fa400a2e86464aabdb47fcaa05aad5f6`。base `87683a786f0d3a0280c92ea01fecce8a3dd4b0fd`。

[actor原件](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-5406/mixed-v1/actor_original) 显示CC2.1.205、UID54321、testbed Python3.12.4、boto3/botocore1.35.9、pytest8.3.2，导入`/testbed/moto/__init__.py`。原4条公开Bash完成，prelaunch/activation正常，开始/结束git status均0行、agent进程0。

East2命令rc1是实际Create/Describe都返回East1 ARN的断言失败；East1命令rc0且ARN正确，两种命令均输出另一地区列表为空。公开`test_create_table_standard`独立完成1 passed、5 datetime弃用warnings，无skip或采集/导入故障。actor容器、网络、relay、stub清理完整，无残留。

[私有原件](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-5406/mixed-v1/private_behavior) 在同一image的独立root容器运行，不能替代actor权限。三变体的三个命令各自执行，首项失败后未跳过其余项：

| 变体 | East2新探针 | East1新探针 | 原公开East1测试 |
| --- | --- | --- | --- |
| base | ARN错误：报East1 | 正确 | 1 passed |
| gold | 正确 | 正确 | 1 passed |
| 恒East2 | 正确 | ARN错误：报East2 | 1 failed |

恒East2的原公开测试失败位于TableArn断言：actual `arn:aws:dynamodb:us-east-2:123456789012:table/messages`，expected同表的East1 ARN。所有新探针的Create/Describe彼此相同，另一地区列表为空；错误在地区字段，不是表名、账户或区域隔离。9个行为命令均有完整结果。

三变体准备均完成；gold/退化分别check、实际apply再验证源码。base/gold/退化完整`moto/dynamodb/models/__init__.py` SHA分别为`87a558769bc0786464aeaca26fc29217c718971f447d6ddfc4ced9a3977d4f23`、`2fd7febd19be90e561f79b324508cc934b05922fc32c8daab7f5097d25234b5c`、`4bd4d6450546ba4a497c938023bea94b7bd81c774e089c0a0db690c461c66253`，与raw prep输出一致。每个私有容器rm/query均0、remaining为空。

## 正式评分、实际导出与清理

[完整三方原件](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/getmoto__moto-5406/mixed-v1) 实际执行原`make init`，包含setup.py develop与pip editable安装，最终Successfully installed moto-4.0.0.dev0，三组install rc0、无failed_commands、未skip。setuptools/egg/editable弃用、版本规范化和缺可选manifest文件是安装警告，未造成安装失败。源码导入仍为`/testbed/moto/__init__.py`，观测包版本4.0.0.dev，runner digest前后相同。

| 正式项目 | noop | gold | 恒East2 |
| --- | --- | --- | --- |
| F2P `test_create_table` | FAILED | PASSED | PASSED |
| 26 P2P | 全通过 | 全通过 | 全通过 |
| reward / test rc | 0 / 1 | 1 / 0 | 1 / 0 |
| 完整pytest | 1 failed, 26 passed | 27 passed | 27 passed |
| 安装 / 测试段秒数 | 8.014 / 6.030 | 6.418 / 5.360 | 6.911 / 4.831 |

正式只运行`tests/test_dynamodb/test_dynamodb_table_without_range_key.py`。直接从三份完整test段逐项核对来源grading.json，81个参考状态全部对应，没有缺席、重复、skip、采集/导入故障或参考外失败；每组151个datetime弃用warnings。noop目标断言实际得到East1 ARN，期望East2 ARN，故0分有效；gold/退化完整27项通过并真实退出0，不是仅调度命令退出0。

两份candidate.patch与输入字节一致。解码frozen_patch完整源码与上述私有apply后SHA一致；gold保存region并以region生成ARN，退化只是把固定East1改为固定East2。二者仅投影`moto/dynamodb/models/__init__.py`、mode100644、excluded_pathset_changed=false；noop entries为空。三份完整eval.log SHA均与ledger一致。

每次candidate removed=true；从原始grade log尾部核manager_close与checked receipt一致，created=removed=1、containers_open/supply_open/cleanup_failures全空，最终exit0。安装、真实候选和两层清理均确认。

## 公开要求与漏判原因

[公开原题](../../../../../../../runs/swegym_quality_batch05_20260921_v1/public/getmoto__moto-5406/user_prompt.txt) 报告client指定East2却返回East1 ARN，其核心是返回所选地区的表ARN。原例创建表名`mock_Foundational_AMI_Catalog`而末尾断言写`test_table`，这是表名不一致；本次公开命令按实际创建名断言，只保持地区要求，不把原例笔误当预期。区域隔离输出也表明本例错误位于ARN，不能直接宣称表真的存到了另一地区。

[来源test.patch](../../../../../../../runs/swegym_quality_batch05_20260921_v1/private/getmoto__moto-5406/test.patch) 将既有create_table测试从East1改为East2并重命名，ARN断言也跟着改为East2，其余改动多为去除旧测试名的boto3字样。26个P2P虽有其它地区操作，却未挡住恒East2 ARN。另一个公开文件中的`test_create_table_standard`保留East1 ARN断言，但不在正式命令/参考内；它对base和gold通过、对同一退化实际失败。因此本结论同时有公开旧行为和新两地区探针支撑，不靠gold输出定义正确性。

修复不能只是把一个固定地区换成另一个固定地区。正式完整1分与私有East1实际失败、实际导出源码一致，形成真实覆盖缺口证据；不是遗漏正式参考或parser伪装。可供后续D6修订的最小方向是同时保留East1/East2 ARN验收，本批没有改正式测试/评分。

[root冻结parser重放](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/moto5406_final_v1.json) 与本卡逐参考读回一致；[远端/本地SHA对账](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/evidence_manifest_moto5406_v1.json) 确认91份、1,782,888 bytes原件无差异，二者均已完成。

## 资源、用途与剩余项

三组2 CPU / 4 GiB，诊断setup/reset900秒，test仍1800秒、whole1800秒；trusted_setup依次293.409、277.820、280.308秒，ledger内存峰值809.312、795.359、795.750 MiB，resource_facts均null。时间接近旧300秒上限不等于本轮在旧配置完成；本批仍以实际900预算记账。峰值包含准备，不当作测试独占需求；未从全程事件证明无OOM/PID拒绝。

[按真实评分report后缀匹配的资源采样](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/resource_moto_pair_v1.json) 对noop/gold/退化分别有21/19/20个样本，采样内memory.events.max/oom/oom_kill及pids.events.max均0。约15秒间隔并非完整生命周期，保留ledger峰值与采样峰值差异，不用采样填补resource_facts=null或未知终止事实。

当前可用于原镜像开发条件和评分覆盖诊断；D6处理前不进入无条件正确性比较或训练奖励。剩余为D6新版本验证（若实施）；Stream/SSE/TableClass未跑组合、完整pip_check及全生命周期资源健康不补记通过。正式题面/public_hints、自主模型及模型/GPU/预算/训练另行管理。本轮只读本地证据、写本题记录，未远端执行或改输入。

[最终机器结果与原件SHA](result.json) 保存81个状态、安装/测试、实际导出、资源及两层清理；[历史partial](result_partial.md)保留原快照。
