# Pydantic 9066：R14 实际 CPU 与公开 actor 非作者窄核

日期：2026-10-03。结论：**本轮 CPU 核查通过，可在本报告范围内进入普通 GPU 探针，使用已登记的精确派生镜像 override。未授予训练资格。** 正式原始分数为 `noop/gold/fallback/upstream271/gold_catch_user_error = 0/0/1/1/0`。五行均完成普通评分；gold 与 catch 的失败来自新增行为约束，不是基础设施错误。公开 actor 已实际执行三条固定命令，完成公开输入交付、导入与小范围开发路径诊断；其返回由控制桩驱动，不是模型解题表现。

## 范围、身份与原件

审查者不是本轮材料、runner 或结果作者，但已接触四题私有材料、控制 patch、参考节点与正式结果，**不是 fresh 公开读者**。复用[四题材料意见](non_author_remaining_material_review_20261003.md)、[R14 固定输入与执行入口意见](non_author_remaining_runner_review_20261003.md)、已有 R7/common runner 意见和发布者 R14 维护／部署证据；不重新审全题语义、全 release 或旧矩阵。公开题面未改，不新增公开读者要求。审查只读本地原件，使用标准库复算 SHA、tar 成员、JSON、AST 提取的冻结 parser、逐节点结果和运输字节；没有连接远端或运行 Docker、模型、安装、项目测试、作者自动检查脚本。只写本报告和[机器读摘要](non_author_9066_cpu_review_20261003.json)。

| 项目 | 绑定 |
| --- | --- |
| 发布包 | `cat2-cpu-r2e089092-swe34-dvc-pyd-20261003-v1` |
| manifest SHA | `51b833975be2c3354be45b731552235a33070315f0039c8e6f54987de95f6ca8` |
| revision | `pyd9066-behavior-v1`；[revision.json](../tasks/pydantic__pydantic-9066/revision.json) SHA `d59f0056995ad33db4cafc63ab9541298f8222d44daef80160ea971ff8bea17d` |
| 正式 job | `pyd9066-formal-20261002235809-r14-19f71`，slot 0，23:58:12Z 至次日 00:16:23Z，自然结束 0 |
| 公开 actor job | `pyd9066-actor-20261003001628-r14-6ff79`，slot 0，00:16:31Z 至 00:17:33Z，自然结束 0 |
| 正式归档 | 654 件；tar SHA `62622bb332360e9fc5b32b0b6a70becc7ea0edda87bdb065e0bb4f0007fae6e2` |
| actor 归档 | 32 件；tar SHA `d6607c7cb7071870715903eef7683eee523ec0ce720abd912372d8f90be592b4` |
| 正式入口／固定输入 SHA | `b127f7309ffae3eae2bbe834c595f846104406e2f858b8073ff2182d0a2ce3c5` / `bea70edd55d2a316b5d92fde1a3a894e9c79363a168e2cd92c7de2d40b83ac1b` |
| actor 入口／固定输入 SHA | `21caef4f953334a2b3759657ac3d5de00bd03373ffa8e40794674ddf5797f4f9` / `226ef4ab9be63c08f0ddfdd5755dc48353d87b3c24fbc3732745737cf36e3882` |

原件根位于 `runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/`：正式在 `packages/swe_pydantic/formal_v2/outputs/<正式 job>/`，actor 在 `packages/swe_pydantic/diagnostics_v2/outputs/<actor job>/`，各有 `jobs/swe_pydantic/<job>/` 控制原件。逐件清单为 [remaining/results.json](../cpu_acceptance_20261003/remaining/results.json)。独立核对全部 686 件路径、长度和 SHA；两个 tar 精确含相应 654／32 个普通文件，逐成员实际 payload 与清单一致，无缺项或多项。没有把 wrapper 的 `passed` 或作者 `checks` 当作独立结论。

## 逐参考结果与失败机制

每行固定参考为 **2 F2P + 367 旧 P2P + 1 新 P2P = 370**。新节点是 `tests/test_json_schema.py::test_default_encoding_preserves_stdlib_dataclass_instance`，要求标准库 dataclass 实例默认值继续编码成 `{'x': 1}`。原日志的 370 个完整 ID 与冻结 parser、ledger／report 分区逐项相等，无缺失、跳过或未归账参考；正对照均 370/370 PASS。机器摘要保留每行逐参考状态、完整原始 385 节点状态、非参考 parser 差异及日志 SHA。

