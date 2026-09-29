# Project-MONAI__MONAI-4583 独立交叉复核

结论：维持 needs_review/static_review、development_diagnostic。gold 对按坐标轴分别取首个非零索引造成背景 label 的缺陷有直接静态解释，历史 4 F2P / 5 P2P 差分支持局部修复。关键未决项是稀疏 3D 覆盖、条件性输入类型变化及实际 actor 开发条件；均不等于已证 gold 回归或 ready_for_probe。

## 暴露时序与身份

独立初稿 SHA256=`72b6a401811ec50d11f982abf54f72ab0b7e2c2ec43520ec337f71e4ddd37039`。2026-09-25 root 封存三份初稿并明确 cross_review release 后才阅读本题 public_read、主审四稿及 refs 指向的旧历史；初稿未改。主审分析稿 SHA256=`10bdd057c1373b8842b1679b70b02517d1a579a1f1fa42bb1f210f728e5f33aa` 与其 record 引用相符；旧 L1_monai_2/records/Project-MONAI__MONAI-4583.json SHA256=`5414f03cbe835279918e621548e1ccca9b0084e2c857f0d60d0fef75a0a80534`。未依据旧文本扩大阅读或执行范围。

## 技术裁定与覆盖

公开反对角 2D mask 的期望 box 为 [0,0,2,2]、class 0 而非背景 -1。原实现分别取轴上的第一个非零位置，组合出的坐标可能落在背景。gold 将 label 追加移到各分支中，用同一个非零点的对应坐标取值；2D/3D 分支均改动，边界框和结果转换逻辑保持。它不依赖某个唯一内部实现：直接从前景像素取 class 等合理路线也可满足已见断言。任务模型是每 channel 一个 box/统一前景类，不能凭空要求将同一 channel 混合类别拆成多个 box。

全部四个新 F2P 是两个 2D fixture 各两种输入：当前 CPU 条件下 _0 NumPy 单类、_1 Tensor 单类、_2 NumPy 双 channel/classes 0、1、_3 Tensor 双 channel/classes 0、1。helper assert_allclose 验证数值、容器类型和 device，未验证 dtype，不应多报覆盖。五个 P2P 包括既有 2D 矩形包装器用例和 3D 矩形/变换逆变换用例；旧记录“字典包装器完全未测”错误。现有矩形 3D 不触发同类稀疏索引错误，仅修 2D 的实现仍可能通过这些测试，因此缺稀疏 3D 反例是具体覆盖缺口（25），不是 gold 已回归（26）。

base tests/utils.py 711–719 行存在重复 CUDA 分支：CUDA 可用时第二个赋值以 TEST_TORCH_TENSORS+(gpu_tensor,) **覆盖**原 TEST_NDARRAYS，两个参数类型从 NumPy/CPU Tensor 变为 CPU/GPU Tensor。长度和四个 F2P ID 不变，NumPy 覆盖却消失。两位角色都在各自封存初判阶段独立识别该机制；主审后稿采用 check 19 issue、14 unknown 合理。这是跨条件的同名参数语义变化，不能凭它断言同条件随机抖动。public_read 对 GPU“加入”的宽泛表述应在最终汇报里改成覆盖原列表，单看 collect-only 的相同 ID 不能确认类型覆盖相同。

## 原运行及历史边界

仅按本题 run_refs 读取 baseline01 w06-0 共享账本第 1 行 noop、第 2 行 gold，不扩读其他题。命令为 `pytest -rA tests/test_box_transform.py`，noop 日志 8246538a 对应 4 fail / 5 pass、RC 1；gold 日志 609ff299 为 9 pass、RC 0。四个失败的 label 分别为 [-1] 对 [0]、[-1,-1] 对 [0,1]。逐个核四 F2P 与五 P2P 状态相符，无 expected 缺项、skip、xfail；差分只支持该历史 CPU 条件下的参数与数据。

source manifest 与实际 image ID 分开，后者在所给身份记录中为 null，不用 manifest 冒充实际容器镜像观测。原日志的源码导入与 noop 清洁/gold 候选源码改动是历史 grader 初态信息，不替代实际 actor 初态。git show 的基线提交说明也不是未提交改动摘要。历史成本不填为当前 actor 成本。

主审 delta 对旧记录纠正有据：已有矩形包装器覆盖；3D 漏测应归 25 而非已证回归 26；无实际 actor 验证不能给 ready_for_probe；同名 ID 不保证参数类型一致。旧报告提到修改断言 helper/conftest 的攻击路径，但目前没有完整生产 projection/restoration 和实际 actor 权限证据。local eval checkout 列表不足以证明攻击可达，也不足以证明不可达，check 31 保持 unknown、additional_exclusions 保持空，不把历史构想提升成已复现漏洞。

## 初判范围调整及下一步

我的初稿 check 24/pass 若被理解为全局不存在误拒，范围过宽，应收窄为 unknown；当前仅能说没有发现对唯一内部修法的锁定。主审 check 27/pass 明确限定局部修复正证据，可接受；我的初稿 unknown 指向更广的完整验证，两者不应机械合并为全部通过。26 unknown 维持，27 的局部 pass 不消除 25/19 的具体缺口或 actor unknown。

screening_record 的 check 18.note 残留“1121 materials-v1机制范围见issue”，属于跨题复制文本，后续授权修订应替换为本题 source/历史运行条件的限定。check 28 也宜从跨题泛称收窄为本题 mask/channel/class 前提。主审 sealed record 的哈希与身份没有因此失效；本角色只指出，不改写原件。

唯一优先下一步：在实际 actor 开发入口完成一个有目的的诊断，先用公开 2D 例，再用同一缺陷机制的稀疏 3D API 输入，记录导入来源、初始工作树、命令/RC、box/label/dtype/device 与实际参数输入类型；在独立私有 grader 条件对照 gold，才能区分开发环境问题与 3D 覆盖遗漏。无需全仓/GPU运行或先做模型实验，本角色不执行或派发该诊断。若任务二接口尚未给出，保持该项待核而不推断环境可用。

## 复核边界与结构检查

本稿为独立初判封存后、root 明确 cross_review release 后的第二阶段复核。仅阅读本题获准 public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json、本题 refs.json 指向的历史及授权原件；不以其他题结论投票。第一阶段的断言、helper、gold、调用者与原日志逐项核读见封存 reviewer_initial.md。此轮再核主审 expected 状态表与精确原日志，未执行或导入项目、测试、容器、安装、网络或模型；没有派发后续任务。共享工作区的阅读边界是流程约束，未声称操作系统隔离。

screening_record.json 的 13 个顶层字段、38 个稀疏 checks 的原编号及 status/evidence_refs/by、issues 的 category/scope/evidence_refs/proposed_action/status 均检查通过；并核对 facts_ref 的输入身份、分析稿 SHA 与 run_refs。additional_exclusions=[]、revision_refs=[]、needs_review/static_review、development_diagnostic 与成本 null 均符合本轮权限。字段齐全不代表全部语义已证实。check 3 实际 actor 输入、29 实际泄露情况及 40 全流程漏检/误拒边界仍 unknown；授权阅读 private/history 属于审查暴露，不等于 actor 曾见过这些内容。主审封存时 reviewer_status=not_read 是当时状态，协调者收取本稿后应在后续授权汇总中更新；本角色不改写其记录。
