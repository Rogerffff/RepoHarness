# Moto6408 R18 最终 CPU 原件非作者窄核

日期：2026-10-03。对象：getmoto__moto-6408，固定 R18 发布 cat2-cpu-r2e093-swe40-moto-offline-20261003-v1。审查者不是工具、题级材料或作者验收记录的作者，已接触私有测试、参考与金标，**不是公开盲读 solver**。

## 结论与适用范围

本次原件足以闭合 **R18 离线供应条件下的普通 CPU 诊断／后续基座探针准入**：三个原 CLI 控制臂的安装全部实际返回 0，分别得到 noop 0、gold 1、reorder_only 0；每臂完整解析 96 项，原 95P 全部通过，失败位置与控制臂作用一致。新宿主 UID54321 原公开 make init 成功，工作区来源与 SDK 正确；真实 Claude Code（CC）经确定桩执行五条原公开命令，安装成功、公开复现仍在目标断言失败、公开检查通过。完整候选、manager、UID 与 CC 清理证据均闭合。未发现需要阻止本次 CPU 结果收口的具体问题。

这里的 CC 是真实 CC 进程和 Bash 工具执行，但命令由确定桩提供，**没有自主模型求解**。它没有产生用于训练的 actor FrozenPatch，没有完成 actor-to-grader（a2g）闭环；本报告不授予 typed-actor 或训练资格。矩阵中的 kind='cc' 只是候选补丁输入枚举，也不是这次公开 CC 的求解结果。两个 legacy 检查布尔值仍为 false，适用边界见下文，不能改写成全检查通过。

审查只做本地标准库读回、SHA256／字节核对、JSON 与文本解析，以及补丁在内存中的严格应用比对；未执行项目、SDK、测试、Docker、CPU、SSH、远端或模型。未重审整题测试语义，未修改发布输入、工具、原件或既有报告，也未读取在途的 Moto6114 作业。

## 1. 原件与运输身份

原件根统一为 runs/category2_repair_20260929/moto_cpu_20261003/（下称证据根）。逐条重新核了各 <job>_evidence/transport_manifest.json 中全部文件的 SHA256 与字节数；共 **136 件运行原件、2,309,760 字节**，无不符、缺件或符号链接。另只读 tar 成员，将对应归档中的每件原件及 transport manifest 与本地文件逐字节核对，未解包、执行或回写原件。四份运输 receipt、归档与实际 manifest 相符；四份 job/status.json 均为 finished、returncode 0。

| 作业 | 实际范围 | 件数／总字节 | transport manifest SHA256 |
| --- | --- | --- | --- |
| moto6408-cpu-81c24ca0fe48 | noop | 45／659622 | e74cecd71ced4480654382e630460d4a51e90211dc58cd11d2af95a509aab2ec |
| moto6408-cpu-85ef01245f8b | gold、reorder_only | 60／1363230 | 6e7484af8524ee398148aa6d4d84476a002e231f10a00dbe04d355fce47cb093 |
| moto6408-uid-f1109eba8347 | 实际开发 UID 安装与来源 | 6／95650 | 49d9958a152621f73708fcfea0cc4caa6448c13319c05dbf26bcf9c9ab6d877e |
| moto6408-actor-ab7e8c1ffbbd | 真实 CC 五条公开命令 | 25／191258 | 2d8640a542c1c5e06fedc037e8f0bc27b124c9a9e66e0951cff8d9eff1770dfb |

归档的独立核值：

| 作业后缀 | 归档字节 | 归档 SHA256 |
| --- | --- | --- |
| 81c24ca0fe48 | 125977 | b2cf1cbe510050faf05d2837ea04d1fe69825aa80819827d63199ae362f84ffa |
| 85ef01245f8b | 264340 | 6ff5b8c6f576b7b64b6dbece5979726040c404f5a33f38a0f56961a064b15d56 |
| f1109eba8347 | 17242 | dc0d1e97b0931f0444f1b1edb8933c13c2ad1c2bfac035280050486030731a46 |
| ab7e8c1ffbbd | 26665 | 512df944c59b6678d828718fd1d543d395db19f3c74faa54d5e8dc6ccf4dcc32 |

