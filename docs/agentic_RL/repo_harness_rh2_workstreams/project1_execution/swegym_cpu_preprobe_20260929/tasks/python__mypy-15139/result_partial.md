# mypy15139：actor 与私有行为部分结果

2026-09-29，`followups_v1`。**原 actor 已可执行这组公开开发检查；依赖派生后的结果相同。gold 只修错误消息的一条 formatter 路径，原例 reveal 仍显示 `Type[builtins.type]`；无条件小写候选实际破坏既有大写政策。正式评分仍在执行，本稿不认定正式误奖或完成验收。** 复用既有静态审查，以下为本批原件读回，不是新盲审。

## 实际开发条件

[原 actor](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/python__mypy-15139/followups_v1/actor_original/attempt.json) 和 [派生 actor](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/python__mypy-15139/followups_v1/actor_revised/attempt.json) 均为 CC 2.1.205、uid 54321、2 CPU/4 GiB，激活 Python 3.11.9。base 为 `16b936c15b074db858729ed218248ef623070e03`；`mypy/messages.py`、`types.py` 均从 `/testbed` 的 Python 源文件导入，未见扩展模块遮蔽。两次开始及结束 git status 均空，六条 Bash 调用完成、完整轨迹已收口、没有命令超时或输出截断。

原 actor 最初 tag 的预取 inspect rc=1；实际运行容器 prelaunch/最终 inspect 的 image ID 均为 `sha256:d086e512d094e2790867fe5a30333e43defc76ae59709b9f0aff8ae7d26670b1`，后续构建原件将它映射到 immutable manifest `a41d688fba76599fcc2bfbfbfe580e864c0c4c6a8ee6ce7edec9b83b34bd0037`。不能把预取 inspect 失败写成 actor 未运行。

[派生构建 receipt](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/python__mypy-15139/followups_v1/actor_build/cpu29_actor_python_mypy_15139_v1/image.json) 确认九个 wheel 与预登记摘要一致、base layers 保留；pip freeze 增减都为空，pip check rc=0。Dockerfile 仅离线安装这些依赖并删除 wheel 缓存，未改项目源码。实际 actor image 为 `sha256:6f59c19c80626a6a4ea88286b128cd4754f821b3816eeb7364283b50423a51e8`。因此这是已装依赖的固化复验，**不是本轮发现缺包后修复**；构建时 pip check 成功仅适用于该 actor image，不代表尚在执行的 grader 安装后状态。

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

[私有完整 matrix](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/python__mypy-15139/followups_v1/private_behavior) 三个变体各六命令均有 begin/end 与 variant complete，子 RC 已逐条核对。它们以 root 在派生 actor image 运行，不替代 actor 权限验证。gold/退化的 apply rc=0，导入确为修改后的 `mypy/messages.py`；远端输入八个 SHA 与本地匹配。但该私有采集未导出 apply 后整份文件 SHA，最终仍须核正式 frozen export 字节，不能只凭 apply rc 声称完成源码身份闭环。

## 公开目标与 formatter 边界

[题面](../../../../../../../runs/swegym_quality_batch03_20260921_v1/public/python__mypy-15139/user_prompt.txt) 允许“统一别名”或“使用代码中的别名”，明确提及错误和 notes。gold 后原例仍同时出现 `Type` 与 `type`，所以不能把局部现代错误格式改善称作已兑现全部公开目标；同时不能擅自把题义收窄为所有显示字符串逐字相同，也不能把 `builtins.` 的消歧用途无条件视作错误。题面记载旧版 mypy/Windows/Python 3.10，当前证据对应题目冻结 base 的 Linux/Python 3.11 运行时和显式 3.10 检查目标，不是旧报告环境的逐项复刻。

公开源码解释了结果：[messages.py](../../../../../../../runs/swegym_quality_batch03_20260921_v1/public/python__mypy-15139/base/mypy/messages.py) 的 `reveal_type` 用 `TypeStrVisitor`；[types.py](../../../../../../../runs/swegym_quality_batch03_20260921_v1/public/python__mypy-15139/base/mypy/types.py) 的 `visit_type_type` 固定输出 `Type[...]`。gold 只改前者错误 formatter 的 `TypeType` 分支。另一处 [options.py](../../../../../../../runs/swegym_quality_batch03_20260921_v1/public/python__mypy-15139/base/mypy/options.py) 明确现代版本且未 force 才用小写；退化直接固定小写，所以 force/旧目标回归有 base 公开契约及旧测试双重依据，不是从 gold 或 reward 反推新需求。

[来源测试补丁](../../../../../../../runs/swegym_quality_batch03_20260921_v1/private/python__mypy-15139/test.patch) 只新增 Python 3.9/no-force 条件下的赋值错误断言，参考为 `testTypeLowercaseSettingOff` 一项 F2P、P2P 空；它静态上没有测试原例 reveal 或大写政策。正式是否将已证退化评为通过，仍等待本批完整原件。

## 预算、清理与剩余项

actor wall=1800 秒，identity=60、各 CLI=180、旧测=300；两次 solve 约 26.7/26.9 秒。私有单 matrix 上限 1230 秒，实际约 15.9/15.1/14.5 秒完成。actor 容器/网络/relay/stub 均清理，残留列表空，结束 agent 进程数 0；私有三容器 rm/query 均0且 remaining 空。未据此推断完整资源事件。

grader 使用独立 COPY-only `install_wave1` image `sha256:cd4daa3006893bd929df21e8174f709049c754926f897eb5630e51524275fccb`，通过 PIP_NO_INDEX/PIP_FIND_LINKS 供应九 wheel；安装 recipe 保持原 test-requirements 与 editable 命令。正式本批统一 CPU setup/reset 上限由300改900秒，test仍1800、whole=3600、candidate-stage=900；这些是当前条件，不证明旧300秒条件通过。此处只记录已生成的配置，不提前确认正式安装/评分完成。

待全部 formal 收口后核 noop/gold/退化的导出整文件、安装/完整 test RC、唯一参考及参考外结果、日志和两层清理，再交独立审查及 root parser/传输对账。当前仅用于开发条件与题义/覆盖诊断，既不能进入无条件能力比较分母，也不授予训练资格；原例范围问题和 D6 未实施继续保留。[机器部分结果](result_partial.json) 保存已读输出、逐子命令 RC 和证据 SHA。本稿只读本地同步原件，未远端执行、重跑或修改在途输入。
