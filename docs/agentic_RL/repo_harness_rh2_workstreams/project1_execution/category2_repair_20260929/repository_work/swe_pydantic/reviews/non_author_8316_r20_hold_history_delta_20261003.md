# 8316 R20派发hold历史guard：非作者静态增量审查

日期：2026-10-03。结论：**指定guard增量静态审查通过**。当前helper可在题主已核收的版本范围内支持一次8316 R20十九行受控接续；本报告不派发、不证明CPU恢复或GPU资格。原R20输入审查、冻结七成员封包、144参考及材料均不回写或重审。

我已有私有材料与旧CPU上下文，不是fresh公开读者。只读本题private helper、归档hold、范围审查及题主disposition，使用本地标准库SHA/字节/AST/JSON；没有执行helper、SSH、Docker、task tests、安装或模型。只写本报告MD/JSON。

## 实际变化

当前 `dispatch_8316_r20_v1.py` 为5096字节，SHA `211dbddbd14df40de37a60d6259138d8ba7ac079ff64becb01b0122c3c64f8e6`。将新增hold/disposition/delta guard块还原为旧块，并还原日志中的own_hold_scope后，整文件字节SHA精确回到此前已核的 `dafcd0a501e5dc1d919ef137cd7e4791ec6c02365b46e39217423f1ae85bc9fd`。因此CPU派发主体、固定input/runner核对、上传gate、预算、8316任务/namespace、正式十九行及actor前置条件都没有新增变化；不是只凭局部diff推断其余不变。

原434字节hold已由题主移到 `runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/cpu_infra_hold_8316_r14_20261003_archived.json`，SHA仍为 `ce3b1b2581109b955261c5da6d689df0dd219ffd6f5f34e03714710e19160f5b`。历史原文、旧job、失败等待事项和原范围全部保留。旧R20静态输入报告的“当时hold原路径仍在”也是历史事实，旧报告字节未改；当前处置由新disposition单独说明。

## 新guard的范围

若任何新的 `cpu_infra_hold.json` 存在，helper在创建job/journal和远端命令前退出75。sequence hold原gate仍保留。通过这一检查后，还要求归档原hold SHA、scope_review_accepted、old_R14_retry_allowed=false、disposition中的8316 source_release和formal_inputs SHA与当前R20输入相同。再要求本delta JSON通过字段及**当前helper自身裸SHA**相同，防止用本静态报告批准随后未审helper。

题主 `cpu_hold_scope_disposition_v1.json` 绑定已读核的6283独立范围报告；本次完整读范围报告，核其结论及SHA，并重新核disposition的36件历史/来源绑定（原hold按归档位置核同字节）。加上本题入口及报告等，共42件本地文件绑定、50项程序化材料断言通过。这不是新CPU运行验收，也没有机械重审6283旧375或8316旧759原件。

disposition只准一次6283 R19/reset300和一次8316 R20/reset900，禁止原R14重试，并明确首个新infra或清理未知保原件、建新hold后停。6283不必等待8316成功的范围结论有自己的已核旧精确镜像/预算依据；不能把8316未来900秒成功当成6283的300秒证明。本次只复用该已审范围判断，不重新裁决6283语义或实测。

## 必须保留的限制

`allowed_once` 是题主的执行范围约束。**当前helper没有消费一次性令牌或阻止同一版本第二次手动调用，也不会自行创建新infra hold**；它不含自动循环，且正式runner首次异常停止仍未改变。因而本报告通过只适用于题主执行的一次受控接续：不得把helper可再次调用当成再次运行授权；首个新infra/清理未知必须由题主立即建新hold并停。若以后要无人值守派发，应另审一次性计数及失败自动hold机制，不能把这些能力说成已实现。

新actor依旧要求真实新十九行通过、清理无残留及R20 source身份；本报告不替代该核收。当前helper的模块说明仍有“保留6283暂停”的旧文字，已与新处置不符；这是不影响执行guard的文档残留，实际scope以disposition及代码为准。任何后续helper字节改动都会使本delta SHA guard拒绝，需重新绑定审查。

当前读取时新infra hold和sequence hold均不存在；此事实不证明CPU空闲、负载恢复或新预算足够。题主报告6283正在尝试公平槽，本报告没有审该新作业结果，也未派发8316。实际CPU恢复、8316新矩阵通过、actor核收、GPUready和训练资格全部保持false。

完整身份、原字节还原结果及本地绑定见同名JSON。无本窄范围内决定性静态阻断；旧输入/封包/审查历史、归档hold和共享代码均未由本审查修改。