作者材料仅作导航，结论来自上述运行原件。核后还对照了两个矩阵作者 raw readback 的 report 与逐参考状态：它们与原 ledger 及独立解析的实际日志完全相同。作者 Markdown 的历史“待 UID／actor”措辞不回写，本报告补闭合实际后来取得的原件。

导航材料身份：tasks/getmoto__moto-6408/cpu_matrix_owner_readback_r18_20261003.md 为 2926 字节、SHA256 bc2a0d7d498df9a951a385c44fc4325ec7718aacd36b83de3774ff1bd52b27b6；reviews/moto6408_r18_uid_install_owner_readback_20261003.json 为 1934 字节、e4afc2ba78504d7cde5c645e67a1e5230abca0b30fe0319f428634cab819b9ff；reviews/moto6408_r18_uid_public_actor_owner_readback_20261003.json 为 5697 字节、3b941b7aa4cff4d41776417e645fbc573adfc3b7e1e5ad9397a65dc641d9eeb4。未把作者的 true 字段作为独立证明。

## 2. R18 消费、环境与预算

沿用已固定的 moto_two_r18_offline_tools_non_author_20261003.md 和 moto_two_r18_public_actor_tools_non_author_20261003.md 静态范围，不重复审查全部 1419 个发布成员。当前 release manifest 仍为 a84bdc339618e010440df3728c982b2d1d141b1f8295f69761984386ee3a512e。三个工具 manifest 与成员重新核字节：矩阵 58e4b113ef1b98c3f5ce3df56cb7a654b9c2f4d425bd5f6b65e8c21eb49457d0，UID 7761a5da501bdc76aaf804cc6a05ac9f3b0c1e0e4193f9248670d98c0cd41560，公开 actor 8df46bb3a71d05288c8b50642c6661f6c606f2f22fdaaf7677903238a3a62f9c。

两个矩阵作业的 output/runtime_inputs.json 逐字节相同：11324 字节，SHA256 5b573330845f417270b886bf94b15c0e8a0e53eb872e3d0c19eaeb80e0c56870。每个已登记 expected 字段与工具 expected_runtime.json 的本题条目相同；实际 consumer_readback_before_checks.json 与该 expected 对象完全相同。核了实际 prepare、export-gold、run 命令文件、退出及完整 stdout/stderr，使用固定 R18 repo 的原 CLI，没有换 grader。

| 身份项 | 实际固定值 |
| --- | --- |
| public base | 1dfbeed5a72a4bd57361e44441d0d06af6a2e58a |
| public bundle | sha256:614eff48270224a61e540333a4588303eae4f76e5d3e259e894e78db7e16ba71 |
| ENV bundle | sha256:fc3f039787ba630fe6b8a80f5a4022fea3eb418b70219f9f57b3fe76933c8f08 |
| grading bundle | sha256:567ba1e2c71fa772cb3ac2e112ad1a7fb196056ca57ea1fa0b01a1b13a7dc0ae |
| grading registry | sha256:6b8864f0912219fdfd1cbfc5d5161544c5fdf57f9baa05ed53dc041c4d38a013 |
| grading revision | moto6408-tag-ownership-v1 |
| materials | sha256:7d6fc3219336eddad6b46bd7ac8d2bf4c59e9885fa87f36c3c37a1fee5453049 |
| effective test patch | sha256:00546841fca20f0b6b781fb49124370d0dab60bf99fdcd01e55aa947b4b65365 |
| scripts aggregate | sha256:0a9ea950c04be347597580233a5658ce48f282cc2f61e4eb6d37cdf798a69528 |
| 本题 source ConfigID | sha256:a0071858b0bb3a9c316e3c75dd49e9a3a2f8136f7bb4213e1210b44b7de2e689 |
| 本题 source manifest | sha256:db52bf5253616c8662863703accf3ad9e5c20e809e63f2e5829b48fb1212f8a4 |
| 本次实际运行 ConfigID | sha256:f00e022c3edf2dd23121abab802e401a64ee9e98598f07fb37a83d5c4c2012a1 |
| 注册供应 recipe | moto6408-offline-build-wheels-copy-only-v1 |

