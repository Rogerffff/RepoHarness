# mypy15139 跨包结果复核

2026-09-29。审查者：MONAI/Conan/Moto 题负责人。先读公开题面、base 源码和 actor/private 原件，再读题主 partial；随后续核已完成的正式三方、实际导出及 root 冻结 parser。仅本地读证据和计算摘要，未运行项目或远端命令。既有协作上下文可见，不称无上下文盲审。

**确认正式 noop/gold/unconditional_lowercase 为 0/1/1，退化的既有大小写行为回归被唯一来源参考漏掉，支持 S1/T2b 覆盖缺口诊断。原 actor 已成功，不能写成环境修复。gold 只改变错误消息的一条 formatter 路径，原例 reveal 与 index 仍分别显示 `Type` 和 `type`，不能据 formal=1 宣称全部公开目标解决。** 先核题主 [result_partial.md](../tasks/python__mypy-15139/result_partial.md)，再对已落盘的 [最终卡](../tasks/python__mypy-15139/result.md) 及 [机器结果](../tasks/python__mypy-15139/result.json) 窄对照，主事实、P5 范围保留及用途限制均与独立判断一致。

## 公开依据与语义范围

[公开题面](../../../../../../runs/swegym_quality_batch03_20260921_v1/public/python__mypy-15139/user_prompt.txt) 提出错误和 notes 中的别名不一致，允许统一别名或使用代码中的别名，未指定某一 formatter 是唯一规范。报告时的 Windows/mypy 0.961 环境也不等于本次冻结 base 的 Linux/Python 3.11 运行环境；公开命令使用 `--python-version 3.10` 检查原例，不执行该源码字符串。

base `16b936c15b074db858729ed218248ef623070e03` 的 [messages.py](../../../../../../runs/swegym_quality_batch03_20260921_v1/public/python__mypy-15139/base/mypy/messages.py) 第1630行 `reveal_type` 使用 `TypeStrVisitor`；[types.py](../../../../../../runs/swegym_quality_batch03_20260921_v1/public/python__mypy-15139/base/mypy/types.py) 第3188行 `visit_type_type` 固定 `Type[...]`。gold 仅改 `messages.py` 第2519行的错误 formatter，不改该 visitor。实测 gold 原例 reveal 仍为 `Type[builtins.type]`，index 错误变为 `type[type]`，第二条 reveal 仍为 `Any`。因此能确认局部变化与残留两套显示路径，不能把 `builtins.` 消歧前缀本身宣布为错误，也不能替公开题面选择唯一理想输出。

退化不是仅凭 gold 不同判错：[options.py](../../../../../../runs/swegym_quality_batch03_20260921_v1/public/python__mypy-15139/base/mypy/options.py) 第361行规定 Python≥3.9 且未 force 才启用小写；`--force-uppercase-builtins` 在 main.py 中可识别，虽然普通 help 隐藏它。公开 `check-lowercase.test` 有 tuple/list 等 force/no-force 对照；`check-classes.test` 第3377行的 `testTypeUsingTypeCTypeAnyMember` 已明确要求 `Type[Any]` 赋值错误。该旧测在 base/gold 通过，在退化实际失败。这是保持公开既有行为的依据，不等于所有大小写规范已无歧义，也不证明 gold 覆盖整个 issue。

## 实际 actor、依赖固化和私有行为

[原 actor](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/python__mypy-15139/followups_v1/actor_original/attempt.json) 与 [派生 actor](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/python__mypy-15139/followups_v1/actor_revised/attempt.json) 都完成6条命令，CC 2.1.205、UID54321、testbed Python3.11.9，mypy/messages/types 从 `/testbed` 的 `.py` 导入。开始/结束工作树干净，结束 agent 进程0，容器/network/relay/stub 清理均正常、残留空。一般检查字段 `interpreter_in_tool_result` 和 `bashenv_denied_for_agent` 为 false，未把整组 checks 误写为全部 true；实际 identity 命令支持这里的解释器与导入路径判断。

两个 actor 的原例均显示 base 行为，三个赋值命令都以目标诊断 rc1 收口；公开旧测均6 passed/6346 deselected。`all_match_expect=true` 说明命令符合预设退出期待，不代表源码已修复。[依赖固化 receipt](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/python__mypy-15139/followups_v1/actor_build/cpu29_actor_python_mypy_15139_v1/image.json) 的9 wheel 摘要一致、base layers 保留、freeze 增减皆空、pip check=0。原镜像实际 ID `d086e512d094e2790867fe5a30333e43defc76ae59709b9f0aff8ae7d26670b1`；派生 actor `6f59c19c80626a6a4ea88286b128cd4754f821b3816eeb7364283b50423a51e8`。这是依赖固化及历史配方对齐，未观测到原 actor 缺包或修复增益。

[私有 matrix 原件](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/python__mypy-15139/followups_v1/private_behavior) 为派生 actor 镜像上的 root 对照，每变体6条命令 begin/end 及 complete 齐全；prep 未失败，三个容器 rm/query=0、remaining=[]。不能替代 actor 权限或自主解决能力证据。

