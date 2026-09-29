# Pydantic5706：独立结果复核

2026-09-29。**正式 noop=0、gold=1、sequence_list=1；退化的 source-only 补丁实际破坏 Python Sequence 既有行为，四项公开旧测失败却通过全部正式参考，确认 S1 覆盖漏检。症状匹配修正有效，P5 目标方向仍未消解，当前仅作诊断。** 这是跨包独立复核，复用上下文及此前脚本审查，不是 fresh 盲审；先读公开题面、源码、候选和运行原件，再读题主 `result_v2_partial.md`。没有远端操作、项目/容器执行或生产修改。

运行根：[symptom_v2_20260928T201808Z-232b80](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-5706/symptom_v2_20260928T201808Z-232b80)。旧失败及其绑定说明见[脚本窄审](pyd5706_symptom_v2_review.md)，旧原件不回写。

## 公开依据与 actor

[原题面](../../../../../../runs/swegym_quality_batch01_20260921_v2/public/pydantic__pydantic-5706/user_prompt.txt) 将 schema 生成失败称为似乎正确，并提出 validate_json 应同步拒绝的方向；来源 gold/测试则支持 Sequence 的 JSON schema/JSON 输入。这个 P5 方向差异不能用 gold 满分或补一个行为后检消解。当前用途仍为 diagnostic-only；先消解目标范围并确定可接受正对照，才有讨论受限比较的前提，不能直接进比较分母或训练。

新 actor 只有一条 Bash 症状命令：在固定 core0.31.0 捕获 `PydanticInvalidForJsonSchema`/`IsInstanceSchema` 和精确 `NotImplementedError: Cannot check isinstance when validating from json,use a JsonOrPython validator instead.`，然后到达 `BASE_CORE031_PUBLIC_SYMPTOMS_CONFIRMED`，rc0。它没有假装题面 core0.25.0 的 ValidationError 已重现。prelaunch/activation通过，CC2.1.205，base/image与旧轮一致，完整轨迹无截断，清理container/network/relay/stub完成，结束agent进程0。

原identity和两组回归复用已核SHA的旧actor，不能写成新轮又跑了三条；旧identity为uid54321、Python3.8.19、core0.31、checkout导入。初始 `pdm.lock`、`pyproject.toml` 已dirty，新轮结束git状态仍为2行；这些既有元数据差异不是source-only候选修改，也不能称为pristine基线。

## 私有回归与实际候选

[私有矩阵](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-5706/symptom_v2_20260928T201808Z-232b80/private_sequence_list/sequence_list/private_matrix.out)直接记录两个退化子命令rc1，helper/matrix整体rc0仅表示识别出预登记失败。base/gold均保留list/tuple/range/deque类型和值，旧六测均6 passed；退化将tuple/deque变list、range报`list_type`，旧测4 failed/2 passed，第四个失败是tuple-of-tuples外层也变list。三个变体均先收集六项成功、完整命令结束标记齐全，三容器rm/query均0、remaining空。私有身份为root，不替代actor权限证明；gold/退化没有运行“必须产生base异常”的症状命令。

这些回归有[公开 base 的 `test_sequence_success`](../../../../../../runs/swegym_quality_batch01_20260921_v2/public/pydantic__pydantic-5706/base/tests/test_types.py)直接依据：明确列出tuple、range、deque、tuple-of-tuples期待值，不由JSON题义争议或gold实现反推。私有四类型探针额外检查精确类型，旧六测本身的值比较已独立拒绝退化，因此无需仅依赖新增类型断言成立。

正式已导出的两份candidate.patch与v2输入逐字相同；解码整文件并与公开base对比，gold仅改`_generate_schema.py`的Sequence生成路径，60545字节，SHA `82a04ddea65392cf028fecf3acb54c36ef6975540d24b483a74403d5c5fc4522`。退化仅在`_std_types_schema.py`添加`collections.abc.Sequence: list`，36471字节，SHA `7bae36e523323b768de09a8fa885f52217b47a75943408848dae9514f1645f4c`；各自只投影一个源码文件（mode100644），excluded_pathset_changed=false，noop无entries。私有未另导出apply后完整文件SHA，不能把正式导出倒签成私有实测hash；输入匹配、实际apply/导入及退化行为已记录。已另核退化正式完整测试及清理，不以导出完成代替评分完成。

## 已完成的正式参考、安装和清理

