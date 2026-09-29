# iterative__dvc-3665 — 旧结论差异

封存 SHA256 `ca034ff97ae32a9335442ac8d69454537e447412f1fe48b3c6ab2b3354d29041`。协调者于 UTC 2026-09-20T21:15:26.703975+00:00 放行后，才读本题 history/refs.json 与唯一旧记录 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dvc_1/records/iterative__dvc-3665.json`。封存未回写。路径 P/V/R 见封存稿。

| 旧主张/行号 | 处置 | 本次决定性证据 |
| --- | --- | --- |
| 4 F2P强制未公开helper，内联修复可能误拒 (:94-108,177-187) | 确认静态结构问题；未声称实际合理候选已验 | V/test.patch:57-67、base config.py:315-326；最新noop日志:630-687仍是4次AttributeError。旧记录也只写“下一实验”，没有完成的反例可沿用。措辞收窄为强制一个内部接口，不必夸大为必须照抄整个upstream。 |
| Linux功能改动无法测Windows，只加未接线helper也可能满分 (:111-117) | 确认高置信静态路线 | Linux noop29旧测试通过，4新用例仅当前平台path；全部新增/修改断言读完。尚未执行partial candidate，仍须区分静态与真实评分反例。 |
| 11项实际通过却未列P2P，核心cache relative也遗漏 (:119-127,200-210) | 确认范围差异，不采自动重建P2P | 新双角色33真实摘要与22引用逐项差为11，见封存§3。最相关cache相对测试未计分是具体缺口；其余不能仅按“双侧通过”就自动改成正式门槛。任何变更参考都是版本修订，不能静默扩reward。未读旧聚合p2pcov。 |
| os.getcwd生成/testbed身份，移动目录即不匹配 (:84-92,189-198) | 确认可移植性限度；当前无缺席 | test.patch:62 与 grading引用对应；真实cwd=/testbed、两ledger missing=[]。这是当前明确workdir契约外的风险，不与已触发helper问题并列称现有接线故障；不需要本题顺带扫描216题。 |
| gold功能正确、import整理无关 (:129-135) | 确认静态目标路线，限制“正确”范围 | gold只改config；PathInfo.as_posix按平台sep转换，Linux33 passed；尚无Windows/UNC实跑，不能升级为跨平台已验。import整理不是评分缺陷。 |
| 环境干净、权限通过 (:146-174,240-242) | 推翻“干净”的笼统说法并更新条件 | 本题noop日志:132-139,186-198真实有setup.py moto pin变化；gold亦有。最新是离线editable安装的rh2grader54322，不是旧root运行；两ledger env_qualification=absent，actor未知。 |
| 官方3纯测试路径可恢复、排除空 (:56-73,213-220) | 确认最新原件适用结论 | 新diagnostics记录restored2、testfiles3、setup/protect OK；projection gold只config。不能拿旧行号当当前代码；本次用dvc冻结归档与日志。 |
| 与1808同侧划分 (:75-82) | 未核实并不采自动划分 | 本题确有test_overwrite旧行为，但未在本次范围读1808补丁/精确commit，不按同文件/同测试名确认派生或要求同侧。保留旧关系线索，不读邻题。 |
| hints空、泄漏pass、成本26分钟 (:48-54,137-144,244-246) | 限制旧来源、当前未知 | 当前bundle有harness public_hints；实际模型消息/镜像可见资产未验，旧估时不作本轮成本。 |
| needs_repair并“三处都改材料或接线” (:240-242) | 改为needs_review/static_review | helper和Windows行为验收有实质争议；workdir当前匹配，P2P不自动扩大。本轮静态不执行修改/反例，不把提议当已批准修订。 |

新发现补充：42个解析键并非42个实际测试；已通过冻结 parser 源码和日志分词元数据核出33 nodeid+9业务ERROR伪键。这9键不撞22引用，未改变本题reward；保存为解析计数限度。主审核心结论和唯一下一实验不因历史改变：先对不新增helper的合理内联修复做窄Windows行为与冻结RH2对照，明确误拒证据后再讨论行为测试修订。
