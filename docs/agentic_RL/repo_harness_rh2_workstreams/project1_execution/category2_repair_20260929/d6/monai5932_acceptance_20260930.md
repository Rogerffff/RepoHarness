# MONAI5932：漏修拒绝已接入正式评分

2026-09-30。根线程独立验收。**本题已确认的引用顺序漏判已修复；可以作为完成题级修复的版本交给第1类线程。公共评分可信性门仍有效，本页不是GPU派发或训练准入批准。**

原问题是 `ConfigParser` 解析相同前缀的引用。此前只把匹配次序反转的错误候选可以通过原15项验收，却破坏“长引用先出现”的公开行为。现在保留原题面、命令、1项F2P和14项P2P，只增加一个检查实际计算值为4的P2P；它不约束gold采用哪种实现。

## 新版本的实际验证

| 实验 | 实际结果 | 说明 |
| --- | --- | --- |
| 原始代码 | 1失败、15通过，reward 0 | 原F2P在短引用替换处产生原问题的SyntaxError；新增回归通过。 |
| gold | 16通过，reward 1 | 原要求与新增回归同时满足。 |
| 仅反转匹配顺序的错误候选 | 1失败、15通过，reward 0 | 原15项仍通过；新增长引用测试在真实解析路径报SyntaxError，拒绝原因正确。 |
| 真实CC公开开发检查 | 3次Bash调用完成；2项已有公开测试通过 | UID54321，项目解释器正确，从`/testbed`导入；真实首个请求逐字包含本次公开题面。使用确定性桩，不是模型自主求解。 |
| 同次actor原始工件直评 | 原F2P失败、其它15项通过，reward 0 | 原baseline、frozen artifact和projection的SHA保持不变；fresh grader的完整baseline及排除区摘要比较通过。 |

四次评分的全部16项参考均实际执行，无缺席、跳过或未知项。安装子命令全成功；测试真实退出码为1／0／1／1，完整结束标记和日志摘要相符。评分以UID54322执行，候选源码与冻结版本一致；有效测试文件为root属主、候选不可写。候选容器、评分容器、actor网络、relay与桩均已收口，无本批残留。

新CPU机器使用固定原镜像，配置ID `sha256:833da815aeee5132d737c83e3af72b822b5a2e0498368287014919cef084dd49`。2CPU／4GiB／PID512／shm64MiB；准备900秒、测试1800秒、整段评分1800秒。正式测试约16秒，准备约79–82秒。评分全生命周期内存峰值到4GiB，采样中有内存回收、未观察到OOM或PID拒绝；不能把准备期峰值当成测试内存需求，原`resource_facts=null`仍保留未知。

## 实现与接入

扩展受信的`replace_test_patch_append_p2p`，限定本题、文件及新增节点。来源补丁、有效补丁、base文件、公开身份、原参考与父材料摘要均校验；actor/replay共用builder。原两道mypy和其余215行材料不变，未改奖励、公共parser、权限、网络或完整baseline要求。

隔离实现经根复核及上述CPU验收后，用修改前后SHA守卫接回共享树：4个生产文件及对应新登记、材料、测试共15文件。共享树146项定向测试通过，Ruff通过。未覆盖其它线程变化，未提交推送。

- 修订ID：`monai5932-long-first-v1`。
- producer：`s2/ingest_mypy_monai_v1/ingest_manifest_swe_revision_v1.json`，SHA `657efcd6f818608c01b7665fd80bc2b72bb1ce91c11ad952456273a2bf2c55c6`。
- 材料身份：`sha256:f23097a14483357eaec420e25ce1a53ce415fc2a10924112e4b6f6db95b127c9`。
- 运行代码：`runs/category2_repair_20260929/frozen_d6_monai_v1/code_v1/`，670文件，清单SHA `cec560539ecff8778fc06f820a7f804f6e6733287c02b7d8340513321e5b5c82`。

## 证据与适用边界

新运行原件在 `runs/category2_repair_20260929/resume_remote_20260930/remote/monai5932/`，共538文件、4,032,944字节，已与远端逐件SHA/长度核对。镜像层不计入这些证据文件。

- 根实施复核：[monai5932_implementation_0930.md](../reviews/monai5932_implementation_0930.md)。
- 根三方、actor、原工件直评复核：`runs/category2_repair_20260929/analysis/monai5932_{replay,actor,actor_to_grader}_root_review_0930.json`。
- 原件对账：`analysis/monai5932_evidence_copy_0930.json`；共享接入检查：`analysis/monai_shared_integration_0930/`。
- 工具作者自审：`analysis/monai5932_replay_author_review_0930.md`，明确不作为独立reviewer结论；根线程未编写实现或验收工具，另核原始日志和实际请求。

新actor入口中的一个额外`solve`审计override未执行，故没有对应审计字段；根已从真实首请求核对公开prompt字节，不能用作者本地spy冒充这个运行事实。该缺字段无需重跑公开命令。训练capture drain、真实模型行为、反作弊公共链路、随机稳定性多次复验不在本片证明范围；已有镜像dirty文件也如实保留。
