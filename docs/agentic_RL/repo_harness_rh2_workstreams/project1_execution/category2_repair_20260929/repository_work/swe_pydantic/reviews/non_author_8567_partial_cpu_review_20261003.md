# Pydantic 8567：R14 失败轮的非作者 CPU 窄核

2026-10-03。**noop／gold 两行实际验收通过，可复用其原始 0 分与本 job 原件；c3_reorder 未完成评分，保持 `reward=null`。本题 CPU 矩阵未通过，普通 GPU 探针尚未就绪，未授予训练资格。** 失败发生在可信设置之后、候选安装和测试之前的 `control_surface_protect` 调用：300.071 秒超时。本 run 收尾零残留。外层最终异常的“或存在残留”字样不能作为残留证据。

## 审查范围与归档身份

审查者不是材料、runner 或本轮结果作者，但已接触私有测试、候选、参考结果和正式原件，不是 fresh 公开读者。复用[四题材料核查](non_author_remaining_material_review_20261003.md)、[R14 执行入口核查](non_author_remaining_runner_review_20261003.md)、[8567 两份正对照语义意见](non_author_8567_positive_semantics_20261003.md)及已核共享 runner／发布身份。这里只审这轮已完成两行的可复用性、第三行失败阶段和运输／清理；不重做全题材料、旧矩阵或 release 全量审查。没有运行 SSH、Docker、模型、安装、项目 pytest 或作者检查器；本地标准库读取原件并复算 SHA、tar、census、FrozenPatch 和逐 ID 状态。只写本报告和[同名 JSON](non_author_8567_partial_cpu_review_20261003.json)。

| 身份 | 实际绑定 |
| --- | --- |
| job | `pyd8567-formal-20261003001737-r14-b631d`，slot 0，外层返回 1 |
| 发布包／manifest | `cat2-cpu-r2e089092-swe34-dvc-pyd-20261003-v1` / `51b833975be2c3354be45b731552235a33070315f0039c8e6f54987de95f6ca8` |
| runner／输入 SHA | `b127f7309ffae3eae2bbe834c595f846104406e2f858b8073ff2182d0a2ce3c5` / `bea70edd55d2a316b5d92fde1a3a894e9c79363a168e2cd92c7de2d40b83ac1b` |
| revision | `pyd8567-order-old-behavior-v5`；[revision.json](../tasks/pydantic__pydantic-8567/revision.json) SHA `22636f9481cc93a112a768043a21cc8d9d5ae8abaf6be1fffdc96a3aa870b81a` |
| 原件／tar | 375 文件；tar SHA `5f1fa451cbbb80f809bfcf92e9f581d9c9ca5915d5aa50151afa1f7ddb79e09c` |
| 材料身份 | `sha256:79fdb8c6fb5328a023a3f1b5ff2ade9e6fa405aec636d42755783bbb36546d0d` |
| 公开 bundle | `sha256:f01b3794148642ee4d987fdb2e57ec142f19080378c9ced0221290542149379f` |
| prepare 环境锚 | `sha256:8d64c28668f711aa8ab86fbe1bfe10ff3a24b4afc5c2a3001e8b43b8e3bcfb8d` |
| base HEAD | `8060fa1cff965850e5e08a67ca73d5272dcdcf9f` |
| 实际派生 image | `sha256:bc5d796fe30c9c0150a1c15c25347a98f0a1f25bf5f8d9cb098756b38b3c2b74` |

原件根：`runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_v2/outputs/<job>/`，控制原件在同根的 `jobs/swe_pydantic/<job>/`。按 [remaining/results.json](../cpu_acceptance_20261003/remaining/results.json) 独立核完 375 文件的路径、字节数和 SHA；tar 精确含相同 375 个普通文件，每个成员实际 payload 相符，无缺项或多项。没有用作者 `checks`／wrapper `passed` 代替实际验收。

## noop／gold 可复用的实际结果

两行参考均为 **1 旧 F2P + 1 新 F2P + 158 旧 P2P + 2 新 P2P = 162**。原始日志、AST 提取的冻结 Pydantic parser、逐参考状态与原 report／四分区结果逐项一致，无参考缺失、跳过或未归账。两行完整采集 168 个实际测试节点，所有未列为参考的六个节点 PASS。

| 候选 | 原 reward | 旧 F2P | 新 F2P | 旧 P2P | 新 P2P | 测试退出 | 可复用 |
| --- | ---: | --- | --- | --- | --- | ---: | --- |
| noop | 0 | FAIL | FAIL | 158/158 PASS | 2/2 PASS | 1 | 是，原始负对照结果 |
| gold | 0 | FAIL | FAIL | 158/158 PASS | 2/2 FAIL | 1 | 是，原始负对照结果 |
| c3_reorder | null | 未执行 | 未执行 | 未执行 | 未执行 | 无 | 无候选结果；需补验 |

