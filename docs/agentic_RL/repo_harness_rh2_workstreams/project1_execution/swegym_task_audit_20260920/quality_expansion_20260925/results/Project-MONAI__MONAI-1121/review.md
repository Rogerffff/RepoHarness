# Project-MONAI__MONAI-1121 独立交叉复核

结论：维持 needs_review/static_review，仅供 development_diagnostic。AHNet 的局部修复有静态证据及历史差分支持，但公开“为所有网络增加 TorchScript 兼容测试”与当前候选交付/评分范围的错位仍未解决。封存后新增原件进一步证明：39 pass / 1 fail 与 40 pass 是 **materials-v1 修订收集条件后的历史 grader 结果**，不能描述为对未经修订原始 test.patch 的原样 pytest 验证。

## 暴露时序及核验对象

独立初稿 SHA256 为 `bbee4010837b6e0887e33848f80161bc77d9fa034018e6164a5d2d98ef277880`，本稿不修改它。2026-09-25 root 确认本包三份 reviewer_initial.md 及主审后稿封存后明确 release，才接触其他角色结论与历史。以下 materials-v1 原件及 root 比较记录也是 **此次 release 后首次暴露的补充证据**，初稿没有读取或据此判断；不可追溯伪装成独立初判已有证据。

本稿路径缩写 ROOT=/Users/roger/Desktop/claude-code-verl-stage0h；B=ROOT/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925；RUN=ROOT/runs/swegym_quality_expansion_20260925。额外读取 ROOT/runs/env_recipe_repair_20260919/materials_v1/runs/Project-MONAI__MONAI-1121-{noop,gold}/materials/materials.json，materials_v1/prep/Project-MONAI__MONAI-1121/{prepare.py,config.json,stderr.log}，materials_v1/replay_with_install_recipe.py，以及 B/pack05_monai1121_material_override_review.json。仅依赖本题授权路径，未跟随历史文本扩读旧日志。

## 决定性原件与主审结论

1. 公开目标覆盖“所有网络”和新增测试交付；public_hints 的预定源代码限制、测试恢复机制与之冲突，但实际 actor 是否收到该限制仍未知。完整 gold 仅修 AHNet 两处类型/形状处理，不能代表实现了所有网络的测试交付。nets/__init__.py 中还导出 DenseNet、DynUNet、HighResNet、Regressor、SegResNet/SENet 等未被本次新增往返测试覆盖的网络。此处不是单凭预定 hints 判断必然误拒：即使 hints 未送达，现有评分也没有验证候选实际新增所有网络测试。
2. 新测试涉及 AHNet、Discriminator、Generator、UNet、VNet；helper 做 script、序列化、加载及 eval/no_grad 下输出比较。F2P 仅 AHNet，35 个 P2P 混有旧功能测试和 Generator/UNet/VNet 新 script 测试；Discriminator 四项虽在运行中通过，却不在 expected 集合。逐个核对 36 个 expected 状态均与原日志一致，不把执行项数量当成目标语义覆盖。单一随机输入/固定配置不证明所有网络或训练行为。
3. AHNet gold 将 forward 内固定置零的 dropout 值改为浮点，并将 PSP 的 tuple 尺寸改为 shape 切片。公开 AHNet 没有非零 dropout_prob 参数，相关 DenseBlock 调用传 0.0；原代码已经无条件置零，不能把 gold 定性为新增禁用 dropout 的回归。AHNet 默认 upsample_mode 为 transpose，因此不能从 PSP 构造器默认 trilinear 推定该 F2P 已覆盖插值分支。局部正证据保留，未测分支归覆盖限制，check 26 仍 unknown。
4. 本题 historical refs 指向 L1_monai_1/records/Project-MONAI__MONAI-1121.json，文件 SHA256 `3b6d2003342f6bc369a7320d2d2a04a6964293e71adcc708329cb367dc45c0a9`。旧记录中的下载/np.int/helper fixture 错误只是旧阶段记录；本轮新的 scoped 日志证明其对应 grader 条件已变化，不能照抄为现存失败。主审纠正旧文的默认分支和假设 dropout 需求有原件依据。

## materials-v1 补充证据的精确含义

分别对原始与修订 test.patch 用纯 stdlib 在内存中应用 unified diff，核每个上下文；用 AST 比较函数与断言，不执行生成内容。原始 test.patch SHA256=`d82fc5d7df743e2b694e098cc59bb9d03d27d1f94111c490698ed69a92b7d678`；两份 materials.json 相同，文件 SHA256=`57e4dd0d2e447726477a1bad5aacc755f76585e5be5b94ce04ee630fd3f85a0d`，其中修订 test_patch SHA256=`928e345a3f5f89887542d82f5c9e1e189873cb3d45ee5e4b52a1de614c96f241`。两种补丁生成的六个路径相同，唯一材料化源码差异是在 tests/utils.py helper 后增加说明注释及 `test_script_save.__test__ = False`；全部函数定义与 Assert AST 相同。config 中保存原始 patch、append_to 该 helper，stderr 为空。故可确认目标调用与断言未被改写，同时确认 pytest 收集契约确已修订；空 stderr 本身不是运行通过证据。

