# R2E 环境检查项（R01–R20）与逐题记录形状

2026-09-24 / Claude（B 线）。从 [40 项清单](../environment_screening_checklist_20260915.md) 里取与"环境资格"直接相关的项，按 R2E 的材料形态（镜像预装、隐藏测试私有恢复、期望映射可含 FAILED / ERROR、无安装段）改写判定依据。题意 / 反作弊 / 真实求解（清单 §6–§8）不在本轮。

状态词汇：`pass` / `issue` / `unknown`（证据不足，写缺什么）/ `not_applicable`（写理由）/ `not_checked`（未列即此）。自动项由 `collate_facts.py` 或探针填，人工项由 sub-agent 读证据后填，都必须带 `evidence_refs`。

## 1. 检查项

| 编号 | 对应清单 | 问题 | 判定依据（R2E） | 填写者 |
| --- | --- | --- | --- | --- |
| R01 | 1 | 身份对应 | 派生镜像 21 项复核 ok；覆盖表 `base_image_manifest_digest` == 环境包；`hidden_tests_tree_sha256`、`run_tests.sh` sha、HEAD == 评分面 | 自动 |
| R02 | 2 | 初态含问题 | noop reward 0 且 `num_parsed_tests>0`、`missing=[]`、`mismatched≠[]`（0 来自目标测试，不是零解析 / 缺席） | 自动 |
| R03 | 3 | 求解者输入 | 公开 prompt 含完整题面（长度、代码块）；`public_hints` 里"pre-activated conda env"对 R2E 不成立（全局问题，见 decisions E09）；`run_tests.sh` / `install.sh` 在工作区可见（来源镜像自带，只泄漏隐藏测试目录名与命令） | 人工（读 facts.source + 探针 RUN_TESTS_SH_HEAD / GIT_STATUS） |
| R04 | 4 | 合法修改范围 | hygiene `test_files` = 隐藏测试文件 + `run_tests.sh`；gold 触碰的路径（`rh2_runs[].gold_included_paths`）不在其中；若解题需要改 `r2e_tests` 以外的测试辅助文件，记录 | 人工 |
| R05 | 6 | 依赖与工具链 | 探针：`python` 解析到 `/testbed/.venv/bin/python`、版本；pytest 可用；`pip check` 结果或"无 pip"；导入方式（editable finder / 路径项 / 仅 cwd）；gcc / make 有无 | 探针 + 人工解读 |
| R06 | 7 | 资产 / fixture | 期望中每个 FAILED / ERROR 键在 gold 日志里的原因行（`non_passed_reasons`）分类：上游本就失败 / 缺可选依赖或 fixture / 需网络或外部服务 / 资源 / 顺序 / 不明；`?? datasets` 之类未跟踪资产目录 | 人工 |
| R07 | 8 | 真实身份下可用 | 派生镜像 facts：agent uid 解释器可执行、私有目录不可读；探针：`chown` 后 `/testbed`、site-packages、home、`/tmp` 可写，`/usr/local` 不可写 | 自动（derived_image）+ 探针 |
| R08 | 9 | 候选代码生效 | gold 后 `RH2_OBS_IMPORT_PATH` 在 `/testbed` 且 gold 达到来源定义（reward 1）；gold=0 的题需归因（材料 / 资源），不能只凭导入路径 | 自动 + 人工 |
| R09 | 10 | 本地开发验证 | 探针：仓库自带公开测试文件可收集、可运行（rc、尾行）；公开复现脚本在 base 上展示题面所述行为（`REPRO_RC` + 输出）；收集失败要区分 conftest / 插件 / 依赖原因 | 探针 + 人工 |
| R10 | 11 | 网络需求 | 探针 `NET_CONNECT_RC≠0`（无出网）；R06 分类里"需网络"的键；解题 / 测试是否需要下载 | 探针 + 人工 |
| R11 | 12 | 外部服务 | 期望 ERROR / FAILED 键是否因服务不可达；orange3 sql 测试 skip 属正常 | 人工 |
| R12 | 13 | 资源 | gold 峰值内存 / 4 GiB 限额（> 60% 记 issue——**只是提示**：`memory.peak` 含 `chown -R` 产生的可回收页缓存，orange3 实测 2 GiB 限额下仍通过，见 decisions E12）；`/tmp` 1 GiB tmpfs（numpy `2f4a9650` 需 6 GiB）；setup（含 chown）与测试耗时；探针 `chown` 秒数 | 自动 + 探针 |
| R13 | 14 | 重复一致性 | 同资源 profile、同镜像 / 脚本 / 候选下 ≥ 2 次 RH2 运行（R-f + 中央复跑）reward 与差异集合逐条相同。两轮期限参数不同（R-f 候选 / 评分 1800 / 1800 s，中央复跑 900 / 3600 s），都完整结束，不影响结论，但不写成"所有运行参数相同" | 自动 |
| R14 | 15 | 重置 / 缓存 / 并发 | 每次 fresh 容器；`omitted_cache_count.baseline == post`（账本里是 {baseline, post} 计数对，pillow 镜像自带 `__pycache__` 时非 0 属正常）；探针前后 `git status` 行数不变；并发只记录（本轮 4 包并行，耗时不作校准） | 自动 + 人工 |
| R15 | 19 | 参考解析一致 | 对账 `agree`（reward、三个差异集合、观测映射逐键相同）；不一致写原因 | 自动 |
| R16 | 20 | 分差来源 | noop mismatched − gold mismatched = 目标键，且与题面描述的行为对应；gold 仍不符的键单列 | 自动 + 人工 |
| R17 | 29 | 泄漏 | 派生镜像：git 清理、私有目录 700；探针：HEAD 无子提交、无 remote、reflog 0、无 `*.orig/*.rej/*.patch/*.diff` 残留；`?? install.sh` 内容是否含修复 | 探针 + 人工 |
| R18 | 37 | 修复改的是环境还是题目 | 任何配方 / 提案标类别：资源 / 解题侧条件 / 材料修订（expected、隐藏测试、gold）；材料修订只提案 | 人工 |
| R19 | 38 | 可复验 | 每条结论有命令 + 证据路径；复跑账本 run_id 可查 | 人工 |
| R20 | 39 | 共享修复范围 | 配方适用的仓库 / 版本 / 题号；同仓不同版本不自动继承 | 人工 |

