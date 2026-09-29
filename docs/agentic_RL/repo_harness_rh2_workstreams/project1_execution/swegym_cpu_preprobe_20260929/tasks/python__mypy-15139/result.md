# mypy15139：最终 CPU 结果

2026-09-29，`followups_v1`。**正式 noop=0、gold=1、无条件小写退化=1；退化实际破坏 force-uppercase/Python 3.8 显示政策及一项公开旧测试，确认 S1 覆盖缺口。原 actor 已可运行本组检查，依赖派生结果相同。** gold 的原例仍同时显示 `Type` 与 `type`；这一现象是否属于本题必须统一的全部范围尚未消解，不能用正式1分解除用途限制。题主已读回正式原件、root冻结parser及传输对账；[跨包独立最终复核](../../reviews/mypy15139_result_review.md)及本卡对齐已完成。保留 [partial 历史](result_partial.md)，本卡是当前入口。

## 实际开发条件

[原 actor](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/python__mypy-15139/followups_v1/actor_original/attempt.json) 和 [派生 actor](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/python__mypy-15139/followups_v1/actor_revised/attempt.json) 均为 CC 2.1.205、uid 54321、2 CPU/4 GiB，激活 Python 3.11.9。base 为 `16b936c15b074db858729ed218248ef623070e03`；`mypy/messages.py`、`types.py` 均从 `/testbed` 的 Python 源文件导入，未见扩展模块遮蔽。两次开始及结束 git status 均空，六条 Bash 调用完成、完整轨迹已收口、没有命令超时或输出截断。

原 actor 最初 tag 的预取 inspect rc=1；实际运行容器 prelaunch/最终 inspect 的 image ID 均为 `sha256:d086e512d094e2790867fe5a30333e43defc76ae59709b9f0aff8ae7d26670b1`，后续构建原件将它映射到 immutable manifest `a41d688fba76599fcc2bfbfbfe580e864c0c4c6a8ee6ce7edec9b83b34bd0037`。不能把预取 inspect 失败写成 actor 未运行。

[派生构建 receipt](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/python__mypy-15139/followups_v1/actor_build/cpu29_actor_python_mypy_15139_v1/image.json) 确认九个 wheel 与预登记摘要一致、base layers 保留；pip freeze 增减都为空，pip check rc=0。Dockerfile 仅离线安装这些依赖并删除 wheel 缓存，未改项目源码。实际 actor image 为 `sha256:6f59c19c80626a6a4ea88286b128cd4754f821b3816eeb7364283b50423a51e8`。因此这是已装依赖的固化复验，**不是本轮发现缺包后修复**；构建时 pip check 成功仅适用于该 actor image，不代表grader 安装后状态。

## 精确 CLI 与行为

[公开命令原件](../../../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs/python__mypy-15139/public_commands.json) 使用 `python -m mypy --config-file= --no-site-packages --no-incremental --cache-dir=/dev/null`，原例固定目标 Python 3.10。检查的是源码字符串，没有运行 `type[type]` 表达式。三条赋值控制同为 `Type[Any]` 赋给 `int`，分别指定现代默认、`--force-uppercase-builtins`、目标 Python 3.8。

| 检查 | 原/派生 actor 与私有 base | 私有 gold | 私有 unconditional_lowercase |
| --- | --- | --- | --- |
| 原例第一条 reveal | `Type[builtins.type]` | 同左 | 同左 |
| 原例 index 错误中类型 | `Type[type]` | `type[type]` | `type[type]` |
| 原例第二条 reveal | `Any`，完整 CLI rc=1 | 同左 | 同左 |
| 现代赋值错误 | `Type[Any]`，rc=1 | `type[Any]`，rc=1 | `type[Any]`，rc=1 |
| 强制大写赋值错误 | `Type[Any]`，rc=1 | `Type[Any]`，rc=1 | **`type[Any]`，rc=1** |
| Python 3.8 赋值错误 | `Type[Any]`，rc=1 | `Type[Any]`，rc=1 | **`type[Any]`，rc=1** |
| 六项公开旧测 | 6 passed，rc=0 | 6 passed，rc=0 | **1 failed / 5 passed，rc=1** |