public source face 仍是 xingyaoww/sweb.eval.x86_64.getmoto_s_moto-6408:latest。实际 image inspect 同时返回本题 source 与 derived ConfigID；source 13 层是 derived 14 层的完整前缀，实际 ENV 含 PIP_NO_INDEX=1 与 /opt/rh2/build-wheels 的 find-links。没有借用 Moto5960 的 source 身份，也没有将诊断 override 写成新的 public source。

原 default prepare 指定本题与固定 repo，私有 host grading views 与 public prepared 面分离。原 export-gold 从 R18 固定 ingest 导出到 gold_input；run 明确传 registered recipe 和实际 f00e… derived ID，无 overlay、repeat 为 1。verify／inspect／prepare／export 与三次 run 的真实 CLI 退出均为 0，stderr 空；verify 的 passed_cpu_not_run 是发布材料状态，未冒充 CPU 验收证据。

实际预算保持：setup 300、apply 120、test 1800、candidate 900、whole 1800、cleanup 120、pull 1800 秒。实际策略保持 2CPU／4GiB／PID512／shm64MiB 与相应测试隔离。gold/reorder 的实际 prepared summary SHA256 bfd887dcd402f0104fce7b2af410feb4aaf4479b1f03af66761f9bc0c76fe5ef 又被新 UID 和公开 CC 输入绑定；不能用旧 R13 prepared 身份替代。

## 3. 三臂安装、评分和逐参考结果

读了三份完整 eval log、diagnostics、ledger、stage、classification、projection、baseline 和 FrozenPatch。每臂只有一条 ledger；stage_error 与 infra_failure_detail 为 null，report 为正常 resolved/unresolved、null/tests_failed、reward 0/1 组合。没有把非空 report 或 CLI 0 等同于正常评分。

| 臂 | raw reward／outcome／failure_category | 实际 make init | 实际 pytest | 1F／95P |
| --- | --- | --- | --- | --- |
| noop | 0／unresolved／tests_failed | 0，10.659 秒 | 1，12.030 秒 | 1F 失败；95P 全通过 |
| gold | 1／resolved／null | 0，11.126 秒 | 0，12.367 秒 | 1F 与 95P 全通过 |
| reorder_only | 0／unresolved／tests_failed | 0，11.146 秒 | 1，12.698 秒 | 1F 失败；95P 全通过 |

完整实际命令为原 make init 与 pytest -n0 -rA tests/test_ecr/test_ecr_boto3.py。三份日志均有完整、唯一的安装／测试开始、结束与 RC 标记；两次 editable build/install 均成功，install_skipped=false、install_failed_commands=[]、log_partial=false，install/test 的 completed 均为 true。candidate 包装 exec 为 0；noop 和 reorder 的 **内层 pytest 为 1**，不能把包装退出 0 当作测试全部通过。三臂是新供应下实际安装 0，不会静默抹掉旧 R13 源镜像三次安装 2 的历史观察。

三臂均收集 96 项，实际短摘要 96 行、解析键 96 个、无重复、遗漏、skip、XFAIL 或范围外键。按固定参考完整并集逐项重建状态，再核 diagnostics 的成功／失败／缺失／跳过／未解释分区，与每一项相符；每臂 95P 均为 PASSED，不只看总奖励。作者 raw readback 的逐参考状态与独立结果相同。

唯一 F 节点是 tests/test_ecr/test_ecr_boto3.py::test_multiple_tags__ensure_tags_exist_only_on_one_image。noop 在原前缀第 630 行 new_image["imageManifest"] == second_manifest 失败。reorder_only 已通过第一次 imageManifest、第二次 tag 写入与第二次 imageManifest 断言，也通过 moved["failures"] == []；随后 **第 635 行 assert len(moved["images"]) == 1 实际为 2 == 1 而失败**。完整回溯给出两条 image 结果。它通过重排使先取返回值正确，但共享 tag 的重复归属仍在，因此这个失败不是安装、导入或旧断言失败的替身。gold 完整 96 项通过。此处只核实际失败与控制输入关系，不扩展新的 AWS 行为要求。