## 2. 探针字段与检查项的对应

`dev_probe.json.derived` 的十项最小条件（`min_dev_conditions_ok`）：`interpreter_isolated_ok`、`python_resolves_to_venv`、`pytest_ok`、`import_from_testbed_ok`、`import_from_testbed_path_in_testbed`、`writable_testbed`、`hidden_tests_denied`、`git_head_has_no_children`、`network_blocked`、`probe_completed` → R05 / R07 / R17 / R10 的机械部分。其余字段（`import_from_tmp_ok`、`pip_ok`、`pip_check_ok`、`writable_site_packages`、`public_collect_ok`、`public_run_rc`、`repro_rc`、`stray_patch_files`、`git_status_count_before_after`）供人工解读。原始 KEY=VALUE 在 `agent.values`，多行块在 `agent.blocks`。

## 3. `screening_record.json` 形状（每题一份，sub-agent 填）

```json
{
  "schema_id": "rh2.r2e_screening_record.v1",
  "task_id": "r2e_gym_subset::<instance_id>",
  "instance_id": "<instance_id>",
  "task_revision": "r2e_gym_subset_e8b9fcbc/expected_v0",
  "source_adapter_ref": "s2_r2e ingest_manifest_v0 (pin ea567fec…)",
  "recipe_ref": {"derived_image": "r2e_derive_v1", "resources": "default | task_resources_v1:<iid>"},
  "code_snapshot_ref": "runs/r2e_snapshot_20260923.sha256 (388 files) + r2e_env_tools.sha256",
  "facts_ref": "tasks/<iid>/facts.json",
  "dev_probe_ref": "runs/r2e_env_repair_20260924/<pkg>/dev_probe/<iid>/dev_probe.json",
  "checks": {
    "R01": {"status": "pass", "evidence_refs": ["…"], "by": "collate_facts.py"},
    "R06": {"status": "issue", "note": "…", "evidence_refs": ["runs/r2e_rf_20260923/remote/eval_logs_r2e/…"], "by": "<agent>"}
  },
  "issues": [
    {"category": "resource | material | solver_condition | reference | unknown", "scope": "task | repo:<name> | global",
     "summary": "…", "evidence_refs": ["…"], "proposed_action": "…", "status": "open | proposed | verified"}
  ],
  "solver_conditions": {
    "cwd_required": "/testbed", "interpreter": "/testbed/.venv/bin/python (PATH first)", "pip": "absent | present",
    "network": "none", "public_tests": "<file> collect ok / run rc", "notes": "…"
  },
  "classification": "env_ok | resource | material | solver_condition | unknown",
  "revision_refs": ["material_revisions/<iid>.md", "recipes/task_resources_v1.json#<iid>"],
  "disposition": {"state": "environment_qualified | qualified_with_recipe | held_material | needs_decision | unknown",
                  "scope": "…", "reason": "…", "evidence_refs": ["…"], "reviewer": null},
  "costs": {"probe_seconds": 0, "rerun_attempts": 0, "rerun_seconds": 0}
}
```