noop 的旧 `test_plain_validator_plain_serializer` 在 `test_validators.py:2827` 得到 `True`，断言其为 `str` 失败；新增未知类型双顺序节点在 `:2908` 得到 `Unsupported` 实例，预期 `'custom!'` 失败。这是 PlainValidator 取代内层 handler 后 serializer 丢失的普通行为失败。

gold 的 `functional_validators.py:156` 调用本应被取代的 `handler(source_type)`：旧 F2P 在 `:2860`、新增 F2P 在 `:2900` 构建未知类型模型时触发 `PydanticSchemaGenerationError`；新增两个 P2P 分别在 `:2916` 触发未定义内层前向引用的 `PydanticUserError`，在 `:2925` 构建模型时触发 Python <3.12 对 `typing.TypedDict` 内层 schema 的错误。四个失败均是范围内普通行为失败，158 个旧 P2P 通过。这里保存金标候选在当前扩展材料下的实际 0 分，不把它称为正对照或把异常改归 infra。

两份日志各有唯一真实测试开始／结束标记，大小／SHA 与 ledger 和 report 一致：noop 80505 字节、SHA `7910307d281f83cb83d81ff769ac2d472af0f9dffb212e7a51b6472352c0b412`；gold 91682 字节、SHA `7176bb10825fe36106526040d95e3249e333adae5f7751e1dfb58375f812f2cf`。report 都是 `unresolved/tests_failed`、`swe_f2p_p2p/binary_v1`，infra detail 和 execution failure stage 为空；没有 collection error 或半截测试段。

安装实际全部返回 0：候选 prerequisite 原 stdin SHA `69f723c29108c52e3cea16130b8957922b825a066c71e54f017841c164040eb4`、执行 UID／Python／core 和 wheel 约束一致，原 stdout 完成标记为 `RH2_PYD_FIXED_OFFLINE_PREREQUISITE_OK=1`。editable 安装、测试依赖安装完成，未见行首安装失败标记；candidate exec 返回 0，安装未跳过，测试退出 1 后仍完整报告。七个保存脚本 SHA 与固定 spec 相等，实际 trusted setup 三次 stdin、两次 candidate test stdin 与保存字节一致，runner 前后摘要未变。

两行实际导入审计的原 Docker stdout 与保存的 supplemental observation 完全相等：UID **54322**、Python **3.8.19**、解释器 `/opt/miniconda3/envs/testbed/bin/python`、core **2.15.0**，三个源码模块均导入 `/testbed`，文件 SHA 分别与登记候选及运输后源码相等。有效 `tests/test_validators.py` SHA `dbe96a1fc7ce78c9fb1453e5eb2481f381d665f99042d282d1c525edf6ed6e0c`，root 所有、执行 UID 不可写；effective patch SHA `a1ed762e8f64ddaa9654c2281e66e7be993de5b6b13a27ee04e8cf3387e5bfc6`。

两行保护控制面完成但耗时明显：实际调用 `0025` 182.027 秒、`0062` 147.166 秒，均输出 `RH2_PROTECT_OK=1`；第三行调用同字节脚本超时，见下一节。不能因前两行保护较慢而否定其已完成的安装／行为证据，也不能以此定位第三行的具体卡点。

## c3_reorder 的实际失败阶段

c3 的 patch SHA `221bbe05b331ff83740ba64eff3a91666c5eb0b2062e80b1fa3c4e75721f86a1`、FrozenPatch、投影、delta 注入和 fresh grader 基线均核对通过。trusted setup 调用 `0097` 返回 0，实际 `RH2_SETUP_APPLY_RC=0/RH2_SETUP_RESTORED=1/RH2_SETUP_OK=1`，有效测试 patch 已应用。随后 `0099` 执行 `grader-protect-control-surface v1`，开始时间 1790987139.8226542、结束时间 1790987439.8939154，差 **300.071261 秒**。

该调用目录实际只有 `call.json`，无 `exit_code` 字段、无 stdout／stderr 文件。不能填造退出码或证明脚本停在某条 `chown`／`chmod`。原 report 为 `failed_to_grade/infra_failure/reward=null`，detail 为 `grading_control_surface_protect_timeout_after_300s`。ledger 的 install/test/observations、diagnostic 的 candidate prerequisite/control surface 都为 null；原日志没有安装／测试开始标记，没有正式测试 segment。其 49419 字节日志和 SHA `3d3f1484486321103d1393a9ddbb2de1321b94d0406fe7d487e1ce62128bf2c9` 是已归档的失败阶段日志，`log.partial=false` 不等于测试已完整执行。

原 report 的 `execution_failure_stage` 仍为 null，故本报告单独记录**从原调用确定的 observed stage**，不回写契约字段。c3 的正式 162 个参考完全未执行，不能记模型 0 分、普通行为失败或正对照失败。既有正对照语义意见继续保留，其本轮完整运行验收仍缺。