| eval log | 完整字节 | SHA256 |
| --- | --- | --- |
| noop | 54122 | adafd927612debec37ce686c3f30ec419034584bda20e8e6e7a878793fb9871f |
| gold | 52634 | dac2c6e1589c6353e1082d3eca54cd875ad312e5f1a0c26d35fbf115ee5186ad |
| reorder_only | 54507 | 25a07b52058a7c7335f61cfdc2898e3098ce0fbf22274e2c2f68d58164cf9d45 |

## 4. FrozenPatch、恢复、保护与 CLI 双层清理

三臂 baseline canonical digest 都是 sha256:32fc7df32714c89e75f470cb901d66e388599d9cd1da1eb812e02ae67c09f904。核了固定消费者的 canonical JSON 编码规则，再独立重算 baseline 与 FP digest；classification 为 projectable，私有路径、excluded／ignored 及 runner integrity 越界项均未出现。baseline 的 ENV 字段为原契约中的 null，未伪填成 ENV bundle 身份。

noop FP entries 为空，digest sha256:c7a1f2cc9dc27d7c5429cfc94c369e2c997c8d060e95c375385e4c2c1ecff751。gold 与 reorder_only 的 FP 都仅修改 moto/ecr/models.py，普通文件模式 100644。原公开 base 文件为 40991 字节，SHA256 4df8182f9651cc5ef40ecac5defd993da7e9277e241de403b189c9b41658dc70；只用标准库在内存逐 hunk 验证旧行并应用实际 patch，所得完整内容与 FP 的 base64 payload 逐字节相同，没有执行候选。

| 候选 | 输入 patch SHA256／字节 | FP digest | 实际 payload SHA256／字节 |
| --- | --- | --- | --- |
| gold | fa6d9adadc553b4eb713ca3749a90efe7adb572348c837fd2bbf48a3dd95d7dd／993 | sha256:c7a0ad65e5d1db08e250158fa2adf21143f913517a8a98781eb20cf2591337ce | 6409665fa0420c68497ff050f3af09240fa4a8d0facbf19c883f4439c3d41a01／41279 |
| reorder_only | 38870a10babbb10239825686c1493cefdff753bf3d7a15db83f217de8321ee8b／290 | sha256:4e0dba7ef7a260319edd3f95809123556f62fb7b6a57e2ced71ae7865e708ec3 | 48d45a656d49931ccc3ae43c03e555b6b5240015bf4f7fb95b443ef55c46f315／41064 |

gold artifact 的 candidate.patch 与此次 export 的 gold_input、gold manifest pin 相同；reorder artifact 与题主固定 reorder_only.patch 相同。没有替换补丁或将公开 CC 的运行嫁接为这些 FP。旧 constructed_negative_unrun 是历史角色元数据，不能据此否认本次确实已跑；旧 R5 的原材料反例正式得分仍未知，本次不反向填分。

candidate apply 的实际 agent UID 为 54321。sanitize 记录保留 base HEAD、7671 条历史，删除 46 个引用后余 192，remotes／reflog／unreachable 为 0，验证违规列表空。grading 侧有相应 sanitize。trusted setup 的 restore 为 1、apply 0，预期和实际测试文件均为 1，无缺失或 irregular；protect 实际 protected 1、目录 3，检查 OK。原评分 prerequisites 以 UID54322、HOME=/rh2grader 运行，固定离线 wheel hash／读取检查 RC0，输出 RH2_MOTO_FIXED_OFFLINE_PREREQUISITE_OK=1，脚本 SHA256 02dbe5bd09606ecf644bed6cd187f8f601a5debf7b1b91dd6905f81cd0c163e4。

