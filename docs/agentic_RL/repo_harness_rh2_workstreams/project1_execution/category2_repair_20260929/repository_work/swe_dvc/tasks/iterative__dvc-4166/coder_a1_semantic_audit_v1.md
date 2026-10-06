# DVC4166：Coder 首臂题主语义审计

2026-10-03。作业 `gpu1003-dvc4166-coder-a1`，请求 `swe-dvc4166-behavior-r14-v1-20261003`，预算 `probe-wide-v1`。本报告封存题主对原候选、完整工具序列和业务证据的判断；独立复核另存，双模型请求尚未核销。

**这是有效的模型错修：正式评分 0，3 个 F2P 均失败，60 个 P2P 均通过。候选拆分 regex 分组，却没有修复尾斜杠规则需要区分文件与目录的问题。** 没有观察到导致本次 0 的安装、评分或模型服务故障。公开测试通过与最终成功声明不能覆盖目标目录遍历行为。

## 原件与候选

[逐件读回和工具时间线](coder_a1_owner_evidence_readback_v1.json) SHA `646c856009b73ed3c344beb4e594b684fa44ea94d0757cb70b7b950b7e0f5bb8`：封存清单 653 件、49,105,412 字节逐件核对；另有清单及同步回执两件元数据。原 baseline tar 的 430 条目按类型、执行位、内容匹配。1055 行 CC 轨迹、89 个工具输入／结果、模型陈述及 90 轮传输记录已审阅；重复的测试头和警告按结果核对，不把自动字节检查单独当成语义审阅。

baseline canonical SHA `16f108c365097d36390d40ff2b06c47fcf186b13c0e4cae2381ebfe6048ab6db`；FrozenPatch canonical SHA `1f21d4efd80771070e0fb6135e9b48c736ff2b587218c3c5b2c4543a850076d7`。严格解码后业务修改仅 `dvc/ignore.py`，另新增 22 个根目录调试脚本，共 23 项。正式 projection 包含原 23 项，没有题主删文件或重评分。hygiene clean 表示当时路径／测试约束通过，不能解释为只有业务文件。终局 `git diff` 显示的 `setup.py` Moto 版本变化已存在于实际 baseline，不归为模型修改；模型最后一次试图撤销它的 Edit 为无变化错误。

### 1. 根因、修法与公开边界

原实现 `groupby` 按连续同类规则分组，保持输入顺序；`ignore()` 逐组匹配并更新结果，本来就是最后匹配规则决定结果。最终候选将 `map` 转 list、每条 regex 单独编译，没有修改 `matches()`、`__call__()` 或目录类型／尾斜杠表示。同类连续 regex 的合并与逐条匹配在这里不会改变最终布尔结果。不存在模型所称“原分组打乱顺序”的依据。

`/*` 与 `!/scripts/` 的真实目录遍历中，父目录名以 `scripts` 进入匹配，否定 regex `^scripts/.*$` 不匹配无斜杠的目录名，目录仍被剪枝；单独匹配 `scripts/helper.py` 不能证明父目录已重新进入遍历。正向目录规则也需要区分目录和同名普通文件。候选未改这些路径，实际三个目标断言失败与源码一致。公开语义不要求所有 issue 写法等效，也不允许绕过被忽略父目录自动恢复子文件。

正式 66 个节点为 63 参考加 3 个未计分节点：原 `test_ignore_file_in_parent_path[data_struct2-pattern_list2-result_set2]`、新增目录剪枝及否定目录恢复三项失败；60 个 P 和三项额外节点通过，无缺失、skip 或无法归属节点。新增“同名普通文件不被目录规则误忽略”的 P 通过，不能据此抵消目录 F。eval SHA `721576fcad7b1f19e0c2b4d9a6231913276d9e3b4d5e4b1162989d0f39b69ed5`。当前无证据要求修改题目或断言以迁就此候选。

### 2. 定位与纠偏

第 6 个工具约 2.939–3.264 秒已搜索到目标 ignore 实现，随后阅读实现及公开单元／功能测试。但模型没有建立正确的目录遍历根因。多次 mock 设置 `.read.return_value`，实际实现调用 `.readlines()`，得到空规则；模型直到较后阶段才识别这个调试错误，又在后续脚本中重复出现。

第 54 个工具约 148.800–151.801 秒将规则按 ignore flag 排序，真实文件脚本的片面结果使模型误判成功；第 65 个工具完整单元模块出现 2 fail／13 pass。第 66 个工具约 196.733–200.601 秒撤销排序，纠正了自己引入的顺序回归。第 83 个工具约 270.314–274.509 秒才改为最终逐条匹配。纠偏恢复了原有顺序，却未解决目录语义。时间是请求／响应边界，不是精确内部推理计时。

### 3. 工具使用

