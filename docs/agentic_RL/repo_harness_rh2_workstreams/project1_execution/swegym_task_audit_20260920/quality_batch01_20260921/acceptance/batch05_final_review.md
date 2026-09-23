# 第五批两题根验收

2026-09-21。**接受两题静态交付，今晚全部五批收口。** B5没有新增优先模型候选，两题分别保留一项CPU诊断；没有运行新测试或模型，也没有修订原题、测试或reward。

- **mypy11707**：根直接核公开四文件、文档、导入/可见性路径与gold/test，支持题面期待与既有规则的冲突。隐藏参考均为stub，不能推出“满足普通.py题面必得0”。先做原四文件base/gold×Y/X，实验确认行为，公开语义取舍另行明确。去掉整个真子模块豁免的候选只是后续可选评分校准。
- **Moto5406**：root核backend传region、ARN常量及官方断言，支持常量换East2的具体漏测候选，但尚无其实际得分。原26P2P中22改名/4未改名，测试体仍有回归价值。先比较base/gold/单常量候选的原27项和既有公开East1节点；保留原reward，公共诊断另记。

根读完两份最终review，检查结构化记录已收窄真实消息、资产、替代解及gold回归的证据范围；封存初稿保留，后稿纠正单位与引用。两题仍为needs_review/static_review/development_diagnostic，不能以三方一致替代运行或actor验证。

[最终元数据检查](batch05_final_metadata_check.json)通过：14结果、18最终输出摘要、6封存稿、4次先封存后放行、2最终review、4历史日志身份；不是OS访问隔离证明。[历史日志抽查](batch05_historical_log_spotcheck.json)确认mypy选2项，gold2pass/noop1fail1pass；Moto原27项，gold全pass/noop仅目标失败；两侧有安装及测试RC，未把旧运行写成新实测。

[CPU交接补审](batch05_cpu_handoff_review.md)经根对最终队列与review补核，无需退回。保留mypy的install_wave1派生/共同依赖pin与Moto原baseline/actual image ID未知；旧git show不当作初态diff。镜像/载荷、归档runtime与路径重定位仍待准备。当前无新增统一前置闸门、排除规则或生产修改。

五批合计40题、21个受限静态候选、19个先诊断或暂缓项，42条选择性CPU方案均未执行。简短后续入口见[夜间总结](../night_summary_20260921.md)。
