# 8511 v2 原完整 FP 重评分请求：非作者最终窄核

日期：2026-10-04。审查者：Codex（review_remaining_materials）。

**结论：本次源码增量和实际生成请求通过；没有新的静态阻断。** 可沿既有流程提交固定请求 `swe-pydantic8511-behavior-v2-fp-regrade-20261004`。此结论只覆盖原完整 FrozenPatch（冻结候选补丁，简称 FP）在新材料下另建评分作业的请求，不代表 GPU 兼容核验、原 FP 的177参考重评分、模型新求解或训练准入已经完成。核查时请求尚未提交，GPU 尚未通知。

## 范围与方法

我已接触8511私有测试、既有 CPU/GPU 证据和作者材料，**不是 fresh 公开读者**。本次仅本地读取、标准库 JSON/AST 与 SHA/字节检查，没有执行作者生成器、远端命令、Docker、安装、项目测试或模型，也没有改旧报告、旧分数、发布封包或原件。

复用已完成的材料审查、R27目标修复输入审查、原 GPU 首臂封存意见和本轮实际 CPU 独立报告。本次没有重复526个 CPU 原件或177逐参考验收；重新核固定 CPU 报告、实际 status、快照及所有新请求路径的当前字节绑定，并核题主528项声明与独立报告526项及两报告构成的精确集合。另核11个 supporting 文件。随附 JSON 列出**42个去重本地文件**的实际 SHA/字节；请求自身、21个去重嵌套路径及 external manifest 合计**23个请求绑定**，与题主实际请求读回证书的精确集合相同。

## 可选 error 键修正

当前生成器 `generate_8511_v2_targetfix_fp_regrade_request_v1.py` 为9842B，SHA `50df23b364586634dbbba796f5370451b6e505058134a8a0dbaba73b876deb68`。与保留的9838B、SHA `80d9cef0d6bf55cf2660f8fcde65de130212b78fcf2105d5fc613d19438dda84` 版本逐字比较，唯一变化为 `actual['error']` → `actual.get('error')`，其他 guard 字节完全相同。

实际成功 status 没有 `error` 键。旧直接索引因而在写文件前触发 KeyError；803B失败记录、旧源码均保留。新表达只允许键缺失或显式 null，非空错误仍拒绝；同时仍要求成功状态、四行顺序及reward、全部checks、固定input/runner/R27身份、177参考、实际清理与指定 CPU 独立报告通过。它没有放宽评分条件。所有检查位于唯一第71行排他式 `open('x')` 新文件写入之前，不覆盖旧请求。AST按Python3.8语法解析通过；这不是在Python3.8运行此本地工具的实测。

第一次尝试的失败记录声明输出未创建、CPU重跑false、模型采样0，与其写前失败位置相符。题主通知attempt02本地RC0、stderr空；本审查没有另读该次 stdout/stderr 原件，独立确认的是实际生成文件已存在、20901B、完整内容和SHA符合本轮绑定。

## 实际 CPU 前置证据与新请求的 join

实际 CPU job 为 `pyd8511-formal-20261003175031-v27-dc821`，独立 CPU 报告 JSON（279710B，SHA `0b765a0293dbe0d9d3d69c10029b78df9a951f94c0b6155dc3e1fca248eea7c3`）的 `actual177CPU_executed`、`cpu_review_passed` 和实际清理字段为true，无阻断。快照3525B、SHA `35f09f905b0f4eb3512067f4f9212eef8dc609d79e4077c10f1c621a44e4c6c5` 与status25016B、SHA `54aa5f57c4de4f63baf622ee9969860374238ce7b6f64628e5c5fd0d2fb93d09`、固定input/runner、两报告及题主核收一致。新请求明确绑定这些原件，没有靠孤立passed标记代替它们。

复用的实际四行顺序和reward为 `noop/gold/narrow/qwen_original = 0/0/1/0`；每行177正式参考。本轮源码等价Qwen负对照保留旧173通过，而新增4项字段保留P2P失败。gold仍有继承范围回归，narrow全177通过。CPU独立报告已分清正式参考与额外SKIPPED节点，本请求未借其扩大参考数或宣称全项目通过。

status、快照和独立报告的cleanup内容相同，实际最终RC0、4个grader创建并移除、open/failure集合空，残余容器和网络查询RC0且空输出；该实际验收复用独立报告的资源观测边界。本次不会将CPU源码等价FP（canonical `538ca970…`）冒作原GPU完整FP（canonical `4c305765…`）已重评分。

## R27身份、177参考与安装/预算边界

