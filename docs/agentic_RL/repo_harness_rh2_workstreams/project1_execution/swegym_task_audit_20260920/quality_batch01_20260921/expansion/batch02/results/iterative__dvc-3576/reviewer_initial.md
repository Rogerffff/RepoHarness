# iterative__dvc-3576 — 独立原件初判

2026-09-21；角色：Batch02 fresh reviewer；`scope=static_review`、`state=needs_review`、`intended_use=development_diagnostic`。本稿在读主审、公开读者与历史质量结论之前冻结。

**初判：冻结奖励只检验空 diff helper 返回空串；公开题面包含更多目标。base 已有缺失旧值处理，不能把全部 issue 当作未修；但 gold 没有把 “No changes.” 移至 stderr，也没有实现题面数值新增项的 `-` 显示。先用原例与一个 CLI 层替代解做定点对照，暂不把 reward=1 解释为完整满足公开要求。**

路径约定（均为权威桌面 ROOT，不是当前 worktree）：

- `ROOT=${REPO_ROOT}`
- `P=ROOT/runs/swegym_quality_batch02_20260921_v2/public/iterative__dvc-3576`
- `Q=ROOT/runs/swegym_quality_batch02_20260921_v2/private/iterative__dvc-3576`
- `R=ROOT/runs/env_recipe_repair_20260919/dvc_install_v1c/tasks/iterative__dvc-3576`
- 下文源码行号相对 `P/base/`；运行行号指实际 `eval.log`，不是环境摘要。

## 独立性、材料身份与证据层次

已读共用 reviewer 角色卡、记录模板、actor 环境卡及质量协议；本题公开 prompt/bundle/环境说明/base_identity，私有 test.patch、gold.patch、grading、validation、source_refs、run_refs 和 environment_record。已见 environment_record 的 `verified_environment_pair`、checks、report 等**环境运行摘要**；未打开它指向的 analysis/history，摘要不作为独立质量结论。未读任何 results 既有文件、public_read、主审初稿/卡/结构化结果、I2/history 或 B1/B2 聚合。本上下文还独立复核同包的 dvc-4166、dvc-1681，未接收它们的主审结论。

元数据核对：`source_refs.json` 的三个 S2 原件第 123 行与本题 public/grading/validation JSON 相等；base=`a338fad036bd9ac8bdd79ecec964f8c5558609c4`。gold.patch SHA256=`adee4b502b36c8feff0555f049affabef2bf4f043e14c56efad7c2184ffc3f10`，与本次 gold artifact/candidate.patch 字节一致；eval script 嵌入 test.patch 与 Q/test.patch 一致。gold/noop 的 recipe 文件与 environment_record 列出的五个哈希逐项一致，测试命令段在 before/after 间不变。

进一步将 P/base 的全部 349 个文件哈希与两侧 baseline_manifest 比较：348 个相同，只有 `setup.py` 不同。原始 gold log:175–186、noop log:161–172 明确展示 `moto==1.3.14.dev464` → `moto==1.3.14`。这是历史派生环境的初态差异，已在 baseline 中，未被误记为候选修复。目标业务源码与测试初态哈希相符。

本轮只读源码/日志并做 JSON、字节及哈希比较；未导入/执行 DVC、测试、安装、Docker、SSH、联网或模型求解。以下分为**静态源码推断**和 **09-19 历史真实 RH2 回放**；没有新的局部执行、当前 CPU 或正式 actor 证据。

## 公开目标与初始问题

题面四个目标：一侧没有旧 metrics 时仍显示新值；JSON 能表达缺失旧值；错误消息可理解；stdout 只放结果表，其余状态如 “No changes.” 放 stderr。正文一次写 STDIN，与末尾明确 STDERR 冲突，合理按末尾汇总理解为 stderr。题面示例对新增数值的 Change 是 `-`；“no old values”没有定义 JSON 必须省略键还是可用 null。

