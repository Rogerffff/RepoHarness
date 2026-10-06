# 同原FP CPU镜像API表示绑定追加独立审查（2026-10-03）

结论：这次窄修保持原严格source identity（来源镜像身份）。两题原Image ID、Architecture、Os、完整RootFS及全部旧GPU Config字段均相同；CPU多出的13个Config键被完整冻结并严格比较，没有删除字段、填默认值或仅接受部分Config。可以交owner用新job/新目录继续既有窄恢复；**本报告没有执行SSH、Docker、worker或评分，修正后的实机通过与105/137参考结果仍待读回。** 原infra/reward=None、单模型样本、另一模型缺项和不授训练资格均保留。

## 已发生的前置失败

[7305前置失败读回](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask_same_fp_cpu_c_v1/cpu_7305_pregrade_failed_readback_v1.json) SHA `d3d0a5b440ca3c29f12beca7fea5666510dd573be726246a01007d81eff71c26`（单行JSON，:1内含slot、队列和stderr原文）。6段内嵌文本SHA均已独立复核。真实slot记录为run / slot0 / returncode1，开始09:55:14Z、结束09:55:16Z；stderr定位旧封存worker L126的 `exact source image differs`。旧源码该检查在 `manager.grade` 和容器创建调用前；这次未进入安装/测试，不产生模型0分。

serial状态只有7305一项returncode1，9378没有启动，证明本次 `stop_on_nonzero` 实际阻止了下一题。`own_containers`返回rc0、names空、stderr空，限于所查询owner标签的容器残留为空；不借此推断宿主所有容器状态。旧静态[worker审查](non_author_cpu_same_fp_regrade_worker_review_20261003.md)、原失败和旧out继续保留。

## 表示差异的独立核对

[两题完整image inspect读回与差异](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask_same_fp_cpu_c_v1/cpu_exact_image_api_diff_v1.json) SHA `c85d39e854e12c74048139ecf9b6db39575123136e0e3f2e3c0e943d8b86967f`。该文件单行JSON，精确对象键为`7305/9378.actual`、`.expected`及`.diff.Config`（:1）；独立比较值和键集后，两题差异仅在Config。

| 题目 | 保持的实际Image ID | 原Config键 / CPU完整Config键 | 参考范围 |
| --- | --- | --- | --- |
| 7305 | `b4f186ca0a0139f4287b9203a666b9fd009af079ddad700bb2bf8019aede8b99` | 4 / 17 | 105 |
| 9378 | `1e5a0ee850161b35d33d26445f73e872488a45e0e436195af239190b68574096` | 4 / 17 | 137 |

原4键是Cmd、Env、Labels、WorkingDir，均存在且值完全相同；Id、Architecture=amd64、Os=linux、RootFS的Type和完整有序Layers列表也完全相同。CPU额外13键为AttachStderr、AttachStdin、AttachStdout、Domainname、Entrypoint、Hostname、Image、OnBuild、OpenStdin、StdinOnce、Tty、User、Volumes。`Config.Image`是非空legacy字符串，不能把它描述为全部空值；绑定仍以顶层Id为原来源身份，不拿Config.Image替代它。证据支持表示差异解释，没有证明某一具体daemon/API版本是唯一原因。

新[CPU表示冻结表](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask_same_fp_cpu_c_v1/snapshot_ceb9df15de2d8c66/source/cpu_image_inspect_expected_v1.json) SHA `f1969b3854a1e3ca0d56a1f517be14d4dbc72a1d3a52897c2c2d631218f2d3d0`。7305 CPU对象为L3–52、原GPU副本L53起；9378 CPU对象L110起。两题original_gpu_readback均与原模板inputs中的expected_actual_image完全相同；expected_cpu_image的五项Id/Architecture/Os/Config/RootFS均与独立CPU actual读回相同，source_readback_sha256绑定上述diff原件。完整source字段和精确SHA见[JSON证据索引](non_author_cpu_same_fp_image_api_binding_review_20261003.json)。

## 新worker的约束范围

最终worker SHA `3086fb2e63fdd6c984baf717c1525ce2bdf7f8693ca9954d8cc815cb817f4312`；L61–68读取固定快照内冻结表，先与**原inputs**逐项比Id/Architecture/Os/RootFS，再比每个原Config字段，保留原数据另加expected_cpu_image及表SHA。原模板/inputs没有被改写；table内的GPU副本不是替代原inputs的权威来源。

L135–138仍按原expected_actual_image_id做inspect，保存原始输出后，要求只有一个对象且其五项字段与CPU冻结表示全等。其中Config整字典17键参与等号，额外键被删、增加或改变均不能静默忽略。这里全等范围是Id、平台、RootFS及**完整CPU Config**；host-local GraphDriver等非来源字段不属于此绑定，不把它包装成整个原始inspect对象的全等。

L101–103将表SHA和明确scope写入binding；L181继续验证起后容器实际Image等于原expected_actual_image_id，防止mutable tag在inspect和容器启动之间改变实际来源。原FP、baseline、脚本、reference、resource/profile、UID、single-shell、caps、取消和清理路径保持上一封存版本。

新快照manifest SHA `ceb9df15de2d8c66b4680fef4bb24c0141dfaaec75c4ecc51ea1d971acea4516`，1100件 / 145,271,383B、1045个code8成员；全部逐SHA/大小/regular身份核对通过。与上一b22c快照比较：只新增`source/cpu_image_inspect_expected_v1.json`，只修改worker，没有删除成员；其余1098件逐字保持，包括两个原GPU模板/inputs、code8、CPU槽和串行helper。故本次不放宽脚本、105/137参考、FP或资源约束，之前setup900及7305五键环境恢复仍按原已审范围分列。

[新launcher v3](../../../../../../../../runs/category2_repair_20260929/swe_dask/environment_recovery_20261003/dask_same_fp_cpu_c_v1/launch_cpu_recovery_v3.py) SHA `c2de434864c43695ed199b8cb6e473e1c30031b1bf6ceb8cc88d5a6c7d358b81`，L12使用新owner recovery v3目录，L16使用新jobID v2，L18–24继续经统一run槽执行完整worker，L45保持stop_on_nonzero=True。这样没有热换旧run或复用旧失败out；本报告仅核源码，不冒称新launcher已实机完成。

## 剩余验收

未发现需要再放宽identity的静态阻断。最少后续工作是对该1100件快照做新namespace纯构造，读回表SHA、原FP、原baseline、完整script与module绑定；再由owner经槽补评，核新实际image读回及起后Image ID、原single-shell、完整105/137参考和真实失败归属、7305五键/原processes两组、pids.events=0、oom/oom_kill=0及manager/owner清理和结束snapshot SHA。任一前置或清理未知仍停止串行派发，保留新失败，不自动补跑。

本审查只新增本对报告，不修改旧报告、历史原件或共享实现，不将前置API兼容修正写成候选语义成功、另一个模型结果或训练资格。