| 候选 | 原始 reward | 旧 F2P PASS | 旧 P2P PASS | 新 dataclass P2P | 测试退出 |
| --- | ---: | ---: | ---: | --- | ---: |
| noop | 0 | 0/2 | 367/367 | PASS | 1 |
| gold | 0 | 2/2 | 367/367 | FAIL | 1 |
| fallback | 1 | 2/2 | 367/367 | PASS | 0 |
| upstream271 | 1 | 2/2 | 367/367 | PASS | 0 |
| gold_catch_user_error | 0 | 2/2 | 367/367 | FAIL | 1 |

读取完整失败栈后，三个负对照均可归为普通行为失败：

- noop：`json_schema.py:1012 → encode_default:1997` 的 core 序列化无法处理 IPv4／IPv6 默认值；`default_schema:1014` 发出排除默认值的 `PydanticJsonSchemaWarning`，测试将警告视为错误。两个旧 F2P 都失败，其余参考通过。
- gold：旧 IPv4／IPv6 修好，但新节点在 `test_json_schema.py:6045` 求 `Model.model_json_schema()` 时，`json_schema.py:2003` 向 `TypeAdapter(type(dft), config=...)` 传入 dataclass 禁止的外部 config，触发 `type_adapter.py:198` 的 `PydanticUserError`。这是新增节点发现的行为回归。
- gold_catch_user_error：捕获该 `PydanticUserError` 后，`json_schema.py:2006` 改抛 `PydanticSerializationError`，再被 `default_schema` 转成排除默认值的警告；新节点仍失败。改换异常没有保住原有 dataclass 默认值。

gold 与 catch 都修复旧 F2P，却被新增 P2P 拒绝；fallback 与 upstream271 同时修复旧缺陷并保持该行为。该证据支持本轮材料的区分作用，不外推为全部 JSON schema 场景已正确。五份 report 均保留 `swe_f2p_p2p`、`binary_v1` 原始评分语义；负行 `tests_failed/unresolved`，正行 `resolved`，无 execution failure stage、infra detail 或 collection error。没有重算或改写 reward。

## 实际安装、运行身份与受保护测试

正式材料身份 `sha256:c72cb966577c64feeb474ea27d304810ce07970af5a5271835a8c812dfeff906`；公开 bundle `sha256:0e6d29a3ac6c591724068a898c07dd4d2a8349f365fa5be9d5700072b0262517`；prepare 环境锚 `sha256:12cea03dbaa225292741e58dc6629710908ab124e3310e9cadd1140f1bad8650`。effective test patch SHA `9d04a80216d751b3c60528a11d90ebe75da799a4d4dd8415412d13b441b14cec`，实际受保护的 `tests/test_json_schema.py` SHA `ab09716b68a52cb5e9d2255cb6e9aa73c6c72598cce84334e26d538b981943ed`。固定安装资产 SHA `7335a7c2790cf4b199fdc725ea53dd828329f2eb03d6f822dbc1e7b93279e2f5`。

五次实际 prerequisite stdin 绑定 `pyd9066-e10-fixed-v1`、Python 3.8、core 2.16.3、offline pip 和八个登记 wheel 的 SHA；对应执行均为 0，原 stdout 唯一完成标记 `RH2_PYD_FIXED_OFFLINE_PREREQUISITE_OK=1`。安装日志的实际 editable 安装和测试依赖命令退出全为 0，未见行首 `RH2_INSTALL_CMD_FAILED=`，install 没有跳过，candidate exec 退出 0、完整 segment。五份测试段各有唯一开始／结束标记，字节数和 SHA 与 ledger／report 一致；测试退出 `1/1/0/0/1`，未因非零测试退出丢失后续评分。

实际正式测试为 UID **54322**、Python **3.8.19**、`/opt/miniconda3/envs/testbed/bin/python`、core **2.16.3**。`pydantic.__file__` 和 `pydantic.json_schema.__file__` 均来自 `/testbed`；每行导入源码的实际 SHA 与固定候选及 FrozenPatch 运输后的 bytes 一致。有效测试为 root 所有、对执行 UID 不可写。base commit 为 `a3b7214a1d6ac8e32c29e9d4436ea6a9e253ead7`。