可公开定位：`dvc/command/metrics.py:108–158` 负责表格与 CLI；`dvc/repo/metrics/diff.py:78–100` 用 `.get(rev, {})` 并捕获 `NoMetricsError`，合并两侧路径；`_diff_vals:20–34` 已接受 old=None，`_diff_dicts:47–61` 展开 JSON。`show.py:241–255` 对不存在的 metrics 文件发可理解的 warning，`show.py:293–297` 在全无 metrics 时抛 NoMetricsError。因此原文 KeyError `'HEAD^'` 的路径在此 base 已有保护；本轮没有实际复现全部原例，也不把源码保护当作全路径证明。

剩余明显路径：`_show_diff({})` 返回 “No changes.”，`CmdMetricsDiff.run:152` 将它交给 logger.info；`dvc/logger.py:164–182` 把 INFO 发到 stdout、WARNING/ERROR 发到 stderr。gold 只将 helper 空输入返回值改为 `""`；没有新增 stderr 状态，也仍调用 logger.info 空串。`LoggerHandler.emit:105–111` 仍使用换行终结符，不能把该改动描述成已经验证 stdout 字节为空。

## 需求—断言双向映射（全部 1 F2P、6 P2P）

评分脚本实际执行 `pytest -rA tests/unit/command/test_metrics.py`，不是全仓 pytest。下表包含该文件全部七项断言；test.patch 唯一改动是 F2P 的期望串。

| 公开要求/旧行为 | 精确测试与决定性断言 | 对应程度及反向约束来源 |
|---|---|---|
| stdout 不出现 “No changes.” | F2P `test_metrics_diff_no_changes`：`_show_diff({}) == ""`，由原 `"No changes."` 改成空串 | 仅测内部 helper；没有调用 CLI、捕获 stdout/stderr。空串是达到目标的一种实现，题面未要求该 helper 的返回表示。 |
| 向 metrics API 转发 revisions、targets、type、xpath、recursive，JSON 命令成功 | P2P `test_metrics_diff`：parse_args 的 func 为 CmdMetricsDiff；mock diff 返回 {}；`cmd.run()==0`；mock 精确收到 HEAD~10/HEAD~1、json、x.path、True、两个 targets | 覆盖旧 CLI 参数契约；`--show-json` 分支运行但没有断言输出内容/流。 |
| 正常 JSON metric 表格显示 | P2P `test_metrics_show_json_diff`：a.b.c 的 new=2、diff=3，精确表格串 | 覆盖既有列/排版；并不调用 JSON 序列化。不能凭名字称 JSON 模式输出已验。 |
| raw 字符串值的差值不可计算 | P2P `test_metrics_show_raw_diff`：old="1"/new="2" 无 diff，精确显示 `diff not supported` | 旧 helper 行为；与数值缺失旧值用 `-` 的目标不是同一分支。 |
| 其它非数值变化保留 old/new 显示 | P2P `test_metrics_diff_no_diff`：old="old"/new="new"，精确表格串含 `diff not supported` | 覆盖已有非数值展示。 |
| 一侧缺旧值仍显示 new | P2P `test_metrics_diff_new_metric`：直接喂 old=None/new="new"，要求 `diff not supported` | 仅字符串 helper 示例；不覆盖题面新增数值、HEAD^ 文件不存在、真实 repo/CLI。 |
| 删除 metric 的旧行为 | P2P `test_metrics_diff_deleted_metric`：old="old"/new=None，要求 Value None、`diff not supported` | 相关回归；不调用真实删除/版本选择路径。 |
| 缺失旧 metric 的 JSON 与可理解错误 | 冻结选集没有对应输出/异常断言 | base 公开 `tests/func/test_metrics.py:973–1006` 有 no_metrics/new/deleted API 断言，但本次不执行且不在 F2P/P2P。 |
| 非表状态转到 stderr；新增数值 Change=`-` | 无流捕获、无数值新增表格断言 | gold 的 new 数值缺 diff 时仍经 `change.get("diff", "diff not supported")`；对题面示例存在静态不一致。 |