`disposition.state` 语义（2026-09-24 按 Codex R1 更正；"已归因"不等于"已解决"）：

| 状态 | 含义 |
| --- | --- |
| `environment_qualified` | R01/R02/R08/R13/R15 pass、探针十项最小条件满足，且**没有未完成项**：没有阻断相关开发验证的环境故障、没有待决定的支撑缺口 |
| `qualified_with_recipe` | 同上，但依赖逐题配方（如 numpy `2f4a9650` 的资源配方） |
| `qualified_with_revision` | 同上，但依赖用户批准的材料修订（修订单编号记在评分面 `material_revisions`），修订后的真实评分已验证 |
| `grading_ok_open_items` | 来源评分可复现（重复一致、与参考逐键一致），但有未完成项，逐条列在 `disposition.open_items`：`dev_blocking`（相关开发验证被环境故障阻断）、`support_pending_decision`（隐藏测试支撑缺口待 T0 决定）、`statement_conflict`（题面与目标测试矛盾）、`expected_penalizes_better_fix`（期望键会惩罚更完整的修复）、`grading_keys_unexplained`（期望里有键在 gold 与 noop 下都失败、原因未定位，用户已决定暂不改材料；09-24 夜加） |
| `held_material` | 材料问题导致 gold≠1 或期望不可信，等待材料修订决定 |
| `needs_decision` | 需要用户决定的项已写成提案（题面冲突、期望惩罚更好的修复、搬迁伪影） |
| `unknown` | 证据不足 |

"相关开发验证被阻断"只看与本题修复对应的公开测试或复现：业务 bug 在 base 上失败是正常信号；`python -m pytest`、正确工作目录、没有 pip 是使用条件，不算阻断；公开测试里与本题修复无关的用例失败记为解题侧噪声（需要写明相关性核对的依据）。十项最小条件不含"相关公开测试可以收集和运行"，所以它通过不等于完整开发环境验收。这些都是环境资格，不是题目质量或训练准入。

**2026-09-24 晚补充**：①处置只是环境侧状态，**不等于入池**——在题意与评分质量静态筛查、基座探针和后续可能的修复之前，没有筛选好的环境池（用户 09-24 晚）。②`disposition.open_items` 的条目可带 `deferred_to`（例：`题意与评分质量筛查`）与 `decided_by`，表示用户已决定把这项留给后续阶段；这类题仍记 `grading_ok_open_items`，不回到 `needs_decision`。③带材料修订的题（`qualified_with_revision`）如果修订了隐藏测试，就没有同版本的独立 runner 参考；R15 改用一次性容器试跑作对照，前提是试跑对原材料能由 gold 日志逐字重现来源期望原文。