请求只含8511，来源为 `cat2-cpu-r2e094095-swe40-pyd8511-fieldinfo-v2-test-target-20261004-v1`，manifest SHA `897cac778bce053740d7ac6dce9b2e90ac96a553a119c0bbdfe7e62b298cfe0d`。producer、registry、revision、四bundle、effective patch、安装资产及真实R27发布回执均核当前路径SHA/字节，且与已核fixed input/spec的身份相同。revision SHA `717aa364…`、有效补丁SHA `6f7360d5…` 和公开/环境/E10边界沿用已核范围。

177参考为1F+176P；请求的源分区为原SWE 1F+168P，再加历次8个P，合计177，也就是旧受审173加本次4个P。新命令完整保留 `tests/test_dataclasses.py` 目标。固定input SHA为 `88939f7d852133b2b6130f8d2e2c5a3237e9c7bdd13ed994dfa25c6782f368cd`，runner逐字保持原SHA `b127f730…`。spec预算仍reset300/apply120/test1800；候选阶段900、评分3600、清理120等原请求预算是另一层预算，没有将reset300改成900。

原公开题面/base和首臂交付身份保持。镜像、wheel recipe/manifest/assets及public delivery与旧请求一致；实际CPU证据为Py3.8.19/core2.14.5，UID54322，镜像精确Id `sha256:df6c3affb7ea6fd826f44863ec92926f7b52558dd0f1b42e05f97aec9fe8ca68`。新请求要求GPU使用既有精确缓存、不新增build/pull/load，缺缓存或新consumer兼容支持由共享发布流程处理。**CPU-a的R27部署成功不是GPU当前代码或镜像缓存兼容已验的证据**，请求明确将这部分交给后续实际评分支持与回执。

## 原完整 FP 与 baseline 运输保留

原job为 `gpu1003-pyd8511-qwen36-a1`。下列完整文件均重新核本地字节SHA，并与原8511首臂题主封存证书相同；FP和baseline manifest的canonical JSON digest也重新计算一致。这里核整个运输文件，未重复旧tar逐成员census或运行重放。

| 原件 | 字节 | 文件SHA256 |
| --- | ---: | --- |
| frozen_patch.json | 18256 | `4f0aa344d0595d05cea68a448bce3cdda581d8d09f589a1141c666d963f1ba22` |
| baseline_manifest.json | 107617 | `9c61a99b9720ca2d4a1d2ce61c855f05d9839d4de2b5830e96c72fb332837672` |
| baseline.tar | 7075840 | `6207027aa65a3caad3ce78cbb4d08081b2f74a56432bbd6b25e91a1062c472d2` |
| trajectory.jsonl | 643304 | `e7be9964540259ae9ba7323c2fc19ae4ec808bd1bc973eeba89ff117a4d1d932` |

FP canonical为 `sha256:4c305765cca042e14a8b79ebafa304394739f982b0eb68a471a47efbf92b3da1`；baseline canonical为 `sha256:40135f281c216e76a04de6772eaaadcdfd0b46d949e98c5164f29cba2f454e45`。原base、公有bundle及df6c镜像相同。原 `excluded_pathset_changed=true` 明确保留，baseline原环境摘要null亦保留，不把它们改成当前v2身份。新请求新增完整 `original_baseline_tar` 运输pin，评分时必须核原FP/baseline及投影语义，不能仅发送CPU生产源码diff替代。

## 请求用途与尚缺实际证明

实际请求20901B，SHA **`e94ec718add3e42785141c8e38f25928d8268e7cc8f7b81f10c463ad42bea6e3`**，状态为 `cpu_acceptance_complete_original_FP_regrade_only`。model budget的 `attempts_per_model=0`、`new_model_sampling=0`、`additional_samples=not_requested`；Qwen只复用已完成首臂候选，Coder新增次数0、重复0，无新actor/首请求或模型服务。该接续属于已有有效首臂补齐新版评分证据，材料边界和旧173/raw1均保留，新177结果须另记新job，不机械覆盖旧分。

当前题主请求读回证书8005B、SHA `989d7756e1930b40faa961058efe2aff361e299f9f577d361f9ca5f90cd1bf1c` 固定的23项集合全部吻合。证书保留“本独立审查pending”的历史字段，未回写；此新报告给出本次终结论。证书同时明确未提交board、未通知GPU、原完整FP新评分未执行。

后续仍需真实GPU R27 consumer/code兼容与精确镜像缓存核验，原完整FP/baseline运输、安装/core、177参考逐ID及分区、新reward、资源/终止与容器网络清理原件。旧实际raw1不变，新v2评分尚未发生。本报告不授予typed训练、留出、稳定成功率或新模型能力结论。

完整本地绑定见[同名JSON](non_author_8511_v2_targetfix_regrade_request_review_20261004.json)。只写此MD/JSON，无其它文件变更。