已展开相关公开功能测试 `tests/func/test_metrics.py:882–1006`：raw 改变/不变、JSON xpath 开关、JSON 不变、坏 JSON 的 unable-to-parse、无 metrics、新增/删除 metric；它们保护更广 API 行为，**不能计作冻结奖励已有覆盖**。单元 dvc fixture 经 `tests/conftest.py`/`tests/dir_helpers.py` 初始化临时仓库；主要 F2P 纯 helper，P2P CLI 调用对 API mock。

## 合理替代解、gold 与回归

一个有根据的替代路线是在 `CmdMetricsDiff.run` 的空 diff 非 JSON 分支把 “No changes.” 发 stderr 并跳过表输出，保留 `_show_diff({})` 的旧返回值供其它调用者；对新增数值将缺旧值的 Change 设为 `-`，非数值的既有 P2P 展示保持。这直接服从公开行为，却会因私有 helper 空串断言失败。它是**静态误拒候选**，尚未写补丁或执行；不能声称已证明一份完整替代解 reward=0。最小对照应同时核公开行为、其它六项参考与唯一 F2P。

gold 是自然的窄修复：历史已得 reward=1，但仅删除用户状态文本。如果公开需求允许完全省略状态，stderr 缺文本可以另行解释；题面明确提出迁移，不能默认为已经完成。新增数值仍显示 `diff not supported` 是更直接的原例差异。JSON 的 old:null 对“缺旧值”的表达未被公开精确定义，不据此另造错误。

全部 `_show_diff` 相关分支与 CLI 调用已读，未发现 gold 改坏非空表格的直接证据。精确排版 P2P 有实现约束，但它们保存原有输出，本轮不自动判全部排版断言为错误。API 的真实 revision/metrics 读取没有进入此次执行选集；不据七个单元测试推断其回归均受保护。

## 历史运行原件

| 原件（相对 R） | 核实事实 |
|---|---|
| `gold/ledger.jsonl:1`；`gold/eval_logs/evallog_replay-er19-dv1-iterativ_4d6e3c69.eval.log` | log 哈希 fdb62b21…fdb3c4 与 run_refs/ledger 一致；log:216–228 官方单文件恢复/应用成功；:555–564 安装成功；:574–609 七项实际通过，F2P 1/1、P2P 6/6、reward=1，test_rc=0。 |
| `noop/ledger.jsonl:1`；`noop/eval_logs/evallog_replay-er19-dv1-iterativ_9ae4a68d.eval.log` | 哈希 58381050…28e5 一致；:560–604 实际七项，:573–575 失败为 `"No changes." != ""`；F2P 0/1、P2P 6/6、reward=0，test_rc=1。 |
| 两侧 `recipe/recipe.json`、before/after 脚本、diagnostics、projection、frozen_patch、stage、driver 原件 | 同配方离线 `pip install -e '.[all,tests]'`；日志 `Looking in links: /opt/rh2/build-wheels`。gold 冻结仅 dvc/command/metrics.py；noop 无条目；excluded_pathset_changed=false；official test 恢复数 1；清理 removed=true，driver 无残留/失败记录。 |

该对照使用派生镜像 `sha256:0c322496575e0bca8592b7114fc069fab01cfabc225944b51346a97871533cf8`、Python 3.8.19、pytest 7.4.4，`rh2grader/54322`、deny_all、2 CPU/4 GiB、64 MiB shm；允许写解释器前缀 `/opt/miniconda3/envs/testbed`。观察到工作区导入 `/testbed/dvc/__init__.py`，环境资格 env_qualification=absent。`candidate.apply_user=agent/54321` 只说明回放应用 patch 的身份，不是 actor 会话。

## 开发条件与交付边界