实际后续资源采集 `0101` 的 memory events 全 0、`oom_kill=0`、pids `max=0`，`0102` inspect OOMKilled 为 false。该证据排除已记录的 OOM kill／pids-limit 事件；不排除宿主 CPU、I/O 或其它等待，也不证明某种共享资源原因。原件缺失 0099 streams，当前不能进一步定位。共享资源处理已按父线程交发布维护方；本审查未自行修改保护脚本、超时、资源或评分语义。

## 完整 baseline、运输与零残留

三份 FULL baseline 均含 **458 项政策内对象**，canonical digest `sha256:eb494e7682db99522d57c38a96dc78b9469c0c6cbc36e33cdb811b1f25fc2d64`，环境包字段仍为 null。独立复算所有 baseline／FrozenPatch／projection 的 canonical 摘要、task/public/image/HEAD/physical attempt/rollout execution 身份，核候选初态、候选应用后和 fresh grader 应用 delta 前的完整 census，共 **九份**：每份 458 项路径、类型、模式和内容 SHA 全等，并复算 25 项政策排除对象的摘要。c3 的 census 完整不等于后续保护／安装／测试已经完成。

noop 空 delta；gold 仅修改 `pydantic/functional_validators.py`，c3 仅修改 `pydantic/_internal/_generate_schema.py`，其余 457 项保持基线。两个非空候选的实际 patch stdin、原候选 base64 导出 bytes、FrozenPatch content digest、fresh grader 注入 stdin 一致；前两行导入探针再次确认实际源码。c3 已运输源码身份可核，但没有测试阶段的导入／core／UID 审计，不外推该项通过。完整基线依据逐对象 census 与摘要；没有声称额外保存全基线 payload tar 或测试后完整 census。

六个实际 run 参数绑定固定派生 image，全部 `--network none`、2 CPU、4 GiB、512 pids；前两行实际 cgroup 同为 `200000 100000/4294967296/512`。spec reset/apply/test 预算为 300/120/1800 秒，replay 候选阶段／评分／清理／镜像预算 900/3600/120/1800 秒，manager close 为 300 秒。0099 触及保护阶段固定 300 秒上限，不能称整轮预算通过。

105 个调用中 104 个有实际退出 0，0099 没有返回码／streams。六个删除 `0011/0035/0048/0072/0085/0103` 全部退出 0、stderr 空；对应三个候选和三个 grader。manager close 记录三个 grader create/delete 对应，containers_open、supply_open、cleanup_failures 空。末尾 `0104/0105` 明确用本 job 的 run 标签查询容器／网络，实际 rc 0、stdout/stderr 全空，即**归档时本 run 零残留**。

首个 wrapper 异常为 `validate()` 的“真实测试标记缺失”，因为 c3 在测试前已 infra 失败。finally 用 `end['exit_code']==0 and ...` 判断；aborted 的 final status 返回 4，即使所有 residual 查询为空，仍触发“收尾异常或存在本run残留”。原 stderr 保留两个异常链。最终措辞掩盖了前因，但清理已实际成功；不得把 exit 4 解释为四个残留或删除失败。

## 可复用条件、缺口与后续范围

同 release／manifest、同字节 runner、同 revision／有效测试／材料／安装／精确 image／spec 的补验，可以直接保留 **noop／gold 两行本 job 的原始证据与 0 分**，不重跑，不移记为新 job 结果。新单独输入只选择失败的 c3 和原计划尚未运行的六行，应另记 input SHA／新 job；原失败工件、null 和错误链留存。新的固定输入尚未在本报告核查，后续静态意见不能倒写成已完成。本报告没有运行或创建补验输入。

未运行六行是 `upstream261/ok_post_attach/bad_nonvalidators_after_pv/c3_serpass/rv_ser_to_end/n_python_only`。c3 与两份正对照的完整 162 参考结果仍缺，公开 actor 本轮交付／导入／开发诊断也不在这轮原件中；不得据两行负对照签发全题 CPU 或普通 GPU 就绪。

共享 parser 口径继续保留：**168 个 parser 键不等于 168 个合法完整 states**。162 个参考均准确，六个带空格的非参考 PASS 参数 ID 被截断，值为 `input_value='123',`，不是合法状态。未影响这两行参考或原分；在这些 ID 成为参考／声明完整全节点状态前，需共享 parser 维护方修复并单独验。不是本题新增的全 pool 阻断。

baseline 环境锚 null、私有上下文暴露和控制桩／typed 训练租约边界沿已有意见保留。**本窄核完成的是两行复用、第三行 infra 归因和零残留确认；阻断仍是本轮完整矩阵及公开 actor 证据缺失。** 不改历史分数，不授训练资格，不把超时推广成材料或模型语义失败。
