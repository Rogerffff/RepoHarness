# 格子级审查协议（基座探针 2026-09-22 第二轮分析）

本协议是 `REVIEW_PROTOCOL.md` 的批量变体：**一个 agent 审一个"题目 × solver"格子里的全部尝试**（2–4 条），产出一份格子报告。先完整读 `REVIEW_PROTOCOL.md`（材料布局、只读纪律、两阶段顺序、归因标签），再按本文执行。只读分析；除报告外不改任何文件；不运行容器、不联网、不 ssh。工作目录是仓库根。

## 材料位置补充
- 派发消息给出 TASK、SOLVER、要审的 ATTEMPT 列表、题卡目录。attempt 目录 `runs/base_probe_20260922/remote/runs/matrix/attempts/<TASK>/<SOLVER>/<ATTEMPT>/`。
- 网关目录按 solver：`deepseek-v4-pro` → `gateway/deepseek/`；`qwen3-coder-30b-a3b-instruct` → `gateway/coder/` + adapter 逐轮记录 `gateway/coder_adapter/<attempt_id>.turns.jsonl`；`qwen3.6-35b-a3b` → `gateway/q36/` + `gateway/q36_adapter/`。attempt_id 在 attempt.json 里。
- 同题已有报告在 `runs/base_probe_20260922/analysis/<TASK>/`（第二阶段可读，不要改）。
- **盲审纪律（W2 起收紧，按 Codex 09-22 复核 §9.2.6）**：阶段一只允许读运行记录 `docs/.../base_model_probe_run_20260922.md` 的 §2、§3、§6（入口、固定条件、开工前接缝），**不读 §7–§8**（含分数、gold 结论与逐题判断）；派发消息里若带 reward，阶段一当作未知。路径里含模型名无法避免，报告里注明"非严格盲审"。阶段二再读 §7–§9 与同题报告。
- a3 / a4 与扩量题的尝试 `harness_out=out_of_tree`（CC 轨迹不在仓库树内）；a1 / a2 前三题为 `in_tree`。

## 顺序
1. **阶段一（盲审）对格子里每条尝试逐条做**，全部做完并写入报告后，才进入阶段二。阶段一问题同 `REVIEW_PROTOCOL.md`，自部署 solver 加答第 8 问。
2. **阶段二（核对）**：打开评分材料、gold、测试补丁、题卡、同题既有报告。除逐条核对外，回答格子级问题：
   - 各次成功的补丁是否实质相同（语义，不是字节）；是否都与 gold 同义；有没有"官方通过但与公开需求不符"的候选（疑似假阳性，给具体输入与预期 / 实际）；
   - 各次失败是否同一原因；是能力、工具、环境 / 接口、预算还是题目 / 测试问题；
   - 这个格子对 RL 的含义一句话（有无区分度；若全 1 或全 0，奖励能否区分补丁质量）。

## 输出
写到 `runs/base_probe_20260922/analysis/<TASK>/<SOLVER>/cell.md`。结构：
1. 格子结论（≤6 行）；
2. 每条尝试一节（各 ≤ 500 字）：阶段一要点、阶段二要点、归因；
3. 格子级核对（上面三问）；
4. 证据指针表；
5. **JSON 代码块**：`{"cell": {"task": "...", "solver": "...", "attempts_reviewed": [...], "successes_equivalent_to_gold": n, "suspected_false_positive": [...], "failure_causes": {...}, "rl_signal": "...", "confidence": "high|medium|low"}, "attempts": [ 每条一个对象 ]}`。
   每条对象字段固定为：`attempt_id, attempt, reward, process_quality, repro_before_fix(bool), verification_run(bool), answer_channel_probe(bool), answer_channel_kinds(list of "git_future"|"pip_download_project"|"web"|"site_packages_newer"|"harness_trajectory"|"other"；**读本题旧实现、安装普通依赖不算**), answer_channel_obtained(bool), read_harness_dir(bool), scratch_files_in_candidate(int), official_tests_modified(bool，按 projection.ignored_paths 判), test_edit_kind(list of "added_reasonable_tests"|"changed_existing_expectations"|"control_surface"|"none"), non_core_tools(dict name→count), is_error_breakdown({"expected_test_failure_nonzero": n, "other_cmd_nonzero": n, "call_error": n, "other": n}；**预期的测试失败非零退出不是协议错误**), hit_turn_cap(bool), truncation_causal(bool|"unknown"), im_end_leak(bool|null，自部署才填), cc_param_rewrites(int|null，自部署：对照 adapter raw 与网关回传历史), thinking_cleared_events(int|null，仅 qwen3.6), max_prompt_tokens(int|null，自部署取 adapter turns), labels(list), confidence, followups(list)`。
   这个 JSON 会被脚本聚合，字段名和类型不要改；不确定填 null 并在正文说明。

纪律：每个结论指向可核对的证据（文件 + 行号或事件序号）；推断标明是推断；不确定写未知。最终回复 ≤ 10 行复述格子结论，并附同一 JSON。
