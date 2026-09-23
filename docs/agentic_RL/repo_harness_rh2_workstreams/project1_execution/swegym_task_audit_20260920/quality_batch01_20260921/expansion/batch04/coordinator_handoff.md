# 第四批后备交接：三题，尚未派发

**只有收到根任务明确派发后才开始。** 本文件不授权角色启动。根会结合第三批验收、时间和新鲜额度决定是否启用；07:30优先收口，08:00不派新题。权威工作区为 `${REPO_ROOT}`，不用干净worktree替代共享未提交材料。

固定题单：DVC4185、mypy16869、Moto6114，各仓库一题。出处与固定seed抽样、前三批排除、环境入口见本目录README及manifest；manifest SHA256=`6c27c2a0fd6a83be5c11076985e84421c8887f5ff801783db1564e8f20392c9b`。材料根`runs/swegym_quality_batch04_20260921_v1/`。根已核9源行/3prompt/6日志引用/71环境文件，见`../../acceptance/batch04_material_precheck.json`，不重复3,842个base blob检查。

项目目标仍为真实coding agent后训练的可靠环境与评分；本批只静态审查质量及准备最有区分力的少量下一步。沿首批根目录`roles/`、`record_template.md`、`actor_environment_card.md`和父目录质量协议。各题fresh公开读者仅收本题公开包；fresh主审先原件初稿封存、再开放自身历史；另一个fresh reviewer先独立初稿封存、再开放主审/历史。不可复用前批私有上下文作角色，无需强制双反例或40项满填。最多4个活动角色含协调者。

每题仍交7件，限本目录`results/<instance_id>/`；协调者写assignments、batch_report、probe_candidates、cpu_queue、method_adjustments。准备manifest不回写为执行状态，实际以新dispatch/assignments为准。逐题完整改动断言、F2P及必要P2P/helper要读；历史聚合只按精确题ID取，不head猜结构。任何意外跨题信息暴露按实际范围登记，不掩盖或自动重审全包。

私有环境说明：DVC4185必须同时保留`--recipe`、顶层tasks映射的`--bindings`及`networkx==2.3+rh2.1`真实安装条件；构建审计不等于wheel本体。mypy16869/Moto6114为install_wave1镜像增层、原CLI/spec；各题镜像、Python和pins不同。Moto的Terraform gitlink未物化，应先判相关性，不推断原镜像缺失。未来镜像、旧/work路径重定位与运行环境均未核，grader通过不等于actor可开发。

状态保持`needs_review/static_review`，用途`development_diagnostic`；静态候选不是正式准入。固定grader诊断与actor开发验证分开，规范歧义不能用分数或多数票消除。公开读者不要接收本交接、私有环境输入、gold/隐藏测试和旧结论。已暴露审查者不能做盲解solver。

只许静态文件/Git/JSON读取和自身元数据检查。不执行项目、测试、容器、SSH、GPU/付费模型，不安装下载，不改生产/原题/测试/评分，不提交推送。根已用完本夜唯一重置授权，协调者不得兑换任何卡。重要发现/整包完成向根`01a08bd3-b639-7c71-a1ee-f3f4d05b3a0e`回报，不通知其他人。继续既定GPT-6 Astra/max。