base image 为 `sha256:5a05759a5549cc7d65c471fb5d57d8fc554485b6c178a389a1fd373111ff3f4d`；实际派生 image 为 `sha256:2241ad13bceafacf38976b8cfa3d41d0b489099a11741876abba29cbe32781cb`。五个候选与五个 grader 的实际 run 参数均绑定此 ID、`--network none`、2 CPU、4 GiB、512 pids；实际 cgroup 同为 `200000 100000`、`4294967296`、`512`。已保存的七个脚本摘要、实际 trusted setup／测试 stdin 与固定 spec 一致，runner 前后摘要未变。

## 完整基线、候选字节运输、预算与清理

五份 FULL baseline 均含 **482 个政策内文件／对象**，canonical digest 同为 `sha256:358bf444821190bbfe7c321c6c97e541974207284cfce3f896f887f9e223a786`。独立复算每份 canonical 摘要，并核每行候选初态、候选应用后、fresh grader 应用 delta 前的完整原始 census，共 **15 份**：逐路径、类型、模式、内容摘要相等，并复算 25 个政策排除对象的 census 摘要。不是只比较被改源码；也没有把这称为测试后再做的完整 census。

noop 无 delta，其余候选仅有 `pydantic/json_schema.py` 的一项修改，另外 481 个政策内对象保持基线。实际 patch stdin 与登记 patch SHA 一致；候选导出的 base64 源码、FrozenPatch content bytes、内容 digest、projection canonical digest、fresh grader 的实际注入 stdin 均独立对应，导入探针再次确认最终源码 SHA。FrozenPatch 的 task、physical attempt、rollout execution、public bundle、runtime image、HEAD、baseline digest 均与该行 ledger／projection 对齐。fresh grader 在应用 delta 前重建并验证全部 482 项基线；这里的完整基线验收依据是逐文件 census 与摘要，而非声称另有一个包含全部基线内容的 transport tar。两个上述 tar 是本次证据归档，其逐成员内容已另行核验。

**baseline manifest 的 `environment_package_digest` 仍为 null**；本轮可验证另存的 prepare 环境锚、host artifact、精确 image、HEAD 和材料绑定，但不能据此宣称 baseline 自身已有环境包 lineage，或取得 typed 训练租约。普通 GPU 诊断须沿用这组精确注册身份；正式训练 actor 接线、资格和租约仍属另一个准入范围。

固定 spec 预算 reset/apply/test 为 300/120/1800 秒；replay 的候选阶段／评分／清理／拉镜像上限为 900/3600/120/1800 秒，manager close 为 300 秒。五行安装约 4.7–5.5 秒、测试约 7.5–10.0 秒，自然完成，未见超时、取消、预算耗尽或资源错误。185 个记录的 Docker 调用退出全 0。10 个候选／grader `rm -f` 调用 `0011/0035/0048/0072/0085/0109/0122/0146/0159/0183` 均成功；manager 的五个 grader create/delete 对应、open 与 cleanup failure 均空，final status 为 `ok/0`。末尾 `0184/0185` 对本 job 标签查询容器和网络均退出 0、stdout/stderr 空，即归档时本 run 零残留。

## 公开 actor 的实际交付与隔离

实际首轮请求 SHA `78229137896bb37226079d7dcc3064c970e5dfb2945a0fc8218444a194c77bf1`，公开 prompt SHA `523d2b1fa94d4db80eb8551ea773a6ec4489c0e05978b496308f6b65e4ae090f`。对原始 bytes 解码后比较，保留题面 CRLF；首轮 user text 与保存的完整 prompt 严格相等，题面和 hints 与原公开 cache／prepared public view 相等。三条命令与[固定公开命令](../cpu_acceptance_20261003/remaining/public_actor_commands/pydantic__pydantic-9066.public_commands.json) 完全一致；实际 trajectory 中三个 Bash 的 quoted command、timeout、返回和 capture 逐条相符，四次请求、四轮回复自然结束，stdout 22222 字节完整、stderr 0、harness 退出 0。

