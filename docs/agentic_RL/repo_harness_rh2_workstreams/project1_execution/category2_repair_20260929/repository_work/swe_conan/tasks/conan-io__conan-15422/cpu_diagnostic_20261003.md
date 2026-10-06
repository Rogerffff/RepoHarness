# Conan 15422：v2私有矩阵已堵实际preset消费假阳性

2026-10-03，题主自查。当前v2已完成私有八方矩阵：有效正对照全部保留，Qwen3.6 a2在jobs2／7的实际CMake消费检查失败。旧40个P2P每方均通过；正式consumer／评分与非作者v2核查仍待，不授予训练资格。

v1曾在所有jobs字段检查通过该Qwen候选，真实CMake3.23.5却拒读。v1原件完整保留，发布者已获通知不能登记旧草案；本次修订只影响15422。

| 私有源码候选 | v2 F2P通过／5 | P2P通过／40 | 真实configure／build |
| --- | ---: | ---: | --- |
| noop | 0 | 40 | 0／0 |
| gold | 5 | 40 | 0／0 |
| Coder a1 | 4；默认jobs失败 | 40 | 0／0 |
| Coder a3 | 4；默认jobs失败 | 40 | 0／0 |
| DeepSeek a1 | 4；追加／替换失败 | 40 | 0／0 |
| DeepSeek a4 | 5 | 40 | 0／0 |
| Coder a2 | 5 | 40 | 0／0 |
| Qwen3.6 a2 | 3；jobs2／7实际消费失败 | 40 | 1／1，CMake拒读 |

表末两列的0／1是实际命令退出码；F2P/P2P是逐参考计数，不是正式reward。Qwen候选生成的`cmakeMinimumRequired`为3.25，实际输出报`version too new`。这不是凭静态数字判断，也不是schema版本被固定要求；正常gold与两个替代实现均可实际configure和build。

每方收集48个完整节点：45个已登记来源／新增参考完整出现，另三项平台限制的旧节点在Linux跳过（两项Only OSX、一项Only Windows），均不属于参考集。360条参考状态、全部准备与identity的RC0、八个容器删除／零残留、131件输入与原始回传SHA已核。没有ERROR collecting、缺失参考或安装失败。当前v2原件在忽略目录`runs/category2_repair_20260929/conan_cpu_20261003/diagnostic_evidence_15422_v2/output/`；`diagnostic_audit_15422_v2.json`与`diagnostic_15422_v2_remote_audit.json`列360个精确参考状态及131SHA。v1同名后缀原件保留，不改写成新结果。

历史候选的源码与测试改动须分开：Coder a3有README、额外测试和debug文件，DeepSeek a1有测试变更，a4改了本评分文件。此私有诊断只应用每份原patch中`conan/tools/cmake/presets.py`的原字节diff，保留完整原patch、投影SHA及明确遗漏路径；没有让候选测试覆盖受信草案。其它四份非空候选只有该源码文件，投影字节即原patch。结果不冒作完整历史FrozenPatch重放；正式grader仍需按自身初始化／冻结／恢复流程验收。

环境沿历史actor-v2的原Dockerfile恢复。原base config `sha256:bb264f88ffc338f8b33c58e15a5f0373761abfe75145e7ae201e360031a8b9c8`匹配；官方CMake3.23.5归档SHA `bbd7ad93d2a14ed3608021a9466ae63db76a24efd1fae7a5f7798c1de7ab9344`。派生config `sha256:a27936515e625ace25f5d76dcef25566079c7ac355b51bdfc5c3408c26a07ead`，实跑核PATH CMake3.23.5、系统`/usr/bin/cmake`3.22.1不变、Conan入口及testbed导入。构建10件SHA另核。根诊断使用原`private_behavior.py`、2CPU／4GiB、network none，UID0；没有重跑原安装前缀或新actor。

**v2的窄修订：** 在原显式jobs2／7节点内补实际configure＋build，使用Unix Makefiles、`project(NONE)`和已有cmake3.23工具fixture，不新增编译器依赖，不锁schema或最低版本数字。两个完整nodeid及全部5F／40P分组不变；默认Ninja与Ninja Multi-Config追加／替换节点保留。没有新增VS／Xcode／NMake范围条件。

v1静态／材料窄核不能自动覆盖新v2。[v1材料原件](materials/v1/revision_plan.json)、[v2材料](materials/v2/revision_plan.json)及[最小diff](materials/v2/from_v1.diff)分开保存；v2 patch为`9ad7529457054bb004534951feb4d08b40973a06fd30b4a1564054de074a0bb6`。v2真实私有矩阵已完成，现已成为根题卡／修订单的当前补丁。非作者v2核查仍待；原v1非作者材料窄核作为历史记录保留，不自动覆盖v2。私有失败不冒作正式新评分拒绝。

停止条件：私有v2已保留有效正对照和旧40参考并实际区分Qwen消费缺陷；据此交共用发布，不继续扩大矩阵或重跑不变v1。正式consumer／评分、非作者核查与GPU请求仍待；本轮没有改变模型预算或训练资格。
