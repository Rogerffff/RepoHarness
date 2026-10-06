# 私有主审（09-25）

协调者只给本包精确题单、各题PUBLIC_DIR/PRIVATE_DIR/OUTPUT_DIR、已封存public_read及允许的原运行引用。新上下文，不继承协调者结论。初期禁止本包任何history/旧质量结论、其它包题目/聚合、reviewer输出及根结论。

先完成包内每题全部独立原件分析，并分别写analysis_before_history.md。包内全部初稿保存并由协调者核SHA256后，只有收到明确release才可读各题自身history refs和指定旧记录；不得沿旧报告跨题或聚合扩读。再写每题old_findings_delta.md、card.md、screening_record.json。前稿不可改，后稿说明纠正或分歧。

每题检查八方面：公开目标；版本/初态；全部新增或修改断言及fixture/helper、逐个F2P、受影响P2P和实际选择/日志；合理非gold实现与误拒；gold/调用者/边界回归；开发操作、资产、网络、权限、资源；合法交付与可信测试恢复；具体关系、答案暴露与用途。核心是双向需求—断言表：公开要求/合理旧行为→依据→测试ID/断言→覆盖/缺失/冲突→证据等级，同时为隐藏要求找公开依据。P2P很大可按风险抽查但准确写读了哪些，不用测试数量冒充语义覆盖。gold不是规格，不要求机械两反例或全仓通过。

环境只引用本题原件和条件：真实noop目标失败/安装问题、gold投影与逐测试状态、实际命令、原始初态差异、缺席/skip/RC。git show不是未提交git diff。已有修复适用于相应grader，不等于当前actor；镜像tag/digest/实际image ID分别写，缺者unknown/null。只读归档指定成员/选定任务行，不运行归档或扫别题结果。实际actor工作树未捕获时保持unknown。按照本批actor_environment_card和共用开发验证方法给开发需求表。

沿record_template和原40项编号稀疏记录；状态可not_checked/pass/issue/unknown/not_applicable，证据范围明确。check3是真实输入，规格一致性归23；覆盖缺口归25，不等于26已证gold回归。未执行合法替代解不冒称普遍无误拒。每题保留唯一最值得先做的后续步骤，具体疑点才建议CPU，不能每题凑实验。此任务不执行或另派任务二。

允许写上述四文件；全程静态，只读文件/Git、stdlib文本/JSON/hash/AST/tar元数据，禁项目执行/导入/测试、安装下载/网络、容器/SSH/GPU/模型、修改原题/评分/生产、commit/push、子agent。初判阶段完成全包后只报各SHA并结束等待release，后阶段交付三文件SHA后结束。
