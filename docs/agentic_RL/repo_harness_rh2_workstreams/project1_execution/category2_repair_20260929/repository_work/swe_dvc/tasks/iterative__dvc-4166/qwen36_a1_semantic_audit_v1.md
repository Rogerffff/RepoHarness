# DVC4166：Qwen 首臂题主语义审计

2026-10-04 SGT。作业 `gpu1003-dvc4166-qwen36-a1`，固定请求 `swe-dvc4166-behavior-r14-v1-20261003`，宽松单次预算 `probe-wide-v1`。本报告只分析原首臂，不执行新候选、评分或模型。独立语义报告和请求核收另存。

**这是部分定位正确、最终修复不完整的有效 0：3 个 F2P 中仅否定目录恢复通过，正向目录剪枝与原父目录场景仍失败；60 个 P2P 全通过。** 没有观察到造成此次 0 的安装、模型服务或评分故障。模型自己的 37 项通过来自公开 29 项加自增 8 项，不能代替正式目标行为。

## 原件与候选

[逐件原件及完整工具读回](qwen36_a1_owner_evidence_readback_v1.json) SHA `0b8e3c699a133c2d19d0f6e9dc8cd4084e40ec1cc694335c6be932fabc28f8d6`：435 件、41,970,853 字节逐件核 SHA／size；baseline tar 430 条目核类型、执行位和内容。1055 行 CC 轨迹、67 个工具输入／结果、全部模型陈述及 66 份 gateway／adapter 原件已核。重复源码按实际 Edit 和读回比对，测试警告不计为业务错误。

baseline canonical SHA `16f108c365097d36390d40ff2b06c47fcf186b13c0e4cae2381ebfe6048ab6db`；完整 FrozenPatch canonical SHA `90b6ce6e6b04ef062b40b34bc4192a91750ee98d8e2e719c8c47725475565867`。严格解码的两项为业务 `dvc/ignore.py` 与公开 `tests/unit/test_ignore.py`。**正式 scoring projection 仅包含业务文件，原测试修改已剔除。** report 的 `test_files_modified=false`／hygiene clean 是应用后投影的事实，不表示模型未改测试；原两项 FP 保持不变。本题没有新增根目录调试脚本。

## 1. 根因、修法与公开边界

模型正确发现 pathspec0.8.1 的目录 regex 如 `^scripts/.*$` 不匹配目录自身 `scripts`，会使显式否定目录仍遭剪枝。最终 helper 仅改 `ignore=False` 的 regex：尾部 `/.*$` 改为 `(?:$|/.*)$`，若简单前缀与 `/...` 分支匹配则增加裸前缀备选。它没有改 `matches()`／`__call__()` 的文件与目录区别，也明确保留全部正向 regex。

因此正式否定目录恢复 F 通过，但 `blocked/` 的正向规则仍不排除目录本身；原 `subdir/` 与 `!should_ignore` 场景进入本应剪掉的父目录，错误保留 `dir/subdir/should_ignore`。两份实际失败堆栈与源码一致。公开目标要求目录规则区别普通文件，不能把 issue 中七种写法强行等效或隐含子文件重入父目录；模型自己的例子统一期望六种写法恢复裸目录，不能自行成为正式规格。

66 个实际节点为 63 个参考与 3 个未计分原有节点：2 fail／64 pass；参考为 F1/3、P60/60，额外3全过，无缺失／skip／无法归属。eval SHA `65a95989e22595bc320fd3142b10ba5456c06d8deded730379aee152276282b3`。没有据此放宽材料或重采样的依据。

## 2. 定位与纠偏

首轮搜索就找到 ignore，第二次生成同时读取实现与公开单元。工具7在约16.558–18.781秒打印修前六种规则的实际匹配；工具8–10在约18.781–29.612秒定位裸目录不匹配。工具17约50.520–54.793秒首次 Edit；把编码写成 `utf=8` 后立即纠正，未观察该拼写成为后续运行故障。

初版没有区分正负规则。工具27生成错误转义regex，工具28出现 `nothing to repeat`；工具30更正转义后仍把 regex 元字符当路径前缀，工具31／36出现不闭合分组。模型用实际 pattern/groupby 输出定位错误，而未把临时空 group 的打印误归因到业务 groupby。工具41收紧简单前缀，工具46另处理隐式通配前缀。

工具48公开测试显露 `test_remove_ignored_file` 回归：正向 `dir/ignored` 被扩成匹配父目录。工具54–55约152.684–160.706秒加 ignore flag，使 helper 仅用于否定规则，工具56恢复29项通过。纠偏撤销了自己引入的正向误匹配，但也留下原正向目录规则缺陷。边界时间是 gateway 可观察请求区间，不是内部推理耗时。

## 3. 工具使用

