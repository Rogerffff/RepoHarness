# B5 方法记录（静态复核完成）

本夜最后固定两题 mypy11707、Moto5406。各题使用新的公开读者、主审和独立复审上下文；初稿保存并核 SHA256 后，才分别解封自身历史与交叉材料。协调者先记原件独立核读笔记，再看角色输出；前批暴露仍保留，不冒称盲解。环境原件自带 gold/noop 结果，因此 fresh 私有角色也不是 result blind。公开角色只读公开包与公开卡。

复用根对6源行、2prompt、4日志引用和3426 base blob导出的验核，不重扫全树。协调者对36环境文件重新核SHA256/bytes，无差异。只记录实际成功返回的角色和实际送达的材料解封；时间戳区分文件保存、协调者核验、解封和角色完成。初稿不可回写；后续事实修正写入delta/review以及协调者可收口的card/record。

**日志中的命令边界影响源码初态判断。** git show 后的diff描述base提交，与后面的 git diff <base> 不同。Mypy 的 typeshed 多文件diff属于base提交；真正共享未提交差异是 test-requirements.txt 加 types-typing-extensions==3.7.3，未来两侧应保持一致。Moto 的 ThreadedMotoServer diff也属于base提交，noop git status干净且显式diff为空。不能只搜索 diff --git 就累计所谓环境预改。日志行号使用物理换行，避免回车进度输出改变编号。

**两题环境分别处理。** Mypy 使用本题 install_wave1 派生镜像、离线构建pins与冻结baseline CLI；Moto使用原baseline worker→ReplayGrader，无derived-image或recipe/materials/bindings覆写。Moto实际image ID未记录，保留null；tag和manifest digest不能代填该字段。原worker job文件有其他题，只按精确ID选择，后续不能整份盲跑。当前目标镜像、代码依赖与重定位summary尚未准备。image/build审计不等于wheel/context载荷，旧/work路径不是当前可达证明。

**阅读区分要求与推断。** 题面明示预期、仓库旧契约、gold行为和隐藏测试分别列出，不为迎合gold改写公开要求。示例名称笔误可从输入/接口消歧，不自动判坏题；真正相反的预期方向必须保留。仅从ARN错误不能推出表真实存储区域错误。相邻流记录字段、分区和完整TableClass支持不因同文件就自动成为本题新要求。

**check编号与证据范围独立核对。** 原check3是求解者实际收到的输入，公开题面矛盾归check23；静态prompt读取不替代真实消息核验。需求上不需要外部数据不等于实际actor资产齐全，未构造并执行合法替代解也不等于普遍无误拒。具体未测旧行为归check25的覆盖疑点；没有base/gold回归对照时，check26不写成已证gold回归。历史grader范围的pass必须注明对应条件，缺证据保持unknown。

八方面用于阅读导航；记录仍沿原40项check编号及状态，不强制满填。静态结论保留needs_review/static_review、development_diagnostic。合理替代解、错误候选与gold都需区分静态推断、历史RH2、未来未执行实验；没有观测不填写模型成本或执行结果。真实actor消息、身份、依赖、源码导入、权限和可见资产另验；grader安装/得分不构成正式actor准入。

07:30后以收口在手链为先，08:00不派新题；完整链未完成就报告缺失，不缩短独立复审。只写本批五汇总和逐题七文件，不改前批、准备材料、原题/测试/gold/评分，不运行项目/测试/安装/网络/容器/SSH/GPU/模型，不调用quota/reset，不提交推送，不启动B6。

**独立复核后的收口。** 两题共6个fresh角色，6份不可回写初稿，2份最终review；2次主审历史解封和2次reviewer交叉解封均在摘要核验后实际送达。没有核心结论未解决分歧。Mypy reviewer原先把语义/粗改回归合成一个实验，复核后接受先做四文件base/gold×Y/X，粗改另列；Moto双方支持一个East2常量负对照加原有East1断言。两项均未执行，普通模型探针暂不优先，未永久拒绝题目。

原check编号收口：两题3/7/24改unknown，Mypy2改unknown，Moto26改unknown；已证历史/静态子结论继续明确保留。Mypy4补合法源码投影和官方恢复证据，27的“依赖齐”收窄为gold未增加交付依赖且历史grader安装完成；Moto表名问题归23、区域覆盖风险归25，38不因阅读复核完成就成为运行复验pass。没有为了状态整齐把所有历史执行pass一律抹去。

**旧论证须按原件纠正。** Mypy公开文档已有改名不导出的明确例子；隐藏参考全是stub，不能推出满足普通.py字面预期的解必得0。Moto的26P2P中22改名、4原名，保留的测试体仍有回归价值；不足在地区ARN未检查，名称变化本身不是回归无效的理由。两项反例候选都继续标静态预测，不把旧记录的肯定语气迁移成实际运行。

封存稿的细节更正保存在review与可更新card/record：资源峰值只保留原mem_peak_mb字段，未核单位实现不换算MB/MiB；Moto公开稿流测试路径应为tests/test_dynamodbstreams/test_dynamodbstreams.py；Table的region仍用于默认加密键，只是此前未保存给ARN生成，不能说完全丢弃。封存哈希保持不变。

最终交接只含2个具体CPU主实验和1个明确延后的Mypy回归候选。原冻结分数与公开诊断分别保存，保留原版本；没有写执行补丁、修改参考或给出新实验结果。新执行仍受本任务静态范围之外的调度/授权约束，不从本计划自动启动容器或模型。
