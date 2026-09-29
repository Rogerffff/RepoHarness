## 结论

**需小改：R-c 草案通过，可落正式修订单；R-b 属于 P5，不能直接按预授权落地。用户裁定前，整题只作问题定位。**

本轮仅只读核对、内存重放和摘要复算；未修改文件、未重跑容器。

### 1. 模板与公开依据

**两项 R-c 用对，公开依据及行号成立。**

- **参数转发测试**：题面要求一般性的 API `kwargs` 转发，不限于示例中的 `dataset`；新增显式 `number` 参数构成非示例实例。Dataset 方法确实把实例及位置参数转成关键字参数。[题面第 8 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/datalad__16c1ffc349df566151db0beb6d355ca27266bb8c/user_prompt.txt:8)、[dataset.py 第 444 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/datalad__16c1ffc349df566151db0beb6d355ca27266bb8c/worktree/datalad/distribution/dataset.py:444)。
- **旧式过滤器兼容测试**：类级 Constraint 过滤器、带关键字调用的单参 lambda 都是已有公开用法，不是新增需求。[create.py 第 90 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/datalad__16c1ffc349df566151db0beb6d355ca27266bb8c/worktree/datalad/distribution/create.py:90)、[test_clean.py 第 39 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/datalad__16c1ffc349df566151db0beb6d355ca27266bb8c/worktree/datalad/interface/tests/test_clean.py:39)。

`[1,3]`、`[0,2]` 来自公开假命令的 `range(number)` 和过滤条件，**不是抄 gold 输出**。内存重放确认：两个版本摘要均正确，原八键状态不变，新增两键，共十键；没有删测试或遗留 unexpected。本轮不涉及 R-a、R-e、R-f。

### 2. 验收证据

15 份试跑的逐键摘要与记录一致：

| 版本 | 得 1 | 得 0 |
|---|---|---|
| R-c＋R-b | gold、C1、C2 | noop、D、N、F、C-ign |
| R-c-only | gold | noop、C2、F |
| R-b-only | F（新增漏洞） | — |

- 主正对照仍是 gold，不依赖替代解兜底。C1/C2 的旧式过滤器兼容性已有新增测试的执行支持。
- 当前材料的正式评分也核对一致：D、N、C1 为 1，C2 为 0；补丁摘要、投影、完整日志及失败位置对应。
- 新版 D/F/C-ign 的失败**键**有执行证据，但精确失败断言仍是源码推断，尾日志没有保留完整详情。
- “10/10”表示**十键符合期望**，不是十项测试通过；五个期望 FAILED 的死键仍在。
- R-c-only 的 D/N/C1/C-ign 未另跑；与完整版只差 `sadfilter`，复用推断合理，但不能写成实测。

**正式验收尚未完成。** 新材料及镜像落地后，须以正式评分确认摘要、交付、键集和失败详情。[正式矩阵](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/datalad__16c1ffc349df566151db0beb6d355ca27266bb8c/revision_plan.md:490)需补正：R-c-only 不能漏掉 D、N；C-ign 已是已知相关错误候选，不应继续列为可选。

### 3. R-b：我判为 P5

**不同意“只是同一信息的两种表示，因此不是 P5”。**

- 严格读法有依据：题面说 API 调用的关键字参数，同函数渲染器也只接收 `_kwargs`。[utils.py 第 1048 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/datalad__16c1ffc349df566151db0beb6d355ca27266bb8c/worktree/datalad/interface/utils.py:1048)。
- 默认值读法有间接依据：CLI 确实设置默认值，并把全部参数显式传给 API。[base.py 第 274 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/datalad__16c1ffc349df566151db0beb6d355ca27266bb8c/worktree/datalad/interface/base.py:274)，另见该文件 311、338 行。
- **但 CLI 显式传入 `dataset=None`，不等于 Python API 未传该参数。** 对按 `'dataset' in kwargs` 分支的过滤器，两种行为可以产生不同结果；这不是不可观察的内部实现细节。

因此，现有公开材料不能唯一消解参数集合的边界，属于 P5。未来版本不能补作本题公开依据。A 技术上可取，但须用户选择；B 同样不能自行借 R-f 选定严格目标。[v1 P5 规则](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md:79)。

R-c 没有扩大需求或泄漏答案。R-b 也不是为了保 gold——gold 原本就通过；但裁定前，C2 应称“待决读法”，不能直接写成“已确认误拒”。

### 4. profile 差异与需改内容

**profile 差异已能精确解释，不再只是猜测。** 我分别加载当前代码和 `83760b15` 的父版本，复算得到：

- 旧：`1bb8e0cf…`
- 新：`3ec1bfa8…`
- 参数差异只有新增 `tmpfs_mount_flags="exec,nosuid,nodev"`，对应 `/tmp` 挂载变化。[摘要字段](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/sandbox_profile.py:574)。

所以必须撤回“profile 相同”，但**不推翻本批同镜像、同新 profile 下的对照结论**；1200 s 包装也确实只改准备时限。不能据此声称新旧环境完全相同。

落单前的小改：

1. 修订说明统一改成 **P5 待决**；“C2 核心正确”“已纠正 T1”改为条件判断，“唯一漏洞是 F”改为“已验证的新增放行候选是 F”。
2. 补齐上述正式验收矩阵，并更正 profile 记录。
3. 成本说明补一句：先落 R-c 后，未来 R-b **不能简单追加同目标条目**；当前摄入器禁止同题同目标重复修订，后续需解决替代机制。[限制代码](/Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/envpack/ingest_r2e_subset.py:415)。

**停止条件：R-c 无需扩大修订即可推进；R-b 等用户裁定。D′、不可内省 callable、死键等继续登记，不把本次局部通过写成整题正式准入。**