## aiohttp_240d：通过（可落正式修订单）

**草案通过，不等于正式评分验收完成。** 本次只读；未修改文件、未新跑容器。

### 1. 模板与公开依据

两项均正确使用 **R-c**，分别对应一个窄问题：

- **`test_request_port_other_url`**：题面第 9 行说的是一般的“带指定端口的 URL”，不是只修 `localhost:1234`；公开旧测试也已通过 `connect()` 检查绝对请求路径。换主机、端口和路径属于非示例实例，没有扩大需求。[题面原文](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/aiohttp__240da100151933883d7dea0528d45877df025b92/user_prompt.txt:9)、[公开旧测试](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/aiohttp__240da100151933883d7dea0528d45877df025b92/worktree/tests/test_connector.py:324)。
- **`test_https_connect_port`**：公开测试已要求 CONNECT 目标为 `host:port`；源码明确使用该格式，公开 `test_host_port` 也要求 `host` 不含端口。把默认端口实例换成显式端口，是保护已有行为，不是新增 HTTPS 功能要求。[CONNECT 测试](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/aiohttp__240da100151933883d7dea0528d45877df025b92/worktree/tests/test_connector.py:468)、[源码](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/aiohttp__240da100151933883d7dea0528d45877df025b92/worktree/aiohttp/connector.py:350)、[host/port 测试](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/aiohttp__240da100151933883d7dea0528d45877df025b92/worktree/tests/test_client.py:343)。

**第 2 项必做。** 收集日志确实在 `test_client.py:647` 报 SyntaxError，不能把 `test_host_port` 算作当前可执行保护。但必做的根本理由是：WR1 已正式得 1，却破坏公开行为，命中 v1 §4 第 4 步；即使公开测试能运行，也不能替代评分侧保护。“唯一保护”应限定为**当前验收集里拦截 WR1/WR2 的唯一键**。

### 2. 验收证据

我核对了补丁、父版本与修订后文件摘要，并从试跑日志重新提取状态，与 JSON 记录一致：

| 对照 | 修订版试跑结果 | 决定性结果 |
|---|---:|---|
| gold、AL1、SC1 | 1 | 35/35 键匹配 |
| noop | 0 | 原目标键及非示例键失败 |
| DG1 | 0 | 仅新增非示例键不匹配 |
| WR1、WR2 | 0 | 仅新增 CONNECT 键不匹配，实际得到重复端口 |

[验收清单及原件索引](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/aiohttp__240da100151933883d7dea0528d45877df025b92/revision_draft.json:66)。

- 原 33 键及期望完全保留，只新增两键；无 missing／unexpected。**35/35 指期望匹配，不是全部测试 PASSED**；原两个期望 FAILED 键仍在。
- 正对照使用 gold，无须替代正对照豁免；其修改与公开 `netloc` 语义一致。新期望来自公开需求和既有 CONNECT 行为，不是抄 gold 输出。
- 本轮相关 S1 反例均被纠正；WR3/WR4 等登记为 T3 的范围未实跑，不能宣称全部错误都已拦截。

**仍须正式确认**：同时落隐藏测试修订与 expected 两个新增键，重建材料／镜像，再跑同一七项矩阵，核对补丁投影、测试树摘要及严格键集。试跑的简化权限与完整性检查不能替代这一步。

### 3. 范围、泄漏与 X1

没有删断言、为保 gold 放宽要求、改题面或引入新的题测矛盾；R-a／R-b／R-e／R-f 均未使用。两个 FAILED 死键继续登记，当前证据不要求并入本轮 R-a。

**X1 的训练／留出影响已写清，但实际划分登记仍待落实**：训练控制同源重复采样；留出按仓库隔离，不能将 `61833518` 放训练、将本题放留出；另须满足未用于选模型／调参及版本标注条件。[用途说明](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/aiohttp__240da100151933883d7dea0528d45877df025b92/review.md:37)。

一处非阻塞文字校正：`61833518` 包含的是**同一修复核心行及原目标测试的后继版本**，整段并非逐字相同；不是本轮新增的两项测试。X1 确实成立，但不是本次修订造成的泄漏。

### 4. 结论

**通过，可落正式修订单；无需修改测试草案。** 正式评分完成前，不据此直接授予探针或训练资格。