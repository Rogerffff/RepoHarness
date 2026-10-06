# DataLad 6b6f：065 的非作者 CPU 结果复核

2026-10-03。**七候选正式评分与本次公开 actor／题面交付证据可接受，未发现新增阻断。实际 raw reward 为 0/1/1/0/0/0/0；gold、C-A 均精确匹配 17/17。** 这是固定版本的 CPU 材料验收及开发链路证据，不是模型探针成绩或训练／留出准入。

本审查已接触私有材料，是非作者证据复核，不是 fresh 公开盲审。只读本地原件、JSON 和源码，没有 SSH、重跑、项目测试、安装或实现改动。证据根目录为 `runs/category2_repair_20260929/r2e_datalad_cpu_20261003/cpu_c_evidence/`；以下 matrix／actor／build 路径相对此目录。题主两个 owner readback 是索引，结论由原 ledger、eval log、driver、capture 和首请求重建，未凭其 status 判通过。

## 固定身份与构建边界

本地 release `r2e_064_065_candidate_v1/manifest.json` 实际 SHA256 为 `282021962a92b510f077385660ac56acedcd7fac1d97e63db3baa98e4dcc057f`，release ID 为 `cat2-cpu-r2e064065-swe5-20261003-v1`。正式 grading bundle 文件实际 SHA `0a30197e588243533dfff104836e2dda4a4428664685897afff54b4709a52f24` 与 manifest 登记一致；本题 expected 文本实际 SHA 为 `15da45bafd393ca47e0f732decf3079f3fe8c55f43b58359ba4795095d6dccb9`，17 键、16 PASSED＋1 FAILED。

065 正式 `test_1.py`、本地已审私有全文、build/context/material 内实际全文的 SHA 都是 `161f9d3b7bafc365932249ad934aa9f17ef12ff90d88b2ee7683605ccd05a3bd`。原构建 log 打印材料应用成功、实际树 `7c0a5adcca94e3747a8ff2b0bbab7ea94eba162526e036d5e6a1ddf7460c5e6c`，完成 image export，末尾 `[rc=0]`；它与七份评分日志的 setup 树一致。实际新镜像为 `sha256:1c82f7f509ee94bec9223e17afc9343c0794edc259759bdbf96c87f17b47b77f`，配方为 `r2e_derive_v1+material_v2+sysconfig_v1`，SHA `0068598f198826bfd433b152bb307200b14ae1eb3e8034d6c4d7e9ae113111db`，七账本与 actor_v2 逐一一致。

没有只沿用 `build_readback_owner.json` 的 21 项汇总。直接比较 `integrity_base.txt`／`integrity_derived.txt`：源码等 A 段 263 行、venv 非 bin 的 B 段 13849 行、bin 文件 C 段 72 行、Git 初态 D 段均逐行相同；L/P 的差异是登记的 Python 链接／pyvenv home 搬迁。实际 `datalad/support/network.py` 在两份原清单均为 `a23b14c0194ef9fd947119f0c5ceb07cbfea0f13bbb35b331f22e02adb115702`；公开 `datalad/tests/test_network.py` 也相同。构建 root/UID 原 facts 保留解释器可执行、私有目录拒读及 Git 清理记录。它们是构建／环境诊断，不能冒称模型观察。

## 七次正式评分的独立读回

逐份核了恰好一条 ledger、log 的真实 Start/End Test Output、`RH2_TEST_RC=1`、test start/end 时间戳，以及 driver 最终状态。从测试段的原始逐测试状态重建 observed，再按冻结 expected 精确比较；所有 observed 都恰好是同一组 17 键，无 missing／extra，yield 的 XFAIL 不产评分键。源码 `envpack/r2e_parsers.py` 也明确只采 PASSED／FAILED／ERROR，不把 XFAIL 当键。

| 候选 | raw reward | 状态匹配 | 原日志的目标失败／结果 |
|---|---:|---:|---|
| noop | 0 | 15/17 | `weired_url:/` scheme 仍是 `file:implicit`，`is_url` 为假 |
| gold | 1 | 17/17 | 目标用例均通过，固定环境 FAILED 保留 |
| C-A | 1 | 17/17 | 合理解不再因含斜杠前缀分类被误拒 |
| C-B | 0 | 16/17 | 从字段重建得到 `example.com:path/sp1/fname`，与 `example.com/path/sp1:fname` 不同 |
| D-eq | 0 | 15/17 | 修改比较仍未改变真实 `scheme` 与 `is_url` |
| D-eq-minus | 0 | 15/17 | 同样由字段值与识别行为拒绝 |
| D-hard | 0 | 15/17 | 新非示例 `my_host:path/sp1` 的 scheme／is_url 失败，未因只特判原例放行 |