旧测命令为 `python -m pytest -n0 -rA --color=no mypy/test/testcheck.py -k "testTypeUsingTypeCTypeAnyMember or testListLowercaseSetting or testTupleLowercaseSetting"`；收集 6352、选中 6、排除 6346。退化唯一失败为 `testTypeUsingTypeCTypeAnyMember`，完整 diff 明确期望 `Type[Any]`、实得 `type[Any]`。所有 CLI rc=1 均有目标诊断和 `Found 1 error` 收口，不是依赖、导入或收集失败；`expect:any/nonzero` 本身不作为语义通过证明。

[私有完整 matrix](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/python__mypy-15139/followups_v1/private_behavior) 三个变体各六命令均有 begin/end 与 variant complete，子 RC 已逐条核对。它们以 root 在派生 actor image 运行，不替代 actor 权限验证。gold/退化的 apply rc=0，导入确为修改后的 `mypy/messages.py`；远端输入八个 SHA 与本地匹配。该私有采集未导出 apply 后整份文件 SHA；本轮已核正式 frozen export 精确等于同一公开 base 加对应输入补丁，并核正式运行前 diff。它支持两组对照使用相同指定变更，不倒签一份未采到的私有文件测量。

## 公开目标与 formatter 边界

[题面](../../../../../../../runs/swegym_quality_batch03_20260921_v1/public/python__mypy-15139/user_prompt.txt) 允许“统一别名”或“使用代码中的别名”，明确提及错误和 notes。gold 后原例仍同时出现 `Type` 与 `type`，公开展示的不一致现象仍在；是否属于本题必须统一的范围尚未消解，故不能认定完整修复，也不进入比较分母。这里保留 P5 解释边界，不无条件宣称 gold 违反全部题义；不能把题义收窄为所有显示字符串逐字相同，也不能把 `builtins.` 的消歧用途无条件视作错误。题面记载旧版 mypy/Windows/Python 3.10，当前证据对应题目冻结 base 的 Linux/Python 3.11 运行时和显式 3.10 检查目标，不是旧报告环境的逐项复刻。

公开源码解释了结果：[messages.py](../../../../../../../runs/swegym_quality_batch03_20260921_v1/public/python__mypy-15139/base/mypy/messages.py) 的 `reveal_type` 用 `TypeStrVisitor`；[types.py](../../../../../../../runs/swegym_quality_batch03_20260921_v1/public/python__mypy-15139/base/mypy/types.py) 的 `visit_type_type` 固定输出 `Type[...]`。gold 只改前者错误 formatter 的 `TypeType` 分支。另一处 [options.py](../../../../../../../runs/swegym_quality_batch03_20260921_v1/public/python__mypy-15139/base/mypy/options.py) 明确现代版本且未 force 才用小写；退化直接固定小写，所以 force/旧目标回归有 base 公开契约及旧测试双重依据，不是从 gold 或 reward 反推新需求。

[来源测试补丁](../../../../../../../runs/swegym_quality_batch03_20260921_v1/private/python__mypy-15139/test.patch) 只新增 Python 3.9/no-force 条件下的赋值错误断言，参考为 `testTypeLowercaseSettingOff` 一项 F2P、P2P 空；它静态上没有测试原例 reveal 或大写政策。本批正式已将该退化评为通过。force/旧版本和旧测回归的漏检有独立公开依据，不依赖上述 reveal 范围争议。

## 正式评分、实际导出与逐参考

[三方正式原件](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/python__mypy-15139/followups_v1) 均真实执行 `python -m pip install -r test-requirements.txt; python -m pip install -e .; hash -r`。requirements 已满足，editable 构建和安装成功；安装未跳过，失败命令列表空、安装末 RC=0。测试命令均为 `pytest -n0 -rA -k testTypeLowercaseSettingOff`，收集 11308、排除 11307，只运行一个现代默认显示测试。完整日志没有缺失结束段、导入/收集失败或参考外失败。

| 项目 | noop | gold | unconditional_lowercase |
| --- | --- | --- | --- |
| reward / 完整 test RC | 0 / 1 | 1 / 0 | 1 / 0 |
| 唯一 F2P | FAILED | PASSED | PASSED |
| P2P | 0项 | 0项 | 0项 |
| pytest 收口 | 1 failed | 1 passed | 1 passed |
| 安装/测试秒数 | 5.185 / 2.424 | 4.796 / 2.432 | 4.758 / 2.416 |