三次候选 cleanup 均实际 removed=true、rm:ok。完整 CLI stdout footer 各为 rows=1、halted/aborted=null、final exit=0/reason=ok；manager_close created=1、removed=1、containers_open/supply_open/cleanup_errors 空，open grader 与 cleanup failure 列表空，regrade 次数 0。各候选自有标签容器和网络查询都实际 RC0，stdout/stderr 空；没有把查询失败当零残留。

diagnostics 的 resource_facts 为 null、没有额外 environment qualification 收据，因此不能据此生成训练所需的 actual grader HostConfig 全量资质。它保留了正确的评分 UID／profile 策略及实际完整执行；另有下面 UID、CC 初态容器的具体 inspect 与 cgroup 事实，不把它们跨角色替代训练资质。

## 5. 新宿主 UID54321 的真实开发安装

moto6408-uid-f1109eba8347 的 output/docker_calls.json 共 **13 次实际调用，均 RC0**。逐次读完整 stdout/stderr、记录及 result，核 image inspect、run、sanitize、初始化、BASH_ENV 写入、激活检查、原公开安装、身份来源、两次 inspect、删除与两次 absence 查询。result 中 public_development_install 的输出、RC 与第 7 次实际调用逐字节相同。

安装不是 grader root 的安装代证：第 7 次实际 exec 为 user54321、HOME=/home/agent、BASH_ENV=/rh2/bash_env，在 /testbed 执行 PYTHONDONTWRITEBYTECODE=1 make init。完整 stdout **21135 字节／157 行**，SHA256 c3ff6ac751a13b5e98d88b88b7db021d47f4956d799b6cda0483d7098d8e4dac；stderr **426 字节**，SHA256 ed35e0e19a25feaf7ed5c8ae560c1768d041c025c8d733fb28ad3ece924d8f7f。离线 find-links、两次 editable Moto 构建／安装成功，真实 RC0；普通 site-packages 不可写后使用 user install。stderr 两条是 moto_server 用户 bin 不在 PATH 的警告，不是安装失败。本次验证的是原 Python 开发路径，没有额外验证 moto_server CLI 的 PATH 可用性。

sanitize 的 base/history/引用和安装前初始化身份与矩阵相容；activation probe 实际正确。安装后的独立身份输出与 result 相同：UID/GID54321，cwd /testbed，HOME /home/agent；解释器 /opt/miniconda3/envs/testbed/bin/python，sys.prefix 为 testbed 环境；moto 从 /testbed/moto/__init__.py，本题模块从 /testbed/moto/ecr/models.py 加载，实际模块 SHA256 为公开 base 的 4df818…dc70；boto3、botocore 都为 **1.35.9**。

第 9 次实际 inspect 的 image 是本题 f00e…，自有 job label 正确；NanoCpus=2000000000、Memory=4294967296、PidsLimit=512、ShmSize=67108864、NetworkMode=none，与 result/profile 对应。第 10 次 inspect 再核自有对象；第 11 次删除 RC0，第 12／13 次自有容器与网络查询 RC0、stdout/stderr 全空。所有 13 次调用都已读回，而非只接受 summary 的 true。

## 6. 真实 CC 的原公开命令、实际请求与完整结果

CC 输入只来自原公开 prepared prompt、公开 brief 安装命令和 B3 public_read.md 的 bash 块。原 B3 文件为 16608 字节、SHA256 3212cb98b0a286da9a7759f476af6bbcd0f1c0ae3f28e95602dcd74e2111739d；commands_6408.json 为 3029 字节、670922f251bd1dbd90d408bdf86129dd4e71fadee2303b10535c72945c2742e8。逐字节核了 INSTALL、C1、C2，以及原 C3 的两行命令分别作为 C3a／C3b。原可选 C4 未执行，不包装成必需项缺失。

首真实 API 请求 messages_000.json 为 **14332 字节**、SHA256 bc32b473fa882b898c58b054f90fd190a2f92283cdafd8fd557f9cb7a58786b0；其中公开 prompt SHA256 2e130fceb4237c21e81155c8f54d6c96ad87e1a7476ca5a3c544ab3ef6c81aea，与当前 R18 prepared prompt 相同。读了完整用户文本，仍是原 ECR tag 问题与公开复现，没有私有新增断言、补丁、金标或答案。

