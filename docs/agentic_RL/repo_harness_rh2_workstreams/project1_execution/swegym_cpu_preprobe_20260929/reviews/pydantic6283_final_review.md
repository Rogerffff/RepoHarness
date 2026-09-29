# Pydantic6283：完整CPU结果跨包独立复核

2026-09-29。**三候选正式校准有效：noop=0、gold=1、validate_construct=0；所测退化被两项已有P2P正确拒绝，本次没有证明正式误奖。** 不验证控制有直接公开文档和旧测试依据，不是从gold或私有期望反推新要求。该结论只覆盖本次候选与任务范围，不因一个候选被拒绝就解除所有历史风险，也不要求无界全仓验证。

审查顺序为公开原题面／base源码与文档、实际命令和patch、私有与正式完整日志及导出，再对照root冻结parser逐参考，最后读题主result。没有执行远端、容器或历史项目。审查者未编写该题输入／题主结果，属于复用既有上下文的跨包独立核验，不称新盲审或OS隔离证明。

## 公开依据与行为边界

公开根目录：`runs/swegym_quality_expansion_20260925/public/pydantic__pydantic-6283/`。`user_prompt.txt`要求同样有效且类型正确的值经RootModel普通初始化与model_construct得到相等对象，并给BaseModel对照；它没有授权把model_construct改为验证构造。

已有契约有三层直接依据：base `pydantic/main.py:179–190`明确trusted/pre-validated数据只处理默认值、不执行其他验证；`docs/usage/models.md:402–478`明确无验证、可以构造无效模型，给`User.model_construct(id='dog')`例子，说明RootModel可位置传root，且不调用任何`__init__`；旧`tests/test_root_model.py:182–200`直接要求可信Base64Str原样构造，不把它重新解码，也不自动把嵌套原始值转换成模型。

因此私有 `RootModel[int].model_construct('not-an-int')`保留字符串控制检查的是公开“不验证”契约，而不是要求无效值正常通过验证。候选`return cls(values['root'])`跨越这一边界。即使不使用该新控制，两个旧公开测试已经足以判定其退化；不依赖gold通过才成立。

## 原始运行与正式参考

证据根：`runs/swegym_cpu_preprobe_20260929/remote/results/pydantic__pydantic-6283/followup_20260928T184018Z-6ec4ba/`。

| 候选 | 原例与私有行为 | 正式F2P / P2P | reward；完整正式输出 |
| --- | --- | --- | --- |
| base/noop | ROOT_EQUAL False；旧root41通过3xfail；共享construct44通过；不验证控制通过 | 0/1；38项全过 | 0；1 failed/40 passed/3 xfailed |
| gold | ROOT_EQUAL True；旧root41通过3xfail；共享construct44通过；不验证控制通过 | 1/1；38项全过 | 1；41 passed/3 xfailed |
| validate_construct | ROOT_EQUAL True；旧root2失败39通过3xfail；共享construct44通过；不验证控制int_parsing ValidationError | 1/1；36过2失败 | 0；2 failed/39 passed/3 xfailed |

正式F2P是`tests/test_root_model.py::test_root_model_equality`；noop精确失败于初始化与construct不相等，gold及错误候选均通过。错误候选的两个P2P失败为`test_construct`和`test_construct_nested`，完整日志都进入候选新增`cls(values['root'])`后发生Base64Str重新验证的UTF-8解码ValidationError。不是导入、collection、超时或安装失败，亦不是新增私有断言影响了正式分数。

root冻结parser的每行39参考（1+38）已逐键在原日志找到对应状态；参考缺席0、参考外失败0、测试前错误0。三项xfail是既有非参考项，不计为目标失败，也不拿44个执行项代替39参考。三份eval SHA与ledger记录吻合，安装/test起止marker与rc完整。

## 实际候选与安装身份

gold与validate_construct的正式candidate.patch逐字匹配对应task_inputs；SHA256分别`cf1db83c2966404d60f40d33ddee5aa197fe1e12f5a8147fb76076a4f541c64c`和`a3ee895dc358cda2b3be2c1e43e09fd9cf163f29b30799cc2ab6223621bef60d`。另对frozen_patch解码完整文件，纯文本按hunk重建公开base加patch，逐字相同，仅`pydantic/main.py`被导出；源码SHA分别`2a6ba2b34275a9b41065e958e62762160ba675be037e77211a1319bd3e624c3f`、`709ba1bfe57c25dedf580245afbd2b10dad41f84b9e1db56424e8239fdc3ba3f`。因此实际评分候选与行为对照对应，不只依赖候选名称。gold通过避免为RootModel写入额外的extra/private状态来恢复相等，没有引入验证。

三次正式安装均成功构建／editable安装pydantic2.0b3，install_failed_commands为空、rc0；实际导入`/testbed/pydantic/__init__.py`、core0.42.0，runner前后相同。三次apply_ok、test收口及容器清理正常，grade日志manager_close均open容器空、cleanup failures空、最终退出0。应与测试rc的预期0/1分别解释。

三个私有root变体均准备和collect-only成功，四条行为命令的begin/end及variant complete齐全，rm/query均0、remaining空。private_matrix整体rc0表示预期对照跑完；错误候选内两类行为命令实际rc1，不能写成业务全部通过。私有root不替actor权限证明。

actor公开原件另确认UID54321、CC2.1.205、Python3.8.19、base `a29286609e79c79b2ecd71bc7272eea43ed9fccd`、core0.42.0，四条命令完整配对，目标精确复现，旧root和共享construct通过，清理正常。已有pdm.lock/pyproject.toml差异作为镜像初态保留，不能混作候选修改；Devcheck消息仍不证明真实题面/public_hints已交付。

## 题主对照与结论使用

补读当前完整题主`tasks/pydantic__pydantic-6283/result.md`后，正式0/1/0、全部参考、导出、安装与清理事实与本独立复核一致。出稿时曾列的“正式账本未回传”已由完整结果取代；本次跨包结果复核和root冻结parser重放亦已完成，不应继续列为未做。

同时明确保留题主的**S1/T2c示例覆盖限制**：新增核心相等目标仍只检查合法整数42。两个已有P2P拒绝validate_construct，证明的是这类重新验证的退化受到约束，不能推出一般构造相等目标已经超出示例充分覆盖，也不解除S1。该限制与“本次没有观察到validate_construct误奖”同时成立。

题主现已准备非42的合法字符串RootModel实例草案，依据是公开题面的一般“同样合法且类型正确的值”，无需增加内部状态规范。该补充材料尚未执行，不在本次独立验收范围，不能宣称base/gold对它的结果已知。D6正式接入仍未实施；受限比较、训练／留出、完整题面/public_hints交付与模型/GPU资格继续按题主记录约束。本次不重跑已完成的actor/private/formal，也不为单次候选结论追加无界验证。

逐参考重放入口：`runs/swegym_cpu_preprobe_20260929/analysis/pydantic6283_followup_v1.json`。本次读回及静态字节核对无需重跑项目或追加新条件。
