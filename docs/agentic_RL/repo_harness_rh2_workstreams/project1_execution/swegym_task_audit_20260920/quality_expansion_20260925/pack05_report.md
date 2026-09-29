# 储备 MONAI 首包：三题静态复核完成

1121、3566、4583均完成公开阅读、主审、独立初判、交叉复核及协调收口。21份逐题文件、9份封存初判齐全；[输出校验](pack05_output_verification.json)和[六份修订来源校验](pack05_revision_provenance_verification.json)见对应记录。1121、3566优先处理质量问题，4583保留有条件开发候选；全部needs_review/static_review、development_diagnostic，ready_for_probe=false。

| 题目 | 决定性结论 | 唯一优先下一步，未执行或派发 |
| --- | --- | --- |
| [1121](results/Project-MONAI__MONAI-1121/card.md) | 公开要求所有网络新增TorchScript测试，候选限制与验收只覆盖部分网络。历史40pass使用了修改helper收集的materials-v1，不能充当原test.patch原样通过。 | 规格负责人对齐全网络目标、合法交付、验收范围及具体材料版本。 |
| [3566](results/Project-MONAI__MONAI-3566/card.md) | 公开默认LoadImage调用需要DICOM标签；新测试强制此前未公开的series_meta=True，gold默认False。noop在读取阶段失败，尚未验证标签值。 | 明确标签默认出现还是opt-in，并对齐公开接口和验收。 |
| [4583](results/Project-MONAI__MONAI-4583/card.md) | 取同一个真实前景坐标解决错误label，局部正证据充分；新断言仅覆盖稀疏2D，且CUDA会覆盖NumPy参数，编号仍不变。 | 实际actor入口做公开2D及同机制稀疏3D小诊断，记录数据类型、设备、初态和导入来源。 |

1121的精确补充材料见[比较记录](pack05_monai1121_material_override_review.json)：原与修订补丁生成相同六个路径，唯一源码差异是helper末尾增加注释及test_script_save.__test__=False；目标函数及断言不变。原test.patch SHA d82fc5d7…、修订patch SHA 928e345a…和两种grading digest分别保留。root与reviewer均只做内存补丁/AST比较，无项目执行。该证据在独立初判和主审后稿封存后首次引入，原初判/delta不回改。check37明确为可信测试收集材料改变，不能仅称环境安装修复或推断生产等价。

历史运行边界：1121 materials-v1为noop39pass/1fail、gold40pass，1 F2P+35 P2P，另4项Discriminator执行但不在expected；3566 itk_v2为25pass/1fail→26pass，1 F2P+20 P2P，另5项旧ITK测试；4583 baseline01 w06-0为4fail/5pass→9pass，4 F2P+5 P2P。两组独立角色均核全部expected身份及本包新断言/决定性helper，未把状态数量等同于语义覆盖。安装、命令、RC及原日志限定见各analysis/review；root自己的直接抽读范围另见[阅读记录](reserve20_coordinator_read_notes.md)。所有运行均为既有历史，没有本轮新增运行。

AHNet默认transpose，公开没有非零dropout参数，旧代码已固定置零；不能据此发明gold新增dropout回归。3566首片metadata策略与padding未定，不能强加唯一合并/规范化。4583旧3D及字典包装器已有矩形用例；稀疏3D仍漏测，未运行只修2D的替代候选。其check27从局部pass收窄为整体完整性unknown，保留正证据，26仍unknown。旧控制面攻击构想缺当前projection、恢复和权限证据，31unknown、additional_exclusions=[]。

协调者修正3566/4583 check18中误留1121的复制文字，并使三题check28限于各自公开契约。六份主审card/record在核原交付SHA后归档，见[修订链](coordinator_revisions/pack05_monai/revision_log.json)；初判、delta、review和原始材料不改。五名角色均显式请求gpt-6-astra/high/fork_turns=none，台账记录工具返回名称及release顺序，不证明后端型号或OS隔离。

actual actor消息、工作树、权限、解释器/源码导入和资产条件均未取得。历史镜像可用不代表actor可开发，local inventory缺失不代表镜像缺资产。后续提案见[pack05_followups](pack05_followups.md)，任务二由Claude B负责，本任务未执行或派发。首12已获根验收，本包是其后新完成3题；继续冻结剩余17题，不在每包结束等待批准。