| 命令 | 实际结果 | 验证含义 |
| --- | --- | --- |
| public_identity | rc 0 | 实际断言 UID 54321、Python 3.8.19、core 2.16.3、正确 `/testbed` 导入、baseline 源码 SHA `f5b675891b23ab3ce275db9d30f9a871bb01691bd0f4ce60912e14c71950f16e`、`os.access(..., W_OK)` |
| public_goal | rc 1；`TARGET_EQUALS False` | 原公开 IPv4 默认值被警告并从 schema 排除；末尾是预期的 `PUBLIC_ORIGINAL_TARGET_REPRODUCED` 断言，已复现公开基线问题，不是 actor bringup 失败 |
| public_existing | rc 0；2 passed | 两个已有公开节点 `test_ipv4address_type/test_ipv6address_type` 的小范围开发路径可用 |

隔离结论基于真实 body、mount 和源码数据流共同验证。主机 `load_context` 读取 host grading 是宿主动作；实际 runner 随后仅将 `ctx.rollout_views[task_id]` 转成 `RolloutTaskSpec`，其中 `grading_spec=None`，用公开 prompt 启动 Claude Code。devcheck 只改 spec 的 image 字段，actor 路径没有应用私有 test patch 或调用评分。实际 prelaunch `binds=[]/mounts=[]`，无宿主 private 路径挂载；prepared public view 不含 grading。递归检查四个请求的全部 420 个解码字符串，未见两份私有 patch 原文、新测试节点、控制名、revision 或宿主材料路径；后续请求只回传上述公开命令和实际结果。这里没有仅凭私有函数名未出现就认定隔离。

实际 actor 也绑定相同派生 image 和 base HEAD，资源为 2 CPU／4 GiB／512 pids，UID 54321 无有效 capabilities，NNP 为 1，外部 DNS 与直接 upstream 被拒、只允许 relay。激活解释器与预期前缀一致，可信初始化和 sanitize 成功。镜像初态的 `pdm.lock/pyproject.toml` 两项修改属于已审固定派生构建，不能冒称 worktree 初态干净。公开命令只断言源码可写权限，未实际 edit；没有验证一次完整模型修复、全公开套件或私有正式测试在 actor 内的执行。

actor 命令预算 90/90/180 秒，wall 1800 秒、外层 2400 秒；实际 solve 17.08 秒、无超时。收尾无 agent 进程、容器内无 harness 目录／launcher／done marker；container rm 0、stub rc 0、relay/network failure 和所有本 run 标签残留均空。prelaunch 实际 `ACTIVATION_WRITE=DENIED`；但专门的 Bash `BASH_ENV` 写拒绝命令未执行，原 `bashenv_denied_for_agent=false` 保留，不能改称该专门项目已测。

## 非阻断缺口与可继续范围

冻结 parser 的 **377 个键不是完整 385 节点 states**。每行 raw segment 为 385 个节点：noop 381 PASS/2 FAIL/1 SKIP/1 XFAIL；gold 与 catch 382 PASS/1 FAIL/1 SKIP/1 XFAIL；两正行 383 PASS/1 SKIP/1 XFAIL。377 个 parser 键中仅 370 个是本轮参考 ID，另外 7 个是将 13 个带空格的非参考 PASS 参数名拆碎／合并后的非法条目，例如 `test_tuple[Tuple[str,`、`test_callable_fallback_with_non_serializable_default[Cannot` 的值不是合法状态；1 个 SKIP 与 1 个 XFAIL 未保留。根因仍是共享 `parse_log_pytest_pydantic` 的 `line.split()` 口径，属于既有 6283／5662 问题在本题非参考节点上的表现。当前 370 个参考无此形式，逐项状态完整，故不阻断本题原始 reward 或本轮普通 GPU 探针；在这些含空格 ID 成为参考或要声明全节点结果完整前，需由共享 parser／发布入口维护者修复并单独验证。本报告不改 parser，也不扩大为全 pool 阻断。

本轮未见新增阻断或必要原件缺失。**通过范围是固定 R14 材料的正式 CPU 行为区分、原始评分运输、精确安装／运行身份、完整政策内 baseline 与候选 delta 验证、归档时清理，以及精确 override 的公开控制桩诊断。** 可以据此继续普通 GPU 探针，检验实际模型 actor；GPU 上的真实模型修复质量、typed 训练 actor、训练消费和预算／租约资格仍未验证。基线环境锚 null、共享 parser 非参考缺口、未做专门 BASH_ENV 写拒绝和完整 edit 回合均保留；此次结论不补授训练资格，不重写历史 evidence 或 reward。
