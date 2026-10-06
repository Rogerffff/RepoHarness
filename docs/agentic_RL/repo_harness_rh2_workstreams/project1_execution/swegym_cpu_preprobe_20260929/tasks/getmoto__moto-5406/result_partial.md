# Moto5406：公开开发与私有行为结果

2026-09-29，`mixed-v1`。**原镜像actor可复现East2表ARN错误；gold两地区正确，恒East2候选在East2通过，却破坏East1及原公开East1测试。** 三方正式证据尚未齐，本卡不提前确认退化是否被正式拒绝/误奖，也不作最终用途决定。

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

后续接续完整正式日志、投影源码、27项来源参考、安装/两层清理及独立复核。Stream/SSE/TableClass等未跑组合不补记通过；完整pip_check与全程资源事件未由此卡证明。真实CC接收的是Devcheck控制文本，正式题面/public_hints交付、自主模型、模型/GPU/预算/训练仍另行管理。[机器结果及原件SHA](result_partial.json) 固定本次范围；本轮未远端执行、改输入或重跑。