全部 pytest 退出 1，因为 `test_get_local_file_url_linux` 实际得到 `file:///a~`、expected 固定为 FAILED；gold/C-A 的唯一失败就是这一项，所以 **test rc1 与评分通过不矛盾**。gold/C-A 原 log footer 为 16 passed／1 failed／1 xfailed；其他负例的新增目标失败有真实 AssertionError 回溯，不是应用失败、ImportError、准备超时或零解析。

六份原输入补丁实际 SHA、ledger 候选 SHA 和冻结 `candidate.patch` 逐字相同；均以 `agent/54321` apply，投影仅 `datalad/support/network.py`。noop 投影为空。测试／fixture 修改列表为空，runner 前后实际 digest 相等，`runner_integrity_changed=false`。六个补丁的完整身份继续见已登记 `acceptance_matrix.json`，本轮未更换候选或造新反例。

每个 invocation 都是原 `replay_grade_budget.py --env-reset-timeout 1200`，`--repeat 1`；ledger `regrade_total=0`。准备实际约 46.9–52.7 秒，测试约 2.2–2.9 秒。账本保留既有 UID54322、2 CPU／4 GiB、禁网、PID512 profile。`RH2_INSTALL_SKIPPED=1` 表示使用已派生环境，本轮没有重新安装项目依赖；setup／测试段实际完成，没有以安装中止或超时作为负例。

七次候选清理均 `removed=true`；逐份 driver 的 manager_close 记 `containers_created_total=containers_removed_total=1`，grader containers、supply_open、cleanup_failures 均为空，final_status exit0。总 matrix 作业 status finished／rc0、stderr 空。这里确认的是每次登记的候选／grader／供给范围清理，不扩写为全宿主不存在任何其它作业资源。

## 恢复后的公开 actor 与首次失败

原 `actor/attempt/attempt.json` 保留 `ModuleNotFoundError: No module named 'torch'`、termination `driver_exception:ModuleNotFoundError`、harness exit -2；旧 trajectory 0 字节、工具／assistant 计数 0，没有 stub request 文件，gateway drain active_requests=0。旧作业 rc1；内层 container rm0／cleanup_ok=true、网关和桩停止 rc `[0,0]`。它发生在 CC 之前，不算题目 0 分、模型失败或旧公开检查成功；原件没有被新运行覆盖。

`actor_v2/solve.log` 的实际命令切换到独立 `runtime_cpu_v2`，仍调用同一 sealed `r2e_solve_attempt.py`；entry 实际 SHA `10a71cca67af24c9ab5a6de09cb1845751c643632559842bb61dbce6ebc01d5a`、E2E SHA `a5b23b49f126b76a1512a3a6f184bb7e16276c4e9cf137dc7cdc46d3af4ee4fc`、shared solve SHA `00ca849909150de02769f297374a9bbfacf2746347c425474775d9c3e22a04f9` 均与 sealed manifest 及 attempt 一致，没有改材料或旧在途解释器。

新 `actor_v2/attempt/harness/trajectory.jsonl` 实际 SHA `220e3785faeec2ae9a176db4a2328ecc702032d2f26d163161a3e43e915e7c93`，64 行 JSONL、6 个真实 Bash/tool-result，末尾 `result/success`，harness exit0。实际命令结果顺序为 `0/0/1/1/0/1`：preflight 三项 ok；公开 import 为 Python3.7.9／`/testbed/datalad/__init__.py`；原例和公开 helper 是预期 AssertionError，不是依赖缺失；边缘调查 rc0；公开 test_network 为 16 passed／1 failed／1 xfailed。预 launch 原 facts 的 UID/GID54321、cgroup CPU200000/100000、memory4294967296、pids512、swap0、外网探测拒绝和 activation 写入拒绝均在原件，激活实际指向 `/testbed/.venv/bin/python`。

新 attempt 正常完成、quiescence 成功、pip freeze 未变；冻结工件为空且 `excluded_pathset_changed=false`，原 classification 的 runtime_private_pathset_changed=false。内层 cleanup_ok=true、container rm0、容器／网络剩余为空；外层 residuals `_clean=true`、端点停止 `[0,0]`；新作业 rc0。没有 grade 结果，空工件不能转述为模型修复通过。