67 次为 Bash46、Read12、Edit9。两次 `is_error` 为 regex 运行错误；另有 catch 后打印堆栈的工具36与被 `head` 管道掩盖退出状态的公开回归，不能将“仅2工具错误”理解为只有2次失败观察。末尾两次 Read 被返回“文件未变，重复调用”，随后又 cat 相同文件。

相比 Coder，本次 mock 使用既有公开 `mock_open` helper，规则确实被加载，没有 read/readlines 空规则问题。仍有较多相近 regex 模拟、反复源码读取与重复六例；模型一直验证 `matches()` 的平面路径，没有新增真实 WorkingTree／CleanTree 目录遍历复现。没有安装或解释器故障。

## 4. 可观察并行行为

前两份 gateway SSE 各含两个 tool_use：搜索＋目录列举，源码＋单元读取；不是全程单工具串行。两个结果都在下一生成前返回，第一组结果还逆序到达。原件未提供工具开始／结束跨度，不能证明物理执行重叠多少或节省多少时间。其余64个生成至多一个工具；总计66生成／67工具，CC自身 `num_turns=68` 按原字段保留，不强行与请求数相等。

独立初始检索／阅读可成组；regex小例可合成一次脚本。Edit→新规则复现→回归／纠正有依赖，同工作区DVC测试不应无条件并发。主要成本来自 regex 重复试错与缺失类型／遍历分析。

## 5. 自测与最终陈述

修前公开29项通过；中间回归被发现并修复；最终公开29项与新增8个 mock `matches()` 断言共37项通过。新增断言是真测试，但只核裸目录与两个其他名称，没有核目录和同名文件的区分、正向目录剪枝、父目录遍历或非示例目录。它们在正式投影中被剔除，不能计入正式66节点。

工具58错误要求 `dir/ignored` 忽略父目录，随后纠正；工具59把 root级 `ignored` 当作 dir内路径，工具60用正确 dirname复核。模型接受实际结果并修正自测预期，未以删断言掩盖该情况；打印比较仍不是统一失败断言。最终准确描述了“只改否定regex”和自己的37项，但“全部规则正常／完成修复”超出证据，因为两项正式目录行为仍失败。

## 6. 效率、身份与资源

solve201.240秒；CC duration197.657／API174.746秒；gateway响应加总173.172秒、首请求到最后响应197.591秒。累计输入2,082,248／输出27,645 token，单次最大53,374／1,939；累计输入含重复上下文。CC cost11.102365美元为估算metadata，非实付。66请求实际max_tokens65536、HTTP200、attempt1、SSE完整无stream error；未观察输出长度终止、压缩恢复或预算耗尽。context196608、240 turns、10800秒、1024请求护栏保持。

[题主实际双臂条件及实时捕获读回v2](../../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/dvc4166_6954_pair_operational_owner_readback_v2.json) SHA `1c3f40bb23366f78c918749738d9ff54f8897e13ca29323a87f3afc9f3709922`核同题公共prompt原字节、baseline／镜像／HEAD一致，实际sandbox profile只差模型proxy18081→18082。Qwen作业前16:01:08 UTC实时capture绑定engine／adapter／只读挂载／argv与HTTP，revision `995ad96eacd98c81ed38be0c5b274b04031597b0`、BF16／TP1／context196608／max-running1。列明37文件大小逐项一致、其中26权重分片；download声明40与列表37不一致，未重新逐权重SHA或GPU内存证明。

grading total267.749、reset13.227、prep0.229、report test6.841秒；candidate install2.887／test3.371秒，pytest正文0.98秒。trusted setup246.668秒有不同范围，不算模型思考或纯chown。35行有限资源采样中actor16／grader18／relay16，按各自run_id绑定；内核memory.peak采样最大分别1,091,866,624／1,173,024,768／27,836,416字节，已有样本OOM kill及PID limit事件均0。不能据采样推全生命周期无事件或最低配置。report峰值1118.684MiB、diagnostic resource_facts及baseline环境包digest的null保持。v1资源筛选把grader按actor run_id选得0样本，v2仅更正该筛选，旧文件保留。

## 7. 结束原因与当前用途

CC success／end_turn／completed／exit0；gateway revoke且active_requests0，actor／relay／网络及grader cleanup均true，manager创建／删除各1、无遗留／清理失败。UID54322 prerequisite0、install0／test1，runner摘要前后相同，env qualification未单独运行。已退役unit的默认0不作为退出证明；原completed记录与精确PID1成功journal共同支持正常退出。

当前保留原0和部分正确根因作为负信号，与Coder无效分组改写区别分析。CPU／公开actor与既有Coder独立审查按版本复用；新Qwen语义独立复核及题主成对核收另存，不在本文预先ACK。普通重复仍暂缓；单次双失败不等于稳定失败、题目无价值或训练资格。
