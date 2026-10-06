# 6283 v2 正式 CPU 结果与旧公开 actor 有限复用：非作者窄核

核查日期：2026-10-03。已接触私有 v1/v2 材料、旧 CPU/GPU 诊断上下文；不是 fresh 公开读者。仅用本地标准库读取原件、独立复算和静态代码核对，未执行 Docker、SSH、安装、项目 pytest、模型或作者检查/helper。

本轮四行 CPU 核查通过，reward 实际为 0/1/0/0；新增 PrivateAttr 普通行为失败已真实观察。旧 actor 可有限复用为原 source/base 公开题面与固定 CC 开发路径证据，本报告范围内可继续普通 GPU 探针。旧 actor 实际是 base 24e9…，formal grader 是 derived 58d…，不能称相同派生 actor。GPU 自身实际镜像/安装、真实模型/full roles/typed 训练资格未由本审查验收；旧 GPU 原 FrozenPatch 未补评分。

## 运行与原件绑定

job=pyd6283-formal-20261003033613-v2-b5f3a；namespace=formal_6283_privateattr_v2；source_release=cat2-cpu-r2e093-swe40-pyd6283-moto6114-20261003-v1；manifest=2cfdd9b4f1134c0915346b727b729665482c4c1121b550764833f16f2982402e。

[固定输入](../cpu_acceptance_20261003/6283_privateattr_v2/formal_inputs.json) SHA=4d50c69969e883e48f919ac1221594d88665e409a720f67b9a16952c393b4640；[runner](../cpu_acceptance_20261003/6283_privateattr_v2/run_formal.py) SHA=40b0460b70c2890a1eb3fbbf2474e10bee906125e3068868079370044d875805。

[原件索引](../cpu_acceptance_20261003/6283_privateattr_v2/results.json) 的 498 个成员逐件大小/SHA 重算通过，包内与 jobs 槽日志精确集合吻合；tar 内 498 个唯一普通成员全字节与回收原件一致，无解包/执行。tar SHA=a58348d8af6e6d0e4bb9d9d215cc9162c915a7a4ba9d87dad2743ea36facea11。cpu-a slot1，03:36:16–03:48:52 UTC，自然 returncode=0；formal wall=755.791 秒，跨四行多阶段，不是单次 reset 超限。

复用已有 R19 1476 成员发布/固定输入/材料静态审查，没有机械重核整个 release。本轮重核 manifest 和六份相关冻结源码的 manifest 大小/SHA、实际 slot release/material-root/runtime 参数、保存的七脚本及 prepare 公私分区；runner 从冻结 release/rh2/src 前置加载 consumer。status 的 actor_host_spec_equal 是所存 spec 子集口径，不称全部 32 字段独立相等。

## 真实评分与失败机制

逐行读取完整日志唯一测试区段，逐 ID 提取原状态，和冻结 pure parser、report、ledger、分区 diagnostics 交叉核对。每行 41 参考为 2 F2P/39 P2P，无 missing/skipped/unaccounted；按全部 F 通过且全部 P 保持通过独立重算二元 reward，没有只信作者 checks。

| 候选 | reward | F通过/2 | P失败/39 | pytest rc | 机制 |
| --- | ---: | ---: | ---: | ---: | --- |
| noop | 0 | 0 | 0 | 1 | equality 与非示例 equality 普通断言失败 |
| gold | 1 | 2 | 0 | 0 | 全 41 参考通过 |
| validate_construct | 0 | 2 | 2 | 1 | 旧 construct/nested 被误做验证，普通 ValidationError |
| qwen36_a1_pop_private | 0 | 2 | 1 | 1 | 唯一新增 PrivateAttr construct 默认值节点 TypeError |

noop 在 test_root_model.py:313/:498 比较正常实例和构造实例失败。validate_construct 在 :186/:194 调入候选 main.py:194 的 cls(values['root'])，使 Base64Str 构造重新验证；它早已被旧 P2P 拒绝，不是新漏奖。Qwen 对照旧 40 个参考全通过，新增 :505 读取 model_construct(42)._secret 时于 main.py:685 报 TypeError: NoneType object is not subscriptable；这是新增普通行为的拒绝，非安装或基础设施失败。

每行原始 pytest 节点 46 个：noop/validate 各 41P+2F+3XFAIL，gold 43P+3XFAIL，Qwen 42P+1F+3XFAIL。冻结 parser 有 43 键，其中 41 参考合法且完整；另两个含空格 dict[int, bool] 参数节点被截为“…dict[int,”→“bool]]”，三个带理由 XFAIL 未入 parser 表。该既有缺口不阻断当前 41 参考，不外推全 pool；43 键不能称全 46 节点合法状态表。

四份 supplemental stdout 与真实 exec stdout 全字节一致。四行普通初始化 _secret 均为 abc；model_construct 的 noop/gold/validate 均为 abc，无异常，Qwen 为 TypeError。补充观察不改 reward；正式新增节点已经实际执行并判分。

## 源码、E10 安装、身份与公开隔离

八次 candidate/grader run 和四份 inspect 实际都是 sha256:58d0c004cec144834a01dfc160c0f4caf427a9b31fd5ad95a60d03f6f3623226。候选补丁应用为 agent/54321，正式测试/补充观察实际 -u 54322；Python3.8.19/core0.42.0/pydantic2.0b3，import=/testbed/pydantic/__init__.py。main/root_model/_model_construction 模块路径和文件 SHA 与固定输入及冻结源内容全吻合；Qwen root_model SHA=2e8b2748bea649c5bde853049ba9255d62dd6eb033ad9c979dac90765f644b44，匹配既核旧 GPU 源码等价绑定。