八个公开wheel下载日志与清单的文件名/大小/SHA一致，base13层保留，派生image `d8e8a4475e62b5c38ec3629a6ed33bad147ef915084d311f1571325285dbb943` 加一COPY层；本地未同步wheel payload，不声称本地重hash。三方均实际执行editable安装，再从当前pyproject提取testing/testing-extra安装；包括原dirty元数据中的pre-commit依赖，被报告为already satisfied。没有跳过候选安装，没有升级core，安装后的导入为`/testbed/pydantic/__init__.py`、core0.31，runner摘要前后相等。

正式只执行 `pytest -rA --tb=short -vv -o console_output_style=classic --no-header tests/test_json_schema.py`。来源参考均来自这个文件；[测试补丁](../../../../../../runs/swegym_quality_batch01_20260921_v2/private/pydantic__pydantic-5706/test.patch)中的两个Sequence F2P检查schema，后一项还调用JSON验证。`tests/test_types.py`中的六项Python容器回归不在这条命令或273 P2P内。

| 检查 | noop | gold | sequence_list |
| --- | --- | --- | --- |
| 2个F2P逐键 | 均FAILED，目标IsInstanceSchema异常 | 均PASSED | 均PASSED |
| 273个P2P逐键 | 全PASSED | 全PASSED | 全PASSED |
| 完整测试 | 2 failed / 275 passed / 1 xfailed | 277 passed / 1 xfailed | 277 passed / 1 xfailed |
| 安装RC / test RC / reward | 0 / 1 / 0 | 0 / 0 / 1 | 0 / 0 / 1 |
| 安装 / 测试秒数 | 4.443 / 3.392 | 4.205 / 2.576 | 4.122 / 2.647 |

每份完整日志逐行核278个状态，全部275参考出现一次且无skip；额外两个PASS是带空格参数名的callable非可序列化默认值测试，额外XFAIL是`test_get_pydantic_core_schema_calls`，均非来源参考。无额外失败或导入/收集故障，完整test结束标记齐。noop/gold完整eval.log SHA分别`259fb48b685622ce5094a9a9d9f7ac69dc03f146f7d5bc0eaf35378cf14d978e`、`340a94a198cc7841d4715072b539454cd0faeb8286814e91b5d8f45591eadfa0`，本地重算与ledger一致。退化完整日志SHA为`98a14ed851bfd70bbcb1a9e0a88284a4ff6da9d73206589bebe2d0ad7d71c99e`，同样匹配ledger。

三个candidate均removed=true；原driver尾部manager close分别created=removed=1，containers_open/supply_open/cleanup_failures空，final exit0，双层清理完成。setup约170.798/162.298/159.222秒，内存峰值678.469/672.586/673.059 MiB；2CPU/4GiB、setup900/test1800/whole3600条件不变。resource_facts=null，不能据峰值宣布完整生命周期无资源事件。

## 完整结论、对账与剩余边界

退化正式运行前diff仍只在目标源码增加Sequence→list映射，原有dirty锁文件/pyproject与来源环境有关；实际候选投影不包含这些元数据。测试确实运行到完整结束、源码/依赖导入已核、参考全覆盖，所以正式1分不是候选未生效、安装失败或parser误计造成，而是JSON模块没有执行已知Python类型/值回归。gold的JSON参考通过不能消解P5，也不能由来源实现反推题义。

[root冻结parser](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/pyd5706_final_v2.json)三行report及每行275参考均与本次直接读回一致。[传输对账](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/evidence_manifest_pyd5706_v2.json)覆盖旧失败与v2共115件、1,922,316字节，远端/本地SHA无差异。宿主最终容器列表为空，仅保留bridge/host/none默认网络；本题actor与两层评分清理原件也各自确认结束。status为executed_pending_review，不能把这个调度状态当作题目合格。

先读原件后对照[题主v2 partial](../tasks/pydantic__pydantic-5706/result_v2_partial.md)，随后已窄核[最终题卡](../tasks/pydantic__pydantic-5706/result.md)及 result.json：三方0/1/1、275参考与完整278节点、实际候选、安装/清理、S1/T2b及P5仅诊断限制均一致。最终题卡独立对齐完成，无新增阻断。当前可核销运行原件、实际候选、逐参考、完整安装/测试、清理与root对账项；D6未实施、P5范围未解，公开材料真实交付及自主模型/训练资格仍未由本轮证明。现成公开六参数回归可供后续R-c复用，但不能以增加后检绕过P5；先明确目标及正对照，再决定后续用途。