89 次调用为 Read 12、Bash 45、Write 22、Edit 10。7 次工具错误分别包含目录 Read、错误 mock 上下文、缺少嵌套目录、两次空／陈旧字符串 Edit、排序后公开测试失败，以及终局空 Edit。安装与解释器可用。

前半程大量脚本围绕空 ignore_spec 调试；手工 regex 模拟与实际 DVC 使用不同 mock，输出互相矛盾，未先验证规则确实加载。后半程真实 WorkingTree 脚本仍主要把含斜杠子文件作为平面文件列表传入、目录列表为空，因此回避了目标父目录剪枝。连续创建近似脚本增加调用与候选残留，提供的信息少于一次真实目录遍历复现。

### 4. 实际并行机会

90 次 API 每轮至多一个工具，没有观察到工具并发或有效后台重叠。实现、公开单元与功能测试的初始读取可批量进行；纯 regex 示例可以合成一次脚本。Edit、针对改变的回归与回滚有明确依赖，真实 DVC 测试可能共用工作区／缓存，不能一概并发。主要效率问题是调试路径失真和重复，不能靠增加并行数量解决。

### 5. 自测与最终陈述

原公开单元 15 项和功能 14 项在基线及最终候选均通过；中间排序导致的两个单元失败已撤销。不能把重复运行的 29 项相加成更多独立覆盖。根目录脚本多数打印比较而没有断言；错误 mock 的全 False 以及平面子文件匹配不能构成真实目录遍历回归检测。未加入既有测试目录的有效目标回归测试。

最终“分组改为逐条处理确保最后匹配规则生效”的因果陈述不成立：原代码已经保序。关于 issue 是用户预期问题的判断来自平面匹配，不能推翻原有失败节点及新目录行为断言。正式 0 与候选源码一致，这是可用于分析定位、调试与自测习惯的负信号；不是材料失败或服务噪声。

### 6. 效率、服务身份与资源

solve 293.626 秒；CC duration 289.825 秒、API duration 251.907 秒；gateway response 加总 249.721 秒，首请求到最后响应 289.748 秒。累计输入 3,046,377、输出 28,003 token，单次最大输入 59,828、输出 1,416。累计输入含重复上下文，不表示上下文越界。CC cost metadata 15.93196 美元是估算，非实付账单。

90 次请求均实际 `max_tokens=65536`、HTTP 200、attempt 1，SSE 完整，无 stream error、输出长度终止或观察到的压缩／恢复。`maxOutputTokens=32000` metadata 不代替实际请求。预算为 context 196608、240 turns、10800 秒、1024 requests，未观察耗尽。

作业前 09:57:11 UTC 有实时 engine／adapter inspect、只读 model mount、argv 和 HTTP 配置读回，绑定 Coder revision `b2cff646eb4bb1d68355c01b18ae02e7cf42d120`、BF16、TP1、context 196608、max-running 1。补充读回 `runs/category2_repair_20260929/repository_work/swe_dvc/q27_three_coder_operational_owner_readback_v1.json` SHA `84fb2d8871578ca1e2559251110fc0b6aaaa1ce0201bb3e71fab824786513d29` 校验 capture 内全部指针、实际配置及 25 个模型文件大小，其中 16 个 safetensors 分片。没有重复逐权重 SHA 或 GPU 内存权重证明。原 input 的 config-only 字段保持原件，实时 capture 为独立证据。

正式 grading total 277.491 秒、reset 14.128、prep 1.580、report test 7.405；candidate install 3.132、candidate test 3.675、pytest 正文 1.16 秒各有不同计时范围。trusted setup 汇总 252.203 秒，不将整段命名为纯 chown，也不归为模型思考。报告峰值 1109.395 MiB；43 个有限采样覆盖多类容器，未在本报告推导全程峰值或最低配置，diagnostic resource_facts null 保留。

### 7. 结束原因与当前用途

CC success／exit 0、end_turn、completed，解题日志完整；gateway revoke／drain 后 active_requests 0。actor／relay／网络 cleanup true；grader manager 清理闭合。实际镜像 `28ed5ef69d46c326ec183f8719e426611ca848046156fa98f9f6c7f35b46ebeb`、基线 HEAD `520e01f11305aba1994df354adef86e6d90180de`。UID54322 prerequisite verified／exit 0，candidate install 0／test 1，runner 未改；env qualification 未单独执行。没有 infra failure，实际测试失败决定 reward 0。

本次保留原候选与 0，待独立审计封存；Qwen 首臂待返回，成对请求继续 claimed／active，不 ACK、不填 returned、不清 active_request_id。当前覆盖优先，不自动发起普通重复，不因有效模型失败改材料。稳定性、双模型差异、训练或留出用途仍待后续证据及决定。
