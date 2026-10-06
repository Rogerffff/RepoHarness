# Project-MONAI__MONAI-3566 独立交叉复核

结论：维持 needs_review/static_review、development_diagnostic。历史 itk_v2 中 1 个 F2P 和 20 个 P2P 的差分成立，但核心限制是公开默认读取需求与测试私有 `series_meta=True` 接口之间的差距；既不能据此批准实际 actor 环境，也不能沿用旧记录的永久环境阻断或模型猜测率判断。

## 暴露时序与身份

独立初稿 SHA256=`1cf6e386c6ae509f5388d4b1201dfb44d7db29d26e1f1cfb03f9df46886fbc41`。只在 2026-09-25 root 核三份初稿封存并明确 cross_review release 后，读取本题其他角色五份输出及 history/Project-MONAI__MONAI-3566/refs.json 所指旧记录；未改初稿。主审分析稿 SHA256=`60772209144b70492316aef2ba6ca03fbf891d2a9baee9be3ea9d17733320ec5`，与 screening_record 的引用相符。旧 L1_monai_1/records/Project-MONAI__MONAI-3566.json SHA256=`7dbdf7fba67eee3deb9a781ea18ff480700a57dfbbe2dcc97b3daea2694b4e47`；旧文字与此轮直接核过的原件证据分开。

## 技术裁定

公开问题使用默认 LoadImage/ITKReader、itk.UC 和 DICOM 目录，要求保留可取得的 tags。gold 新增默认 False 的 series_meta，只有 opt-in 时另建 ImageSeriesReader、Update，再把首片 dictionary 写回原体积。它提供了接口能力，却保持公开示例默认行为不变。新 F2P 显式使用此前公开问题没给出的 `series_meta=True`，检查 `0008|103e` 并比较 `Series Description=Routine Brain `（含末尾空格），没有验证默认路径，也没有使用输出影像。这是可定位的契约差异；合理的默认提取实现可能因不接受额外关键字而被拒。证据不支持“只有 gold 内部算法能通过”。严格 padding 是否应保留取决于元数据忠实性契约，不能先断言任何规范化均为合理且必然误拒。

完整 gold 与调用链静态核读支持：读取后的 metadata 经 switch_endianness 保留字符串，LoadImaged 可保存 LoadImage 返回的 metadata；不能说未测试的字典包装器一定损坏。第二次读取没有沿用 kwargs，确有额外 IO/像素类型兼容性的未测范围，但无本题运行证明新增回归，check 26 维持 unknown。单张 slice 元数据用于 series 的策略存在语义边界，不能凭 TODO 或首片策略直接判错。

test.patch 的另一改动只是 TimedCall Linux 成功用例 timeout 从 10 秒改 20 秒，不能把它当成 DICOM 语义修复。20 个 expected P2P 包括 15 个 load_image 与 5 个 timing 用例；实际还有 5 个非 expected 旧 ITK 用例运行。逐个对照 21 个 expected 原始日志状态全部匹配。旧 DICOM 路径、形状、affine 和逆序索引用例没有新增 opt-in metadata 断言。timedcall_dist 的名称不能作为 GPU 要求或永久随机失败的证据。

## 历史运行与旧判断边界

只核本题 run_refs 精确授权的 itk_v2 noop/gold 账本第 1 行和 eval 日志。实际命令 `pytest -rA tests/test_load_image.py tests/test_timedcall_dist.py`；noop 为 25 pass / 1 fail、RC 1，gold 为 26 pass、RC 0，expected 无缺失、skip、xfail。noop 727–793 行在新接口调用后到达 LoadImage 的最终 cannot-find-suitable-reader RuntimeError，尚未到 tag 值断言。源码支持额外 kwargs 沿读取链传递的解释，但原日志没有底层 ITK TypeError，不应把推断当成直接观测错误。

itk_v2 离线 wheels 固定 ITK 七个组件为 5.2.1.post1、numpy 1.23.5，随后执行原 requirements 与 setup.py develop；最终安装命令 RC 0 不等于每一安装子步骤都有独立观测 RC。历史 gold/noop test_seconds 分别为 52.733/54.057，只是该次 grader 耗时，不能写成 actor 成本。实际派生镜像 ID `sha256:eae21d6d574c7cd6107c0b2ee1c67d613e3c7af89f58ee91253e616515d866c3` 与 source manifest 分开；脚本 digest `d808c4f1fb4a20294e2c787722b1e551724a1062c9ec83bb0747d652f89a06a8`。该历史环境使旧 ITK 失败消失，不证明当前 actor 的解释器、包、资产、初态与权限。

旧记录的“五个 itkMatrixF44 阻断一直存在”、spawn 会随机失败、模型几乎不可能猜到接口等判断不再可直接用于当前材料。主审 delta 正确区分旧报告与本题新版运行：接口落差有静态证据，猜测概率无实际实验；一次运行通过也不证明从此永不 flake。保留这些边界比简单接受旧 reject 或以全绿推翻全部质量问题更准确。

## 初判调整及记录修正

我的初稿 check 2/pass 与 check 20/pass 范围过大，分别接受主审收窄为 unknown（公开原例未在实际 actor 条件复现）和 issue（score 差分含私有接口契约）。check 27 从 unknown 明确为公开目标完整性 issue，同时保留 opt-in 局部功能的正证据。其他未测兼容性不可并入已证回归。主审方向有原件支持，不是按角色人数裁定。

screening_record 的 check 18.note 残留“1121 materials-v1机制范围见issue”，不适用于本题，应在后续授权修订中替换为本题 itk_v2 限定；check 28 的跨题式泛称也宜改成本题具体数据/接口限制。这是记录引用精度问题，不推翻已核 run identity 或 21 项状态。此角色不改主审封存文件。

唯一优先下一步：由规格负责人明确 tags 应默认出现还是 opt-in，并把公开说明、候选兼容接口与目标断言对齐。接口契约未定前，额外 CPU 或模型试做无法区分环境失败与合理实现被额外关键字拒绝；不建议以猜 private 参数成功率代替契约裁定。

## 复核边界与结构检查

本稿为独立初判封存后、root 明确 cross_review release 后的第二阶段复核。仅阅读本题获准 public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json、本题 refs.json 指向的历史及授权原件；不以其他题结论投票。第一阶段的断言、helper、gold、调用者与原日志逐项核读见封存 reviewer_initial.md。此轮再核主审 expected 状态表与精确原日志，未执行或导入项目、测试、容器、安装、网络或模型；没有派发后续任务。共享工作区的阅读边界是流程约束，未声称操作系统隔离。

screening_record.json 的 13 个顶层字段、38 个稀疏 checks 的原编号及 status/evidence_refs/by、issues 的 category/scope/evidence_refs/proposed_action/status 均检查通过；并核对 facts_ref 的输入身份、分析稿 SHA 与 run_refs。additional_exclusions=[]、revision_refs=[]、needs_review/static_review、development_diagnostic 与成本 null 均符合本轮权限。字段齐全不代表全部语义已证实。check 3 实际 actor 输入、29 实际泄露情况及 40 全流程漏检/误拒边界仍 unknown；授权阅读 private/history 属于审查暴露，不等于 actor 曾见过这些内容。主审封存时 reviewer_status=not_read 是当时状态，协调者收取本稿后应在后续授权汇总中更新；本角色不改写其记录。
