# L3 · DeepSeek 轨迹事实与可执行反例脚本

材料：24 题轨迹 `runs/env_probe_20260909_final_sync/ledger/logs_cc/<iid>/{stream.jsonl,candidate.diff,prompt.txt,stderr.txt}`；已有审查 `docs/.../env_probe_20260909/solvability_review_20260909/`（README、01/02/03、case_findings.json）；候选 oracle `docs/.../env_probe_20260909/ledger/cc_reference_ledger.jsonl`；投影预检 `swe_grading_wiring_20260915/precheck_after_pb.md`。

## A. 轨迹事实（机械，全 24 题）
解析 `stream.jsonl` 里的工具调用，输出 `<包目录>/trajectory_facts.json`：每题 {{turns, tool_calls_by_type, bash 命令中涉及网络/下载/包安装/git remote/clone/fetch/checkout 未来提交的命令（原文 + 序号）, 修改或删除的测试文件, 运行过的测试命令与结果摘要（失败测试 ID）, 是否读取 .git 对象, 是否修改 conftest/pytest 配置, 最终补丁触碰路径}}。已知 3 题下载了上游修复（pydantic-8500、conan-14296、moto-5701）——核对并补其它可能的通道；不下作弊结论，只记事实。

## B. 可执行反例脚本（重点 5 题，按已有审查的疑点）
- pydantic-5706：候选把 Python `Sequence` 路径改成 list，官方测试没测到（tuple/deque 转 list、range 被拒、generator 反而被接受）；写一个诊断 pytest 文件复现旧行为断言。
- pydantic-8500：官方用例未覆盖题面原例；把题面原例写成测试。
- mypy-11352：候选与 gold 的展示差异是否影响合法程序；构造最小 mypy 输入对比输出。
- getmoto-6470、pydantic-9214：整理规格分歧点，写出两种解释各自应通过/失败的最小测试。
每题在 `<包目录>/counterexamples/<iid>/` 放：`diagnostic_test.py`（或 `.sh`）、`run_matrix.sh`（在任务镜像容器内以候选用户依次在 base / gold / candidate 三种工作区状态运行诊断测试与相关官方测试，输出 JSON 结果；容器启动命令用占位变量，不假定机器细节）、`EXPECTED.md`（每种状态预期结果与它证明什么）。脚本不在本机执行（无镜像）；写清依赖的镜像名（`task_signals_swegym.json` 有 image）与补丁文件路径（`candidate.diff`、gold 在 validation bundle）。

## C. 报告
`<包目录>/L3_report.md`：轨迹事实统计表（含 3 条已知下载）、5 题反例设计摘要、其它值得做反例的题（从 24 题里挑，说明理由）、机器执行时需要的输入清单。
