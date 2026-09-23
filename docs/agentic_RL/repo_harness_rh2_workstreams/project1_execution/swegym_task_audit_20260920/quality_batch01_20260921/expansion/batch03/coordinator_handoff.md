# 第三批交接：11题，派发状态见dispatch.json

**收到根任务明确派发后才开始，实际状态看dispatch.json。** 第二批根验收见 `../../acceptance/batch02_final_review.md`。执行与本批材料路径的权威根为 `${REPO_ROOT}`，不是自动创建的干净 worktree。

## 目标与固定范围

项目一要验证真实 coding agent 的可靠后训练闭环。本夜只做 SWE-Gym 静态质量审查：解释公开需求、测试实际约束、gold/合理替代的关系，结合已有环境原件，给出少量可执行的下一步。不是模型解题、正式入池、改写题面或接受旧审查结论。

沿用首批根目录（本目录上两级）的 `roles/`、`record_template.md`、`actor_environment_card.md`，以及其父目录 `quality_review_protocol_20260920.md`。本批如下，不按导出结果或疑点换题：

| 工作包 | 题号 |
| --- | --- |
| DVC | 6954、3665、4785 |
| mypy | 15139、15184、10174 |
| Moto | 6185、6408、5960 |
| Pandas | 50319、51605 |

同一冻结原池排除前两批后，Pandas只剩2题，故总数11；不补虚构第12题。名单、base、源行、镜像引用见本目录 `batch_manifest.json`，SHA256=`424ad043fda8c3171109faa0d6acf9354da8011e6f5c625f24308fdcf19ea3b3`。材料根为 `runs/swegym_quality_batch03_20260921_v1/`。根检查见 `../../acceptance/batch03_material_precheck.json`；不用重做16,541个blob核验。

## 材料与角色顺序

1. 协调者核对本批入口、现有运行条件及当前进度后登记 `assignments.json`；未开始不得写成已完成。共用最多4个活动角色（含协调者），空槽可交错准备不同仓库。
2. 每题一个 **fresh公开读者**，只给公开角色卡和该题 `public/` 包。不得继承协调上下文、其他题结论、私有/历史材料或本交接文件中的私有说明。完成后保存公开稿与登记摘要。
3. 每仓库一个fresh私有主审可处理2–3题。每题先用原件及自身公开稿形成 `analysis_before_history.md`，封存后只开放该题history，再写差异、短卡和结构化记录。
4. 每仓库一个与主审分开的fresh reviewer；**整包所有独立初稿均保存并封存后**才开放任何主审/历史结论。不得把后读到的发现回写成独立初判。允许清楚记录观点修正。
5. 协调者核对完整角色链、决定性证据及未决，更新短卡/JSON/汇总，不修改封存原稿。首个小包和整批完成时向根任务回报，由根抽验。

逐题仍为7份：`public_read.md`、`analysis_before_history.md`、`old_findings_delta.md`、`card.md`、`screening_record.json`、`reviewer_initial.md`、`review.md`。输出仅本目录 `results/<instance_id>/`；聚合为本目录 assignments、batch_report、probe_candidates、cpu_queue、method_adjustments。不要覆盖前两批。

## 原条件说明，仅供协调者和私有角色

参照本目录 `environment_replay_inventory.json`、`environment_replay_notes.md` 定位逐题真实输入与审计输出，根已核对清单210份现存文件摘要及四类入口。DVC的安装wrapper、install_wave1的镜像增层、50319的reference绑定、51605的原基线不是同一路由。同名输入/输出JSON也不能互换；未经实际actor验证，grader安装成功不能填写actor ready。

Moto三题各有一个未导出的Terraform gitlink，固定commit见各题base_identity。先核与本题开发/测试的相关性；导出缺口不能直接判原镜像不存在资产或题目无效。公开包已中性披露材料缺口，不补隐藏结论。

历史聚合必须按已授权的精确题ID取对象或精确原件，勿用head/tail猜结构。若意外看见其他题线索，立即记录具体范围并报告，按实际影响调整后续角色；不掩盖，也不自动重审全包。运行摘要、当前源码、历史执行代码不是同一证据层。

## 结论和本夜边界

- 检查协议八个方面；完整阅读新增/修改的决定性断言、全部F2P及相关P2P，沿必要fixture/helper/调用者追查。测试ID数量不代替语义强弱，也不机械穷举全仓。
- 区分实际执行、解析身份、冻结计分、skip/缺席及普通失败/全局执行故障。源码假设、历史已执行对照、本轮运行和真实actor各自标明；本轮运行栏仍为空。
- 只优先最有区分力的少量下一步，不强制每题构造两类反例。固定grader语义诊断可与正式actor开发核验分开；二者不能互相代替。题面规范歧义也不能由分数或多数表决消除。
- 状态维持 `needs_review / static_review`，可列受限开发诊断候选；不扩生产枚举、不准入正式训练、不估算未观测成本。审查材料已暴露gold，不能给后续blind solver。
- 不执行项目/测试/容器/SSH/模型，不安装下载，不修改生产、原题、测试、gold、参考或reward，不提交推送。只读Git/JSON/文件和自身元数据检查可用。
- 根已使用本夜唯一获授权的重置卡；协调者不得兑换。07:30后优先收口，08:00停止新题派发，在手任务诚实保存完整/未完成边界。无需为消耗额度做重复工作。

协调任务继续使用已选GPT-6 Astra/max；根任务ID `01a08bd3-b639-7c71-a1ee-f3f4d05b3a0e`。有重要新发现、方法偏差、整包完成或需要根处理的阻塞时回报；不向其他人发送消息。