完整 trajectory 为 **61 行、27399 字节**，SHA256 952726c9f54e35a60d9e92115548693fa9571c059619376b667b7375e590e991；含 system13／stream36／assistant6／user5／result1。实际五条 Bash 在第 6／17／26／35／46 行，工具结果在第 12／21／30／41／52 行，最后 end/result 在第 57／61 行。六次真实 API 请求分别携带 1／3／5／7／9／11 条消息；原请求中的此前 tool-use ID、输入及 tool-result 与 trajectory 逐项相同（只去除 cache-control 元数据后比较），未用构造 actor_spec 代替真实 request。

对五个实际 Bash 的完整 wrapper 作了精确文本比对：原 command 字节不变；INSTALL 内层 timeout300、工具330000ms，其余内层240、工具270000ms。wrapper 保存完整 stdout/stderr、真实内层 RC、字节摘要与 RH2DC_END，自身 exit0。所有 .full 与记录 SHA／bytes 相同，output_truncated_to=null，五份完整输出均已读取。

| 公开操作 | 完整捕获字节／SHA256 | 实际内层 RC 与语义 |
| --- | --- | --- |
| INSTALL | 21561／903d9b32f7382d0c018badff46d01af5ccd30ec0945abd41d77de351451d420a | 0；真实 UID 开发安装，离线依赖及两次 editable 构建／安装成功；仅用户 bin PATH 警告 |
| C1 | 80／ab0967c0cce76e574754091ac6f87e0715d1ab255d05b0930be45c22a961a83d | 0；输出 testbed Python 路径、/testbed/moto/__init__.py、boto3/botocore 1.35.9 |
| C2 | 259／3cbee7c06b7f9fd434e89cde4b6e3ea28d8696a2db45fd97260bbf7d13faf58a | 1；公开复现第 30 行目标 AssertionError，见下文 |
| C3a | 982／85aa4b49b446c6d327a988c8bca32f50c8e6b30e03693ded555a1544f55cc3ca | 0；19 passed、76 deselected、90 warnings，3.05 秒 |
| C3b | 2025／9881a4c3fcfbc44e7c73578ddd7bd677d9430bcd350fe0fbad309e98ba7016df | 0；原公开模块 95 passed、356 warnings，14.72 秒 |

C2 完整回溯先经 <stdin> 第 32 行、公开 /testbed/moto/core/models.py mock wrapper 第 124 行，再落到 reproduce 第 **30 行 assert initial_image != new_image**；AssertionError 无额外文本。原脚本此前已通过两份 manifest 不同的断言，完成 repository／两个 image 创建、第一次共享 tag 写入与读取、第二次改 tag 与读取。失败位置证明目标复现仍在，不是解释器、依赖、SDK 或 mock 启动失败。本题 C2 没打印两个 manifest 的实际值，不能借别题输出声称它打印了值；能确定的是该最后比较在原源码上失败。

C3b 是**原公开 95 项**，不是 revised 私有评分的 96 项；C3a/C3b 的简略 pytest 摘要不代替矩阵的逐参考 96 项验收。C1 只打印解释器路径，未打印 Python 版本号，不能从别题推定本次 C1 显式证明了版本号。

实际 CC version 2.1.205，工具 tar SHA256 d3dadfa9cde294ac82c755eb6d889291228849180bac5d677ad1a4027aca1bc4；wall1800、max-turns8。harness 实际 Running=false、ExitCode=0、stdout27399B、stderr0、日志完整、stream error=null；最后 result success、is_error=false、num_turns6。桩实际 messages6、message_start6、count_tokens0；这些是确定桩运行事实，不是自主模型的能力或费用证明。

## 7. CC 实际身份、legacy false 与 finally 清理