| 行为 | base | gold | unconditional_lowercase |
| --- | --- | --- | --- |
| 原例 reveal / index 中类型 | `Type[builtins.type]` / `Type[type]` | `Type[builtins.type]` / `type[type]` | 同 gold |
| 现代赋值诊断 | `Type[Any]` | `type[Any]` | `type[Any]` |
| force-uppercase 赋值诊断 | `Type[Any]` | `Type[Any]` | `type[Any]`，违背既有政策 |
| Python3.8 赋值诊断 | `Type[Any]` | `Type[Any]` | `type[Any]`，改变旧目标行为 |
| 公开6旧测 | 6通过 | 6通过 | 1失败/5通过，唯一失败为 CTypeAnyMember |

私有 prep 未记录整文件 SHA；可确认 apply=0、只有 messages.py 修改、实际导入及区别性输出，不能倒写成私有整文件哈希已核。正式实际源码闭环见下段。

## 正式评分、实际源码与清理

正式使用独立 COPY-only 历史 `install_wave1` grader image `cd4daa3006893bd929df21e8174f709049c754926f897eb5630e51524275fccb`。三方 recipe 的 original/revised install 完全相同：`pip install -r test-requirements.txt; pip install -e .; hash -r`。已逐份核完整日志的安装段与测试段：依赖满足、隔离 build dependencies 完成、editable 构建安装成功；没有被末尾 `hash -r` 掩盖的失败。runner 摘要前后一致，导入根 `/testbed/mypy/__init__.py`。

来源 [grading.json](../../../../../../runs/swegym_quality_batch03_20260921_v1/private/python__mypy-15139/grading.json) 只有1个 F2P：`mypy/test/testcheck.py::TypeCheckSuite::check-lowercase.test::testTypeLowercaseSettingOff`，P2P=0。名称虽为 Off，[test.patch](../../../../../../runs/swegym_quality_batch03_20260921_v1/private/python__mypy-15139/test.patch) 实际 flags 是 Python3.9/`--no-force-uppercase-builtins`，只检查赋值错误中的 `type[type]`；不检查 reveal、force 或 Python3.8。正式实际命令只选该1条，11307 deselected；每次解析1状态，无缺席/skip/参考外失败或段外解析。

| 变体 / report 后缀 | 实际完整测试 | reward | 安装/测试秒 | trusted setup秒 | 账本内存峰值MiB |
| --- | --- | --- | --- | --- | --- |
| noop / 39abb7b7 | 1 failed；`Type[type]`≠`type[type]`，RC1 | 0 | 5.185 / 2.424 | 87.294 | 498.379 |
| gold / 943eeede | 1 passed，RC0 | 1 | 4.796 / 2.432 | 74.464 | 492.039 |
| unconditional_lowercase / 62415d21 | 1 passed，RC0 | 1 | 4.758 / 2.416 | 76.651 | 492.855 |

noop 实际投影为空。gold/退化 `candidate.patch` 分别与登记输入逐字节相等；从实际 `frozen_patch.json` 解码整份文件，与公开 base 比较只有预期 TypeType 分支变化，均仅 `mypy/messages.py`、普通文件 mode100644，excluded_pathset_changed=false。实际整文件 SHA：gold `1e7db55e0d15750d8d579232ba0fbd8c3ea718a28e6a973992076c902358b7ef`；退化 `405b802e0a8b4be73f128d90d4d9ce5eba90ffe52ee9632c2a46215b7bd44ba8`。这排除了仅凭补丁名字或 apply Exit0 推断正式候选内容。

三份实际日志已本地计算 SHA 与 ledger 一致，安装和测试起止标记完整、log_partial=false。candidate cleanup removed=true；各 manager_close 创建/移除各1，无 open 容器、supply 或 cleanup failures，最终 exit0。正式运行2CPU/4GiB、UID54322、网络 deny_all、setup900/test1800/whole3600；`resource_facts=null`，上述内存数字不能证明全生命周期无资源事件或最小内存需求。

[完整正式原件](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/python__mypy-15139/followups_v1)；[root 冻结 parser](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/mypy15139_final_v1.json) 与本次逐参考人工核验一致；[root 跨端证据对账](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/evidence_manifest_mypy15139_v1.json) 142份/1,941,966字节、0差异，排除 wheel/image payload。对账的宿主网络列表不等同本题 actor 残留，清理结论依据各 attempt 和 manager 的本题记录。

## 用途与剩余项

支持 S1/T2b 实测误奖诊断：正式 reward1 接受了一个有公开旧测和选项行为回归的候选。不能将 reward1 当作完整公开修复，不能进入无条件能力比较分母或训练资格。当前仅限 formatter/回归覆盖诊断（diagnostic-only）。只有先消解 P5 目标范围、确认可接受的正对照，再另行决定是否开展受限比较；届时仍须固定公开输入、预算与独立语义验收，并将原 reward 与语义结果分列。P5 未解时，不能靠事后语义审计进入比较。D6 正式评分改动、原例目标范围的裁定、真实模型自主解题和训练资格均未由本次 CPU 运行完成。

最终题卡窄对照与本次原件复核均已完成。已反馈题主清除 partial/尚在执行等残留状态文字，并把网络清理依据明确为本题 actor/manager 记录；这些不改变主事实或用途结论。未修改正式题面、测试、评分、候选或运行输入。