replay 包装脚本核原 test patch hash，建立替换 test_patch 的 versioned GradingEnvSpec，保留 candidate_test_script，并记录材料摘要。materials 元数据给出原 grading digest `sha256:abe5416b1174a06e1bd60a39f47f75386b1d823d5fb738396d03cd69486e6276` 与修订 digest `sha256:71ebb22db1929f173492d50d66d4f6488e453ae5336ace307a791e1a91a9f976`，scope 明写 versioned diagnostic、源 prepared package 保留、production 前 refreeze。它不是原材料等价性或生产有效性的证明。原运行日志没有打印该赋值；收集修订的识别来自已授权材料、配置、脚本与本题账本身份的关联，而非声称在 pytest 日志中见到赋值。

noop/gold 精确命令都是 `pytest -rA tests/test_ahnet.py tests/test_discriminator.py tests/test_generator.py tests/test_unet.py tests/test_vnet.py tests/utils.py`。noop 的 AHNet float 属性被赋 int 错误在原日志 1064–1074 行，1115–1159 行汇总 39 pass / 1 fail、RC 1；gold 1084–1128 行为 40 pass、RC 0。无 expected 缺项、skip 或 xfail。标记让导入的 helper 不作为独立 pytest test 收集，其余调用仍可用，因此这组差分支持 **修订收集条件下** AHNet 的局部修复，不能用来证明未经修订原补丁没有 helper fixture 收集错误。

历史环境为 verified-assets-dependencies+materials-v1，脚本 digest `56667b0a30d20c1c968ac6756e0ec5e2ab65cd085ce2022cc7a7080ddfa5032e`；实际派生镜像 ID `sha256:b3bccbbee1887d67b83232c451588cb0f7226dd41f12d4af10b520b96d3e05bd`，不得与 manifest/source 身份混为一谈。历史 grader 的 rh2grader/54322、2 CPU、4 GiB、deny_all、/testbed 源导入及预训练资产可用不证明实际 actor 开发环境已经具备同样条件。

## 分歧裁定与需要修正的汇报

主审初判对 materials-v1 机制标为未知在其封存时有据；现在需在后续授权记录中补充原件及首次暴露时间，把 historical_collection_condition_gap 的“当前机制尚未核实”收窄为“静态收集修订已核实，当前 actor/生产条件仍未验证”。同步补 recipe_ref/facts_ref/issue 与 card 的历史结果限定，不能修改封存初判制造先见性，也不能把此修订仅称依赖安装修复。

我的独立初稿 check 24 的宽泛 issue 应收窄为 unknown：已证的是目标/交付/断言契约错位（4/23），不是唯一源码实现路径或广义全局误拒已证明。check 27 原先 unknown 应与主审一致拆明：局部修复有正证据，公开全目标完整性有已证缺口，故 issue 合理。check 26 unknown 维持，不把不完整覆盖升级为 gold 回归。

唯一优先下一步：先由任务规格负责人对齐公开“所有网络新增测试”、允许的候选交付及实际评分范围，并在该具体版本中明确是否采用 materials-v1 收集修订；随后才有意义验证 actor 开发能力。单加 CPU 运行不能解决规格错位，不建议改公开问题成私有 AHNet 报错提示来伪装修复环境。

## 复核边界与结构检查

本稿为独立初判封存后、root 明确 cross_review release 后的第二阶段复核。仅阅读本题获准 public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json、本题 refs.json 指向的历史及授权原件；不以其他题结论投票。第一阶段的断言、helper、gold、调用者与原日志逐项核读见封存 reviewer_initial.md。此轮再核主审 expected 状态表与精确原日志，未执行或导入项目、测试、容器、安装、网络或模型；没有派发后续任务。共享工作区的阅读边界是流程约束，未声称操作系统隔离。

screening_record.json 的 13 个顶层字段、38 个稀疏 checks 的原编号及 status/evidence_refs/by、issues 的 category/scope/evidence_refs/proposed_action/status 均检查通过；并核对 facts_ref 的输入身份、分析稿 SHA 与 run_refs。additional_exclusions=[]、revision_refs=[]、needs_review/static_review、development_diagnostic 与成本 null 均符合本轮权限。字段齐全不代表全部语义已证实。check 3 实际 actor 输入、29 实际泄露情况及 40 全流程漏检/误拒边界仍 unknown；授权阅读 private/history 属于审查暴露，不等于 actor 曾见过这些内容。主审封存时 reviewer_status=not_read 是当时状态，协调者收取本稿后应在后续授权汇总中更新；本角色不改写其记录。
