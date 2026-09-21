# B4 方法记录

本批限 DVC4185、Mypy16869、Moto6114，只做静态质量审查及未来 CPU 方案。沿用主协议与原 40 项 checks 的语义；没有改 B1–B3、题目/源码/测试/gold/参考集合、准备 manifest 或评分机制。

1. **把独立阅读和盲测分开。** 每题使用新的公开读者、私有主审、独立复审上下文。公开稿、主审读历史前稿、复审读主审前稿分别保存并核 SHA256；主审历史与复审交叉材料只在对应封存后显式提供。环境原件已有 gold/noop 结果，私有角色的独立性是相对既有质量结论，不是 result blind。协调者原件初读笔记也先记录，再读角色输出；协调者仍有前批暴露。
2. **登记实际交付，不把授权当成解封成功。** 工具容量拒绝的 spawn/followup 只记失败事件，不虚构角色。Mypy 首次历史 followup 失败，最初时间仅记 authorization；成功 followup 的实际交付才记 history_released。文件 mtime、协调者观察时间、材料 release 时间分别保存。已封存文稿不改；主审 card/record 的完成散列是当时快照，协调者收口后的散列另存。
3. **复用材料验收，补做质量所需核读。** 复用上级对 3,842 个 base blob、9 源行、3 prompt、6 运行引用及 71 环境文件的预检，没有重扫全部 base。协调者对 71 环境文件重新核 SHA256/bytes，无差异；逐题继续读取需求、断言、调用者、原日志和实际入口。清单可读、原日志存在、目标机镜像可用、真实 solver 能开发，是四种不同证据。
4. **保留公开题面的多个目标。** DVC 的 false 状态与未变参数 commit 提示属于两项明确需求。gold/评分只解决前一条的强静态证据，不能由标题或已有满分消除。首选 base/gold 双症状诊断，暂缓普通能力 probe；首轮仅保留一个 start 改值正向控制。另保留恒空 status 的漏测假说；不为“一个优先实验”删除独立问题，也不强制再造第二份补丁。
5. **区分等价解误拒与错误解误收。** Mypy 的 Unpack 输出候选必须先证明导入、类型语义和必要回归成立，再讨论精确文本造成的失分；单纯解析通过不足以证明等价。Moto 用实际创建的第二个集群 ARN 查询并核身份，判断“首个集群”错误候选是否仍获原评分。两个方向均未执行，不能把预测写成已观测 reward。Moto 复审选择暂缓按原 reward 统计普通模型正确率，协调者接受并保留 CPU 校准；Mypy 的受限候选仍要求输出语义审查。
6. **不扩张没有证据的规范。** Mypy 原例私有 _Ts 的默认过滤有公开文档依据，输出完整性待验，不能自动判 gold 引入回归。Moto 示例 1/0 笔误可由上下文与创建响应消歧；delete/start 等其他接口、跨账号/区域/服务 ARN 的精确规则不是已确立的本题要求。没有外部规范核证时保留边界歧义，不发明 AWS 契约。
7. **封存后的事实更正写入后稿。** Mypy reviewer 初稿把文件 CLI 说成运行时导入，最终 review 根据 collect_build_targets 的文件分支更正；模块/包路径与文件路径不能混用。DVC 主审和 reviewer 初稿把 mem_peak_mb 换称 MiB，后稿保留字段及 386.82/482.152 原值，不推断单位。日志含回车进度行，引用采用物理换行行号；Python splitlines 会把回车计为另一行，不能直接拿其索引作为原文件行号。
8. **精确区分缺键与假值。** DVC 当前文件缺跟踪键应为 deleted；当前有键而 lock 没记录才是 new。空 YAML 文本是 null，不是带引号的空字符串；七个 F2P 只代表四类假值。无条件 get 的反例需说明非空 lock 缺该键、当前值为 null 的具体前提，不能泛称所有 new 都被隐藏。
9. **未来重放固定实际历史条件。** DVC 同时需要 recipe 与 tasks[instance_id] 的 bindings、NetworkX 兼容 wheel，并保留日志中两侧 setup.py 的 Moto pin 共享预改。构建审计不是 wheel 输入；launcher 默认旧目录不等于本题 v1c。Mypy/Moto 使用各自 install_wave1 镜像和冻结 baseline 入口，无本题 recipe/materials/bindings override。原 /work 路径需另建重定位副本，不能回写历史 summary。
10. **保留证据和用途边界。** 历史真实 RH2、静态推断、未来未执行 CPU、真实模型结果分开记录；raw RC、实际节点、解析键、冻结引用也分别记录。DVC 的 51 个实际节点与 52 个解析键来自绑定别名，额外执行通过不自动增加 P2P。apply_user=agent/54321 与 grader=rh2grader/54322 都不能证明正式 actor 的消息、依赖、权限与可见资产。checks 3/24/29 不因未见问题填 pass；成本无观测则 null。

协调者读取共享 bindings 时见到其他题 alias/source-log 元数据的暴露已登记，没有据此向 fresh 角色提供其他题质量结论。主审、复审和协调者已见私有测试/gold/历史结果，产物只供 development_diagnostic，不得放入未来 solver 上下文；静态完成不等于训练、最终评测或 ready_for_probe 批准。

DVC 复审另限定替代解中的 KeyError 风险：只有基类 status 返回空映射等条件下才会触发参数层直接索引风险；普通无 md5 参数通常仍返回 new，不能把它写成任何 changed_checksum 覆盖都必然报错。Moto 的“非标准 ARN”在最终 card/record 改为“本题未约定的 ARN 输入边界”，避免把语法有效但查询语义未定的 ARN 错称非法。上述修正均保留封存稿原貌。