| 需要的操作/资产 | 公开依据 | 现有证据与缺口 | 最小后续验证（本轮未执行） |
|---|---|---|---|
| 定位 CLI/metrics 入口并从工作区导入 | 上述 source/公开测试；setup.py:49–85 包含 flatten_json、texttable 等 | 入口清楚；历史 grader 导入正确，正式 actor 未验 | agent 实际工具 shell 打印 id/cwd/PATH、sys.executable、dvc.__file__，确认工作区修复生效。 |
| 运行窄测试、构造 Git 两版本与临时 metrics | `tests/dir_helpers.py` 的本地临时 Git/DVC；`tests/func/test_metrics.py:882+` | 不需模型权重/外部数据或远端服务；conftest 顶层 mockssh 等导入仍需预装 | 公开单元文件及功能 `-k metrics_diff`；再捕获原例的 stdout/stderr/JSON。 |
| 准备依赖与可写临时目录 | setup.py 的 `[all,tests]`；环境说明无默认公网 | 09-19 安装修复及 moto 初态差异已核；公开原镜像是否消费这些依赖未知 | 在 actor 候选配方准备阶段固定 wheels/依赖；不把 grader 的前缀可写权限转借 actor。 |
| 修改并提交 source | 合理修复在 dvc/command/metrics.py，必要时 repo/metrics 或 logger | gold source 已投影；无需改 official 测试或不可提交资产 | 核候选提交包含 source，执行公共复现；不用改测试以争取得分。 |

当前控制面只作静态核：`rh2/src/repoharness2/adapters/slime/prepared_task_face.py:312–355` 从 test.patch 取精确 official files，`test_globs=()`，正式 rollout 仍选 **public.image/public.image_manifest_digest**。本题 official 恢复仅 `tests/unit/command/test_metrics.py`；并非按所有测试名恢复。公共旧 hints 的“所有测试改动永不计分”解释过时，实际消息传递未捕获；本题合理 source 修复不需要违反其禁止改测试指令。

`RolloutSandboxProfile` 是 agent/54321，默认隐藏 `/root`；materialize 的 BASH_ENV 文件在 `/root/.rh2_bash_env`。这里只记实际 shell 激活/PATH 待验，未宣布已坏或已激活。原公开镜像 digest 与上述派生 grader 镜像不同，未验运行时答案线索、Git 历史清理与实际工具配置。

当前 `scoring.py:189–270` 依冻结 F2P/P2P 计分，普通已完整结束 pytest 的非参考失败不自动把 reward 变 0；全局启动/收集失败由 manager 另判。本题七项恰好都是参考，不能向其它执行范围外推。

## 八方面完成范围与处置

| 方面 | 本稿状态 |
|---|---|
| 公开需求 | 已拆四目标与 STDIN 笔误；JSON 缺值表示仍有解释空间，未读外部答案。 |
| 材料/初态 | 精确 S2/base/patch/回放链已核；部分旧问题 base 已处理；moto 环境差异已单列。 |
| 测试匹配 | 全部新增/修改断言、全部 F2P/P2P 已展开；真实流/原例及功能分支缺冻结覆盖。 |
| 合理解误拒 | 有 CLI 层替代路线；仅静态候选，尚未执行。 |
| gold/回归 | source+七项 helper+相关公开功能测试已查；gold 完整满足原例未成立，不穷举其它命令。 |
| 开发条件 | 本地资产足够的源码依据已给；历史 grader 可用；当前 actor 激活、依赖与权限未知。 |
| 交付/评分 | source 可投影，精确 official 文件恢复已核；无额外排除建议；没有全套隔离/泄漏验收。 |
| 关系/用途 | 与同审另外两题目标不同，未证同问题派生，不因同仓并簇；暴露 gold/隐藏测试，不作为 solver；不估模型成功率。 |

唯一优先下一步：在被授权的同一派生配方上，对 base/gold/上述 CLI 层替代路线执行题面新增数值、JSON 与空 diff 的流捕获，再跑冻结七项；把“公开满足情况”和“参考 reward”并排记录。若 gold 与完整公开要求的差异得到确认，再决定缩小公开题意或补行为测试，不能先按 gold 倒写规格。此后仍需正式 actor CPU 条件验收，静态候选不等于 ready_for_probe。

费用/token 未获工具计量，记 null；本轮项目 CPU 命令未执行。初稿完成后按全包门禁暂停，等待协调者开放第二阶段材料。
