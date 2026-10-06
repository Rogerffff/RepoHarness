## 总结

**三题修订草案均通过，可落正式修订单；这不等于正式评分验收或探针准入已通过。**

本次未修改文件、未启动容器。已独立重算 **33 份试跑结果**的逐键比较，核对父文件、修订后文件和候选补丁摘要。结果一致，无 missing／unexpected；没有删除原 expected 键或修改原期望状态。

## 1. `aiohttp__1c1c0ea3`：通过

1. **R-c 用对，第 2 步确实命中。** 原隐藏测试只有 [909 行起的目标测试](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/private/aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52/hidden_tests/test_1.py:909)断言“不报告”，输入形态与题面示例相同。新增服务器启动失败的 `OSError` 是窄的非示例实例：[题面第 26 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52/user_prompt.txt:26)没有限定异常类型；[公开旧测试第 664 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52/worktree/tests/test_run_app.py:664)确认服务器启动失败应向调用者抛出。

2. **试跑支持修订。** gold、C1 均为 57/57；noop=0；F1 从旧版 1 变为新版 0，仅新增键失败；C5 仍为 0，失败的七个 shutdown 键未变。注入异常的文本用于识别测试输入，不是抄 gold 输出。

3. **C3 维持 S2 合理，但仍是错误候选。** 已证实的问题是中断后取消主任务时，cleanup **另行产生**的异常被吞掉；不是已抛出的启动异常重复报告。这与 [v1 §10 的明确分级](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md:262)一致。本次没有新证据要求升级。其新版仍为 1，应保留缺口登记和诊断，不能称作合理正对照或“所有错误候选均已拦住”。

4. **结论：通过，可落正式修订单。** 未扩大需求、未放宽原断言、未改题面。

## 2. `aiohttp__22a12cc2`：通过

1. **R-e 加请求级 R-c 实例成立。** “请求值覆盖连接器默认值”明确写在 [公开文档第 536 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/aiohttp__22a12cc2e2ef289d9e96fd87dfc17272177e52ac/worktree/docs/client_advanced.rst:536)；`ssl=Fingerprint(...)` 的请求级用法和 SHA256 定义见 [第 2006 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/aiohttp__22a12cc2e2ef289d9e96fd87dfc17272177e52ac/worktree/docs/client_reference.rst:2006)。四种正反组合没有新增无依据要求。

2. **没有把 gold 的内部实现写进测试。** 指纹经公开参数配置，未替换 `_get_fingerprint` 或 `Fingerprint.check`；摘要由证书替身字节独立计算。真实校验逻辑见 [client_reqrep.py:139](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/aiohttp__22a12cc2e2ef289d9e96fd87dfc17272177e52ac/worktree/aiohttp/client_reqrep.py:139)。测试不绑定校验位置、`close/abort`、cleanup 登记或异常地址。准确说，这是**网络替身下的真实校验行为测试**，不是完整 TLS 握手测试；入口仍保留原有 `_create_connection()` 范围。

3. **试跑支持纠正两类误判。** gold=1（21/21），noop、K3、K4=0；K2、RC 从旧版 0 变为 1，K1、IC 也为 1。K2 的选择逻辑与公开代码等价；RC 的合理性还有既有真实握手对照支撑，不是仅因新测试通过才认定。其余 17 个回归测试未改。

4. **结论：通过，可落正式修订单。** 没有保 gold 式放宽或新增泄漏。原题面非法指纹示例、漏写代理触发条件的问题仍未修，本次通过不核销这些旧问题。

## 3. `aiohttp__61833518`：通过

1. **R-c 范围合适。** 两个新测试都针对同一窄问题：deflate 配合 chunked 写出器提前结束响应。[题面第 24 行](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2/user_prompt.txt:24)直接要求完整传输；[web_reqrep.py:554](/Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_static_prep_20260924/v3/public/aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2/worktree/aiohttp/web_reqrep.py:554)确认该配置是实际服务端路径。未扩到 gzip、HTTP/1.0 或无过滤器空写入。

2. **AP1m 是有效的已知错误候选。** 合并三次写入本身合理，但它仍发送零长度数据块，因此线上字节仍提前表示 EOF。它不是因写入次数不同而被拒：[试跑堆栈](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2/trials/rev_AP1m.json:65)明确显示 `all(chunks)` 已通过，失败在 **`data after the terminating chunk`**。所以新测试确实检查了提前 EOF，不只是空写入。

3. **试跑验收方向成立。** gold=1（49/49），noop=0；AP1、AP1m 都从旧版 1 变为 0；AP2、A1 仍为 1。新断言检查分帧和解压后的原载荷，不要求压缩字节或写入布局等于 gold；原 47 个测试未改。

4. **结论：通过，可落正式修订单。** 无需调整测试内容。正式评分矩阵应包含 AP1m，不能只复跑 AP1。

## 正式评分仍需确认

- 在正式修订单、派生材料和评分身份下复跑验收矩阵，核验隐藏测试树及入口摘要；试跑不能替代这一步。
- `1c1c0ea3` 的 F1、C5，以及 `22a12cc2` 的 noop、K3、K4，**当前可确认失败键，具体断言原因仍属源码推断**。正式评分须保存完整堆栈，尤其不能仅凭 C5 的失败键把原因认定为取消顺序或环境抖动。
- 这些日志缺口不阻断草案定稿，但正式验收完成前，应保留“待正式评分确认”，不能标记为已可进探针。