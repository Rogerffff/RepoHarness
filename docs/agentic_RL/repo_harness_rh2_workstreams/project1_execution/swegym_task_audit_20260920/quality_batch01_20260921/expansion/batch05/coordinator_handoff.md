# 第五批交接：本夜最后两题

根已接受前四批38题静态交付，本批是本夜最后一次题目派发。执行仍须以根发给协调者的明确消息与dispatch为准；本交接不等于已经启动。07:30后优先收口，08:00不派新题；在手题如不能完整结束，保存已完成与缺失边界，不压缩独立审查来凑完成。权威工作区为 `.`，复用共享未提交材料。

固定两题：`python__mypy-11707`、`getmoto__moto-5406`。从原not_reviewed池排除前38题，各仓库按固定seed取一题；manifest SHA256=`ea9421d30ba7bbf9078dc42967f8f5eaa7cc0554a7db19b6aa85bb48d1be9174`。材料根`runs/swegym_quality_batch05_20260921_v1/`。根已核6源行/2prompt/4日志引用/36环境文件及固定选题，见`../../acceptance/batch05_material_precheck.json`；复用准备者3426个base blob验核，不重复全树读取。

目标：独立判断公开要求、合理开发手段、gold与隐藏验收的一致性/覆盖，以及最有区分力的下一步。沿首批根目录roles、record_template.md、actor_environment_card.md及质量协议；每题fresh公开读者只收本题公开包，fresh主审先原件初稿封存再读自身历史，fresh reviewer先独立初稿封存再读任何主审/公开读者/质量历史。不可用前批私有上下文复用角色，不机械双反例或满填清单。最多4个活动角色含协调者。元数据顺序不证明OS隔离。

每题七件交到本目录results/<instance_id>/。协调者写assignments、batch_report、probe_candidates、cpu_queue、method_adjustments；准备manifest不回写运行状态。原题/gold/test、全部变更断言、F2P及相关P2P/helper直接核查。历史按精确题ID选择，意外暴露按实际范围披露。公开读者不能收本交接、私有环境输入、gold/隐藏测试/旧质量结论。

两题环境不同：mypy11707为install_wave1派生镜像及原spec/CLI；Moto5406为原baseline，实际image_id缺失保留未知，不能套用install_wave1。两题都没有recipe/materials/bindings覆盖。归档源码和每题pins/解释器/安装/日志入口见environment_replay_inventory.json、environment_replay_notes.md。Moto Terraform gitlink仅固定commit未物化，先判本题相关性，不能当原镜像缺文件。镜像/依赖载荷、旧/work重定位、真实actor环境都尚未重新准备，不是本次静态阻塞；grader通过不等于actor开发条件已证。

逐题保持needs_review/static_review，用途development_diagnostic；候选并非训练或模型准入。CPU方案只写有明确区分目标的最小实验，不强制所有诊断都先于模型。已有源码推断、历史运行与未来实验分开；不要把论文/旧模型结论当既定标准，也不为配合gold删改公开要求。

本夜只许静态文件/Git/JSON/归档成员读取与自己元数据检查，不执行项目/测试/容器/SSH/GPU/付费模型，不安装下载，不改生产/原题/测试/评分，不提交推送。根已用完唯一重置授权，不能兑换余卡。继续GPT-6 Astra/max。重要发现、整题/整批完成回报根任务01a08bd3-b639-7c71-a1ee-f3f4d05b3a0e；本批后不再扩题，进入汇总交接。
