# 零分复核：DVC、Pydantic、Conan

2026-09-19，Codex 子审查。只读本轮回传日志、冻结题目与 noop/gold 对照，未运行新容器、修改奖励或生产代码。覆盖三仓全部 **91 条零分**，含主批70条和校准/并发/PID对照21条。逐条记录在 `runs/full216_rh2_diagnostic_20260919/zero_audit/core/zero_records.jsonl`，含每个参考ID的原状态行、失败 traceback 行号、安装记录、gold对照与资源采样；覆盖验证见同目录 `verification.json`。

| 审查结论 | 主批 | 全部 campaign |
| --- | ---: | ---: |
| 目标测试确实因待修行为失败 | 52 | 61 |
| 目标失败成立，但混有独立运行或参考契约问题 | 13 | 19 |
| 本次0由资源/参考问题主导，不能当干净目标失败 | 5 | 11 |

“环境/参考主导”描述本次失败机制，不是要求把noop改判1；未修复的noop本可为0，但资源或依赖遮蔽后不能据此证明任务已被正常检验。

**安装报错单独记录，不自动把目标失败归为环境失败。** 91条中72条有安装失败；大多数仍实际执行了目标源码和断言，gold使该目标通过。这个证据支持当前特定补丁对照，不保证改变依赖或构建脚本的候选也能正确安装。

## 需要带回修复/环境流水线的事实

1. **DVC-2141：512配额下的8条0受到进程资源污染。** 基线、512重复和进程扫描批，两个F2P实际抛 `BlockingIOError: EAGAIN`，不是题目期望的metrics内容断言；5个P2P也失败/ERROR。2048对照的两条noop仍为0，但这时实际失败是缺少 `working tree` 内容，P2P全通过，gold两次为1。后者是有效目标失败。直接 `/proc` 扫描还记录507/496个僵尸进程，父进程均为容器PID1：`remote/evidence/dvc2141_procscan.jsonl:43`、`:85`（路径相对本轮 runs 根）。
2. **新增 DVC-4778：gold=1也没有证明noop的失败原因正确。** noop四个F2P都有FAILED行，却全部以 `re.error: redefinition of group name 'ps_d'` 结束。测试期望 `dvc.add` 对symlink抛 `DvcException`；gold提前抛目标异常，因而4/4通过，同时 **51个参考外测试仍失败**。实际0被另一条正则执行错误遮蔽，不能作为干净能力信号。依赖兼容性是待复证解释，具体版本根因尚未验证。
3. **两个gold零分来自参考ID表示不一致。** DVC-4185的7个F2P全通过，P2P中反斜杠参数的1个键缺席；原日志里双重转义对应测试为PASSED。Pydantic-8977的4个F2P全通过，5个P2P的非ASCII/控制字节键与pytest转义输出不一致，对应输出也为PASSED。不能把这6个MISSING键解释成6个测试未执行。
4. **目标失败有效、环境仍不完整的实例已具体定位。** DVC-5822的F2P是题面同款 `assert bool(scm)==bool(rev)`，但noop/gold另外46个测试失败；DVC-4125、5148、4166、4066、4719、5004也混有命名组重复异常。另见旧 `networkx` 的 `fractions.gcd` 导入失败（3794/4166/4066/4185）、`DiGraph.node` 缺失（2231）、`pygit2.GIT_OBJ_COMMIT` 导入失败（9395）。这些发生在参考外，不能改写成所有零分都由环境导致，也不能忽略为环境全好。
5. **Conan-11594确有参考键碰撞，但这次0仍有真实依据。** 来源F2P键被空格截为 `test_run_tests[Ninja`；noop的 `Ninja Makefiles` PASSED和 `Ninja Multi-Config` FAILED都映射此键，后者最后覆盖。真正失败断言为target生成成 `RUN_TESTS` 而不是 `test`，gold两者都通过。保留该有损映射问题，不把它误报成此次假零。

## 安装与正常失败如何区分

Pydantic的 `pdm: command not found` / `make install` 失败贯穿noop与gold，但20个noop均有具体目标错误：例如8500字段顺序、8316 snake_case、5706 Sequence schema；19个gold参考全通过，8977剩下的是ID问题。没有证据支持“这些0都是没装好pdm造成”。DVC安装也常出现离线构建依赖不可取、requirements路径不存在，最后一条命令却返回0；因此只看安装末rc既会漏错误，也不能做零分归因。

权限/外部程序错误也不自动算环境故障：DVC-3527、5336在测试中主动mock只读/权限错误，目标就是正确处理它；Conan-13230跨编译时不应调用xcrun，缺少xcrun触发的失败正对应待修分支。三者gold按题意修复后通过。

## 重点原始证据

以下路径均位于 `runs/full216_rh2_diagnostic_20260919/remote/replay/`，JSONL提供其余91条的完整定位。

- DVC-4778：`baseline01/workers/w02-0/eval_logs/evallog_replay-f216-baseline01-w_190e8609.eval.log:17325` 为测试体，`:17339` 为预期异常，`:17374` 为正则构造，`:17739` 为错误，`:19112`起为F2P状态。gold日志尾缀 `967ae3ef` 仍有51个参考外失败；原gold新增早期 `DvcException` 分支。
- DVC-4185：`baseline01/workers/w02-2/eval_logs/evallog_replay-f216-baseline01-w_ae247e4c.eval.log:2772` 有转义参数PASSED；7个F2P全部PASSED可在逐条账本核对。
- Pydantic-8977：gold日志路径由JSONL对应行给出；934/936/1065/1075及uuid参数行是转义后的PASSED，参考却保留原字节表示。
- Conan-11594：`baseline01/workers/w01-3/eval_logs/evallog_replay-f216-baseline01-w_363e2ca9.eval.log:621`、`:625` 为同键不同真实nodeid；`:606` 为真实断言失败。

边界：所有有失败的F2P均找到具体traceback；逐ID重放计数与账本一致。但这些仍是候选进程输出，不是独立可信测试事件，不能核销已知stdout/hook伪造面。主批未完整持久化终止事实，采样无OOM不等于严格排除一切瞬时资源问题。题目描述是否足够、测试是否覆盖所有合理解法属于下一层质量审查，本切片不据当前0/1直接批准训练题池。