完整 prelaunch.json 为 2300 字节、SHA256 c587ac21b5105af192d2227611a9e3e9858b5ccd6830dc856d36d758e5accb36；activation_check.json 为 506 字节、73fb9643db872f68959ebfcdb426723effe20413035d8a64063b248103bf1bf3。真实 inspect 为本题 f00e… 镜像、2CPU、4GiB memory/memory-swap、PID512、shm64MiB、init=true；home/tmp 使用原 tmpfs 限额，没有 host bind/mount，no-new-privileges、非 privileged。

实际 agent UID/GID54321，permitted/effective capabilities 为 0、NoNewPrivs=1；cgroup CPU 为 200000/100000、memory4GiB、pids512、swap0，工作区 owner54321且可写。生产 sanitize/init/activation 保持固定 base 和 testbed 环境；root 管理 BASH_ENV 文件0644、目录0755，agent 可读、写入 DENIED。实际 DNS／直接上游／受禁目标与 root 执行被拒绝，既定 relay 可连接。原 CC profile 的网络隔离不同于 UID smoke 的 network none，不把两者混称相同网络模式。

interpreter_in_tool_result=false 和 bashenv_denied_for_agent=false 保留原值。固定 DevRunner 的前者仅在 trajectory 的 tool-result 文本中搜 RH2_SYS_EXECUTABLE=<prefix>/，后者仅搜 RH2_BASHENV_WRITE=DENIED。这次原公开命令通过完整捕获文件交付，tool-result 是 RC／捕获摘要，没有生成这两种旧标记；公开清单也没有专门的 BASH_ENV 写入标记测试。因此两个旧布尔检查本身没有通过，不能静默改为 true。

实际解释器／模块来源由 C1 全输出、生产 activation 与独立 UID 读回支持；实际 BASH_ENV 当前访问控制由 prelaunch 的 ACTIVATION_WRITE=DENIED、root 所有权和0644／0755支持。它们解释当前事实，不冒充缺失的旧 tool-result marker 测试，也不授予更广的安全或训练认证。

post_run_facts_root.txt 保留旧文件名，但真实调用角色为 **agent_uid_54321**。全文给出 harness/runsh/rundone 已不存在、git status RC0、agent 进程曾有4个，可信清理后 RH2_AGENT_PROCS_AFTER=0；newer files119及有限 cache 路径是实际 import／测试产生的工作区事实，不能声称 agent 无写入。整段包含 Git，因此按既定工具在 agent 角色执行；本报告不凭文件名当 root 证明。

attempt finally 的实际 container_rm=0、stub_rc=0，network／relay failures 空；最终自有标签容器／网络列表空，force 后残留空。固定 DevRunner 的 finally 包含容器、relay、网络、stub 清理和最终重复查询；查询失败会形成 sentinel，不会被当空列表。本批 CC 原件没有 UID 工具那样的全部 Docker argv/stdout 调用清单，清理证据限于实际 attempt／最终查询、固定消费者代码和 parent0，未虚构该清单。作者关于角色／命令／清理的摘要与独立原件相符。

## 8. 收口边界与保留项

本次证明固定 R18 的供应缺件已在这三个原控制臂和两种实际开发执行路径上解决，原评分参考、补丁与 consumer 身份保持，结果 0/1/0 与逐参考和具体失败位置相符。普通 CPU 诊断与后续基座探针可以使用这些已闭合条件，无本次启动／验收阻断。

以下历史与资格边界继续保留：旧 R13 source 镜像的安装失败、旧 R5 原材料反例得分未知、未开始的 UID75，都不由本次改写；没有把 UID75当题目失败或样本。公开 CC 是确定桩命令执行，没有自主修题、模型尝试或 actor FrozenPatch/a2g。矩阵 FP 是独立控制输入，不能嫁接为该 CC 的提交；训练 typed-actor 资格、额外 grader 资源资质和未执行的可选 C4 不在本报告授予范围。没有本题 CPU 结果之外的跨题环境保证。

本报告为唯一新增文件；原件、作者导航、固定发布与此前非作者报告均保持原字节。
