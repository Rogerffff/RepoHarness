# B4 固定三题静态质量审查

三条公开阅读→私有主审→独立复审链已收口。结论为 **1 个受限静态候选、2 个先诊断后再排普通 probe 的对象**；三题均保持 `needs_review / static_review / development_diagnostic`，没有正式 actor 验收、训练或最终评测批准。现有 gold/noop 运行来自 09-19 原件，本批没有执行项目、测试、CPU 反例或真实模型。

| 题目 | 最重要的质量结论 | 最终用途与唯一优先下一步 |
| --- | --- | --- |
| [DVC4185](results/iterative__dvc-4185/card.md) | gold 修复假值加载，但题面另列的未变参数 commit 提示仍有强静态未修证据；七 F2P 不覆盖该流程或真变化对照。 | 暂缓普通能力 probe。固定历史共同预改和环境，做 base/gold 两阶段重载后的 false status、truthy 参数非 force commit 对照，仅附 start 改值控制。 |
| [Mypy16869](results/python__mypy-16869/card.md) | StarExpr 崩溃与局部修复有源码和真实历史日志支持；语义正确且导入完整的 Unpack 输出可能被精确 `*Ts` 文本断言误拒，尚未实证。 | 受限开发诊断候选，须保留语义审查及 actor 门。做 base/gold/先验证语义的 Unpack 候选对照，将原 _Ts 文件 CLI 与默认私有过滤检查合在同一实验中。 |
| [Moto6114](results/getmoto__moto-6114/card.md) | 唯一新增 ARN 断言只验返回一项，没有核目标身份；仅在 ARN 分支返回首个集群的错误实现静态可能过全部参考。 | 暂缓按原 reward 统计普通模型正确率。用 gold 与错对象候选比较原 35 项评分和独立目标身份断言。 |

**DVC 的决定性证据。** `commit → Stage.changed_entries → changed_checksum` 继承普通文件哈希比较；参数 info 保存选定值而没有 md5，普通 status 却走参数值比较。gold 只改 fill_values 的真值判断，所以“status 干净、commit 仍提示”仍有完整静态解释。公开读者、主审和复审在交叉前各自识别了双目标；一致意见不是运行证明。若后续 gold 的 commit 行为意外正确，应根据真实初态和调用链修正静态结论。旧“当前缺键应 new”的建议已纠正为 deleted；只有当前有键而 lock 无记录才是 new。七个假值文本只有四类语义，空 YAML 文本并非引号空字符串。

**Mypy 的限制。** 两个 F2P 分别保护普通和语义分析后的 AST 路径，另有四个旧行为参考。Unpack 反例必须先验证导入、类型语义与必要回归，不能拿候选自身错误证明误拒。原例 _Ts 默认被当私有声明过滤，有公开文档依据；不能自动称为 gold 新引入错误或原崩溃未修。复审初稿把文件 CLI 说成运行时导入，最终 review 已按文件分支更正，封存初稿未改。受限候选不表示原 reward 可充当所有合法解的正确性标签。

**Moto 的限制。** 核心要求是返回 ARN 所指集群，数量相同不足以证明身份正确。具体错对象候选尚未制作或运行，不能写成已观测 reward=1。gold 对正常输入域未发现确定错误；跨账号、区域、服务的 ARN 可能语法有效，只是本题没有规定相应查询语义。示例 cluster-1/cluster-0 是非阻断笔误，可用创建响应的实际 ARN 消歧；不应扩张到 delete/start/modify 等接口。独立复审据身份漏测建议先校准，协调者接受这一比普通候选更保守的用途。

**历史执行证据与实际条件。** F2P 指期望由失败转为通过的参考，P2P 指应保持通过的参考；下表均为已核原日志/账本，不是 B4 新运行。

| 题目 | gold / noop 冻结参考 | 原始测试结果 | 条件与限度 |
| --- | --- | --- | --- |
| DVC4185 | G 7/7 F2P、22/22 P2P、R=1；N 0/7、22/22、R=0 | G 49P/2S、RC0；N 42P/7F/2S、RC1 | dvc_install_v1c、Python3.9.20、NetworkX 2.3+rh2.1、recipe + reference-bindings-v1、两侧 setup.py Moto pin 预改。51 实际节点、52 解析键，不能把额外执行项算新增 P2P。 |
| Mypy16869 | G 2/2 F2P、4/4 P2P、R=1；N 0/2、4/4、R=0 | G 6P、RC0；N 4P/2F、RC1 | install_wave1、Python3.12.4、原并行选择命令；目标参考无 skip/missing。旧 -n0/跳过诊断不能替代这次条件。 |
| Moto6114 | G 1/1 F2P、34/34 P2P、R=1；N 0/1、34/34、R=0 | G 35P、RC0；N 34P/1F、RC1 | install_wave1、Python3.12.4、单文件 -n0；旧安装失败不再代表当前已引证评分配方。 |

三题历史 grader 为 rh2grader/54322，candidate apply 为 agent/54321；均不等于正式 actor shell 验收。各镜像、pins、冻结入口、原始输入、脚本和日志路径已分别进入 [CPU 队列](cpu_queue.json)。目标机镜像可用性仍未知，本地三组构建 context/wheel payload 缺失，原 summary 仍引用历史 /work 路径，需要另备重定位副本。DVC 构建审计不能代替 NetworkX wheel，也不能漏传 bindings。资源峰值只保留原字段 mem_peak_mb，不将未经核证的值改写为 MiB。

**过程、产物与验证范围。** 实际登记 9 个 fresh 角色（每题 public reader/main/reviewer 各一），每题 7 文件，共 21 文件；9 份初稿封存、3 份交叉 review、6 次成功材料解封。失败派发另记事件，首次未送达的 Mypy 历史授权不计成功门。协调者仅在复审完成后收口 card/record；初稿散列保持原样，角色完成时的 card/record 散列与最终散列分别保存。稀疏 checks 沿用原 40 项编号；3/24/29 保持 unknown，无观测成本为 null，不新增排除规则或材料修订。

最终文件、角色、封存、门禁、字段、队列和路径的元数据核验及 25 个非自引用输出散列见 [assignments](assignments.json)。准备验收复用上级的 3,842 base blob 检查，未重扫全部源码；协调者另对 71 个环境原件核 SHA256/bytes，无差异。该验证不包含项目测试执行。方法修正与阅读暴露详见 [method_adjustments](method_adjustments.md)；候选限制详见 [probe_candidates](probe_candidates.json)。

本批只写授权的五份汇总和逐题七文件，未改 B1–B3、准备 manifest、原题、源码、测试、gold、参考或评分；未运行项目/安装/容器/SSH/网络/GPU/模型，未查询额度或兑换重置，未提交推送，也未启动 B5。审查者已暴露私有材料，这些文档及反例设计不得提供给未来独立 solver。