E10 install asset SHA=6e50864b8f8976413f6fb32df2fd11060e1b190fb4161c8567810ac748e6a570。recipe 和 eval/candidate install/test 内嵌安装文本逐字一致：先 editable 消费候选，再从候选 pyproject testing/testing-extra 导出安装依赖，失败向外传播。四行完整日志各有唯一安装/测试开始结束、RH2_INSTALL_RC=0，无失败步骤，candidate exec=0、片段完整；pytest rc 如表。wrapper/docker exec 0 不等于 pytest 0。

实际有效测试 SHA=6bb8bce7277436102efc2bb43a61dcddd2ccf9830730b7e3026b7add680129e8，owner0、grader54322 不可写，runner 前后摘要一致。私有 trusted_setup 只写 grader 容器；候选只运输源补丁。prepared 公共 payload 无 grading 或新增私有节点，与旧 actor 原题面/public hints 逐字相同，host grading view 独立保存。

实际 2 CPU/4,294,967,296 字节内存/pids512/network none；四 prelaunch 均 UID54322、effective capabilities=0、NNP=1、DNS denied，inspect 无 bind/mount、OOMKilled=false。reset/apply/test=300/120/1800，未采用 R20 的 900 秒例外。protect 0025/0060/0095/0130 分别 132.983/120.217/128.154/184.567 秒，均 RC0 和 RH2_PROTECT_OK=1；本 run 成功不保证共享 CPU 全面恢复或未来 300 秒足够。

## FrozenPatch、完整 baseline 与运输

四 baseline 均完整 391 唯一文件，canonical digest=sha256:0143226df9f52b56a3921127ed7ef0cb3b56c11b3eea232418cfffc9ab35e0ef。12 次 candidate baseline/post 与 grader baseline census 全 path/object type/mode/content digest 逐项核对，391 文件和 25 excluded digest 一致；未只比较数量。精确镜像/base HEAD a29286609e79c79b2ecd71bc7272eea43ed9fccd 保持，grader 重建与候选基线一致。

noop delta 为空；gold/validate 仅 main.py，Qwen 仅 root_model.py。三 candidate.patch 与固定输入/实际 stdin 一致；源导出 base64、FrozenPatch 全 content_b64/content_digest、grader 写入 stdin 全字节一致；post 恰为 baseline 加 delta，其他文件未变。baseline/FP canonical digest、projection/ledger、task/public/image/head、physical_attempt/rollout ID 全连接；hygiene clean、projectable。391 文件内容证据是全逐文件 digest/census 加精确镜像重建，归档没有逐字节复制所有 baseline 文件。

baseline environment_package_digest 保持 null；current revision/ledger envdigest 非 null，不能补写 baseline env 身份。ledger env_qualification=absent。运输支持当前受信 CPU 重放与普通探针，不提供 typed 训练租约/资格。

## 清理与旧 actor 有限复用

140 docker calls 全 RC0。四 candidate 和四 grader 的 8 次 rm 成功；manager 建/删各4，open/supply/cleanup failures 空，final_status0。末尾 0139 ps/0140 network 使用本 run label，RC0且 stdout/stderr 空，本 run 零残留已核。

复用 job=pyd6283-actor-v1-20261002T173908Z-652bc，实际原发布 cat2-cpu-r2e064065-swe5-20261003-v1 / manifest282021962a92b510f077385660ac56acedcd7fac1d97e63db3baa98e4dcc057f。它是旧 R7 审查复用的更早原 source actor，不是 R19 actor 重跑，也不是当时在 R7 release 下执行。本轮再核 32 归档成员全字节及 attempt/prelaunch/captures/四请求与必要冻结源码数据流。

actor 实际 Image=sha256:24e9c51fedb7dc930796362c90f72e8e7a9c47d9362fa72414c6c6ff8a1a2882，与 R19 base_id 相同，绝不是 derived58d。UID54321/Python3.8.19/core0.42.0/base HEAD/main.py SHA/import与可写性通过。公开三命令实际0/1/0：原 equality TARGET_EQUALS False 的 rc1 是已知基线问题，已有公开测试41 passed+3xfailed。正式四行 E10 新安装在 grader54322 已验，旧 actor 三命令没有重新执行 E10 recipe。

真实 CC2.1.205 经四请求/三 Bash 控制桩运行；首请求原题面逐字存在，保存文本仅按 CRLF 标准化对照，公开 hints/public payload 未变。核420解码请求字符串及完整私有补丁/新增节点均未交 solver；原入口从 rollout_views 构造 grading_spec=None，driver 只收公共 prompt，binds/mounts=[]。主机 host context 加载私有 view 不等于交付 solver。收尾零残留、agent procs0。

actor_reuse_accepted=true 仅为原 source/base 固定公开 CC 交付、导入、已有测试和可写开发路径。actual_58d_actor_verified=false；不宣称真实模型/fresh reader/源码编辑成功/大范围开发/full roles/typed actor。公开输入未改，不要求更换公开读者。

## 当前用途与限制

cpu_review_passed=true；ordinary_gpu_probe_ready_within_review_scope=true。这个 true 表示四行 CPU 与允许的 source 公开诊断复用没有范围内阻断，可继续普通 GPU 事实收集。GPU 须绑定授权 actual image_override 和真实服务/checkpoint，并自行核 UID54321 的实际镜像/core/import/wheel可读性/E10安装开发/清理，本报告不代验。

旧 GPU 首臂 install RC1/权限拒绝、原 raw reward1 和40参考历史工件保持；源等价新 CPU0不是对旧 GPU 原 FrozenPatch 实际补评分。没有新 GPU 执行/请求提交、训练资格断言、reward规则修改或历史回写。只写本 MD 与同名 JSON；raw_bindings 绑定索引/归档/关键原件，完整498成员清单留在原索引。