唯一精确 nodeid 为 `mypy/test/testcheck.py::TypeCheckSuite::check-lowercase.test::testTypeLowercaseSettingOff`。noop 的完整 diff 是预期 `type[type]`、实际 `Type[type]`；不是基础设施失败。三个状态与[root冻结parser重放](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/mypy15139_final_v1.json)一致，无缺席、skip 或段外测试状态。私有六项旧测不在正式选择范围；不能把“已收集”写成“已执行”。

两份 `candidate.patch` 与输入字节一致。解码正式 frozen artifact 的全部 `mypy/messages.py` 后，gold 为120569字节，SHA `1e7db55e0d15750d8d579232ba0fbd8c3ea718a28e6a973992076c902358b7ef`；退化为120490字节，SHA `405b802e0a8b4be73f128d90d4d9ce5eba90ffe52ee9632c2a46215b7bd44ba8`。逐字节等于公开 base 仅施加对应单一 hunk；gold 用 `options.use_lowercase_names()`，退化无条件返回小写。两者只投影该文件（mode100644），noop entries为空，`excluded_pathset_changed=false`；实际运行前 `git diff` 与此相符，没有候选测试改动。

三份完整 eval.log SHA 均与 ledger 匹配；安装前后 runner digest 均为 `bffa1d1e04c07d52b4d5db5941f0d97a8c71a68e29cca90c4bf5671ea66e1548`，导入为 `/testbed/mypy/__init__.py`。源码投影、实际行为和正式单键通过共同支持确定的政策回归漏检；没有用 parser计数代替真实命令结论。

## 预算、清理与剩余项

actor wall=1800 秒，identity=60、各 CLI=180、旧测=300；两次 solve 约 26.7/26.9 秒。私有单 matrix 上限 1230 秒，实际约 15.9/15.1/14.5 秒完成。actor 容器/网络/relay/stub 均清理，残留列表空，结束 agent 进程数 0；私有三容器 rm/query 均0且 remaining 空。未据此推断完整资源事件。

grader 使用独立 COPY-only `install_wave1` image `sha256:cd4daa3006893bd929df21e8174f709049c754926f897eb5630e51524275fccb`，通过 PIP_NO_INDEX/PIP_FIND_LINKS 供应九 wheel；安装 recipe 保持原 test-requirements 与 editable 命令。正式本批统一 CPU setup/reset 上限由300改900秒，test仍1800、whole=3600、candidate-stage=900；这些是当前条件，不倒签旧300秒条件。实际 trusted setup分别87.294/74.464/76.651秒，三方均完成。ledger内存峰值约498.379/492.039/492.855 MiB，但 `resource_facts=null`，不能据峰值替代全生命周期资源事件证明。

三次 candidate cleanup 均 removed=true；driver尾部 manager close 的 created=removed=1，containers_open、supply_open、cleanup_failures均空，最终退出0，两层清理完成。root 的[传输对账](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/evidence_manifest_mypy15139_v1.json)覆盖142件已结束原件、1,941,966字节，远端/本地SHA一致；本题 actor/manager 记录确认任务资源已清理，manifest 仍列出 bridge/host/none 三个宿主网络，不将它们称作本题残留。此范围不等于资源全程无事件。

当前只用于开发环境、显示政策及覆盖诊断，不进入能力比较分母或训练奖励。剩余项明确区分：原例 reveal/错误显示的 P5 范围及可接受正对照；D6 的版本化测试修订实施。可复用现有 `policy_force`、`policy_old` 和失败旧测作有公开依据的 R-c 控制，保留现代默认控制；如果先补公开旧测 P2P，还须同步让正式命令实际执行它，单加参考键不足。reveal 的正式新断言须在范围消解后定，不把 gold 输出自动当需求或正对照。自主模型、公开材料真实交付、模型/GPU预算与训练资格仍另行管理。

[机器结果](result.json)保存三方ledger、完整源码摘要核对、逐参考、命令RC及证据SHA。历史raw/partial不改；本轮只读本地原件并写题卡，未重跑、修改正式材料或操作远端。
