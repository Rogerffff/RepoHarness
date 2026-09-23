# getmoto__moto-5752：历史差异核对

无历史稿已由协调者封存，SHA256 `d182af74107404043237c671788b7fedca59d399bac426d8901aca39cf140ff4`，未回写。门禁开放后仅读本题 `I2/history/getmoto__moto-5752/refs.json` 所指 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_moto_2/records/getmoto__moto-5752.json`，以及其中本题 mat 和 stage1 原件；未读 repo_level_findings、跨题结论或聚合。下文路径相对权威 ROOT；PUB/PRI/RUN 缩写同初稿。

| 旧主张 | 本轮结论与决定性证据 |
| --- | --- |
| tag 过早 return True 导致顺序错误，gold 完成题面目标 | **确认。** M:1608–1613、gold、公开 MWE 与当前 baseline no-op 失败位置一致；stage1 empty 原日志:913–932同样在反序 Equals 得2而非1，gold:996为80 passed。不是安装失败冒充目标失败。 |
| BeginsWith 完全没有公开依据，窄修法必然证明“不公” | **保留范围疑点，收窄旧定性。** 题面只有 Equals 顺序例，新增单标签 w/world 确实修另一个旧缺陷；但公开校验器 M:1462–1468 明确允许标签 BeginsWith，旧普通字段测试也解释前缀含义。窄修法可作为自然部分实现，其是否满足本 issue 全部合理要求尚待裁定；不能仅据题面未逐字出现就宣布合法解误拒。此点未改变初稿。 |
| hints 给出的写法可直接做合法候选，BeginsWith 两条都会失败 | **更正。** 精确原件 `runs/env_overnight_20260916/L1_moto_2/mat/getmoto__moto-5752/hints.txt` 的片段写成 `parameter.tag`，实际字段是 `parameter.tags`；它是未验证讨论片段，不应原样当可运行补丁。修正字段并采用其控制流后，w/world 前缀断言预计失败；a/a 与 Equals 等价，单独执行反而可过。四断言同一函数，首个失败还会阻止后续执行。唯一优先实验仍使用初稿的独立窄实现，只确认范围差异，不预先称合法完整解。 |
| gold 的 tag Contains 列表分支保留了可达残余缺陷，AWS 应匹配子串 | **推翻当前调用路径上的缺陷结论。** `describe_parameters` 在匹配前调用校验器；M:1462–1468仅为 Name 放行 Contains，tag:hello/Contains 会抛 InvalidFilterOption，根本不会进入被指控的列表分支。公开 by_path 同样先校验。旧拟议反例不能产生其预测的“返回0”。实际 AWS 行为本轮没有实测；旧断言亦无精确 AWS 原件，不外推。 |
| Description 删除8处，材料错配/评分缺陷 | **计数更正并降为无关清理。** 精确 test.patch 是7处 put_parameter；旧断言不变，by_path response_object 不输出 Description。它仍是 P2P fixture 变动，完整记录但没有造成已知错配或不公的证据，不据非最小化直接记检查1失败。 |
| 15个截断参考ID不稳定 | **确认当前绑定、收窄风险。** 旧 status_map 与当前 parser 都在空格处截断；14个 filter 参数 case 仍以 filters0–13区分，另一个为 datatype[something。当前固定 parser/expected 组合解析80项、无missing/skip。假想更换 parser 后的风险不等于当前身份错误，不改 oracle 或 reference。 |
| 79个P2P覆盖较好，没有充分说明具体阅读 | **明确边界。** 本轮逐体读到33/79引用对应18个旧函数，含全部 describe 及共用 get_parameters_by_path；其余46只核日志/引用。已读函数详初稿§2，不把整个选中文件称全部人工审过；旧建议扩展回归未执行。 |
| 与5502/5835同文件所以应成组 | **未核实关系。** 本轮未打开这两题及 repo_level 汇总。同文件与共用P2P不自动证明同一修复、答案重叠或留出污染，不形成分组决定。 |
| hints 不对 agent 可见，泄漏因此已排除 | **仅静态字段确认，运行未知。** 历史 public.json 的 public_hints 是通用操作说明，未嵌入上述原始 hints；当前公开稿同样未见该修复片段。实际模型消息、Git/挂载/缓存未验，不能宣称泄漏已排除。特权审查已读该片段，暴露仅限审查。 |

历史原件补证：`runs/env_overnight_20260916/L1_moto_2/mat/getmoto__moto-5752/{test.patch,gold.patch}` 与当前 PRI 字节一致，SHA分别 `e978cfc7231752056767cc3192ed5a67be3e630ae0ab3b32a4c2f6d071e397f8`、`94e23bedb77a52fbef589882aec31531129cab051d1d6b49d1a28adcb9986a64`。其 _lines.json 指向本题 public/grading/validation 第73行；无需跨题搜索。

`runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/getmoto__moto-5752/gold/offline/a1/eval.sh` 明示 make init、checkout base 的唯一测试路径、注入官方补丁、运行80项。gold test_output:864–876实际 editable install成功、install rc0；:880–888官方恢复与注入成功；:893–900收集80项；:996–1000全部通过且test rc0。empty:826–829 install rc0，:1026–1031目标1 failed、79 passed、test rc1。日志含root pip警告，这些旧证据不证明当前正式非root actor；当前baseline的rh2grader/54322证据仍按初稿单独陈述。旧 raw hints 并非实验轨迹，旧22分钟不作为本轮cost。

最终仍 `needs_review / static_review`、`development_diagnostic`：公开契约是否包含额外 tag 前缀修复待独立裁定，实际 actor 待验。未改任务、测试、gold、配方、奖励或封存稿；不新增排除，不新增第二个反例计划。