## 实际首请求与公开／私有分离

直接读取 `actor_v2/gateway/datalad-r065-cpu-c-public-v2/requests.jsonl`，其实际 SHA `0cb0787767bf1b24092f16e8b3a3a7ec1f78c932f49c9d57a081c2ec2d3c718f` 与 owner readback 的 request_log_SHA 一致，7 个请求。首行 body 与 `actor_v2/stub/requests/messages_000.json` 解码内容相同；后者原字节 SHA 为 `2dbecffc6bdef428e9248c74be3bce39bf321c72c2c4f3c49654d7b8bfdd5df6`。两个摘要分别标识 gateway 日志和首个完整请求，不混称同一文件。

首个 user 消息逐字包含 prepared prompt 一次，实际 **1203 字符**，SHA `a0f4c92ea4cc56c9a07670100d75b30dfc828e7c82c6b671b1ba7e8cd38bf233`；其中 issue 正文本身 **1100 字符**，SHA `7aee20e15dc5452af921173d20792fe95c0b0d17e04c935c7fe99c648acf1cad`。`attempt/prompt.txt` 同内容。直接核请求 body 不含两个新增私有测试输入 `my_host:path/sp1`／`data_server.example.org:/srv/ds`，没有从 owner 布尔字段推定交付。

这只证明真实 CC＋CPU 桩入口收到了原公开 prompt。桩预设 Bash 与模拟 token／费用不是实际基座推理，私有 gold/C-A／反例矩阵也不是模型成绩。GPU 探针的实际题面、公开开发说明交付和模型行为仍需另外核，已登记的 gold 边缘回归及同仓答案关联继续保留。

## 逐次原件 SHA 索引

各行 ledger 位于 `matrix/<候选>/ledger.jsonl`，完整 eval log 位于同目录 `eval_logs/`（每目录一份 `.eval.log`）。这些实际摘要均与原 ledger／题主 readback 一致。

| 候选 | ledger SHA256 | eval log SHA256 |
|---|---|---|
| noop | `f500d359536b3d6fad96a6a62a6c2b626c52efb6665d00e65901a34fb4f62e57` | `5b59dc84447e2c93e6a545130a10dc95b1f0dd7076395225fb082422e1fe67df` |
| gold | `7da32fcdaefaf73ac80c2d2654ba4a02d32f67c9f9e553a9524cce2a83e2cd20` | `d6c3bc57da92a86b7037c644c3a6e50202c94d06071bcce95a5f844b57456921` |
| C-A | `64370f0e93f9f09ee8a5fb6489724a4e0fc6c064ff7177e686a7cc3abbc2ec91` | `8adc3de29a4acc9a394eff7d9e04446a0ffa4ff6448e4a2785ffa3108722e00f` |
| C-B | `b1038388c3454a5b69a3b55468533f86149c923a0b33be88256a23296b5b0e18` | `96500ba31bb88a80aa537b4d4aaac72a744deb36246cff70b6482bb6325fb358` |
| D-eq | `deebdce930a202d0fd4c2c592650c2833e3945f24d03b15e5c7f6b48fa649a90` | `b955c2650127886604fe3f5f6c590cc8724e81e9252acd9dc4a3e43cb76985ba` |
| D-eq-minus | `029096e3448977aab48a953a81a6709688e3cc9c78b5e4482ae5ce79625955d8` | `5ea028f72bf08cb4f25d6429eeb633cb07082b10eda84546122c2db11446afd4` |
| D-hard | `4e42ebe4cd313506c060a4cb4cf969df8d7766a91e9962be2a83bc533f2ff028` | `381a8cb68b17b2707db3e0e3a36c91eaa54ff6fd2d90834e341923f3be949726` |

题主索引的实际摘要：`checks/cpu_matrix_owner_readback.json` 为 `22fd0ef81bd4e16ac846f52ef475b95d3a419eedbee6250a5e28cc76f5feee3b`；`checks/cpu_actor_owner_readback.json` 为 `e74e7315b2e43faab7315bba6008f85dc39681ef96f9fbafa3288764da5de111`。原 build facts SHA 为 `968d6b083bca036d42eb496ffe826bb8ffc08721476cefbc2e22a2a110a83cc4`，build log SHA 为 `aa23b808489c05ddacef2649f85b35996e32c9ea2f906be1d4a01350df175f5d`。
