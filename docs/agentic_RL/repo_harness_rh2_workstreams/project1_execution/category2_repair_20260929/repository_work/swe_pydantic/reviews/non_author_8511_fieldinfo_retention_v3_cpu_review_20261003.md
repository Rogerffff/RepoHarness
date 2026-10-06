# 8511 FieldInfo 保留行为 v3：非作者实际 CPU 窄核

日期：2026-10-03。作业：`pyd8511-retention-20261003T153716Z-v3`。

**本次诊断执行与原件核收通过。baseline 四项 PASS、narrow 四项 PASS、原 Qwen 四项 FAIL。四项均为原基线已能满足的行为；原 Qwen 丢弃 FieldInfo 的静态缺口已成为运行实证，属于候选回归。** 可以据此起草最小私有 P2P 保留组合，并走后续正常材料、发布与正式 CPU 验收。本次没有运行新177参考矩阵，也没有完整 actor 验收；原173参考、raw1、原 FP 和旧失败记录均保持。完整材料覆盖尚不接受，不授予训练资格。

`cpu_review_passed=true` 只指本次三候选、四项直接行为诊断的证据核收。同名 [JSON](../../../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_pydantic/reviews/non_author_8511_fieldinfo_retention_v3_cpu_review_20261003.json)列出148成员逐件 SHA/大小、38条实际命令、三个 CID 与具体限制。

## 1. 身份、范围和独立核查方法

审查者不是本轮材料、诊断 runner 或候选作者。已接触原私有材料、R14 CPU 原件和两模型 GPU 轨迹，不是 fresh 公开读者。复用刚完成的 v3 静态窄核及[原两臂执行与语义审查](../../../../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_pydantic/reviews/non_author_8511_8567_qwen_first10_execution_semantic_review_20261003.md)；没有重读旧209/204件或扩大到其它题。

只用本地标准库读已同步原件、核 tar/JSON/SHA、解析生成的 stdin，并把固定 narrow diff 作为数据严格逐 hunk 应用。没有 SSH、Docker、安装、项目测试、模型、作者 helper 或 board 操作；只写本报告及同名 JSON。

权威原件为 [v3 evidence 根](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/8511_retention_original_evidence_v3)。独立复算归档 SHA `6ff4a4b36934ebf661a761213fbd99280105c9c6ed867dbd12a0969d654bf177`，大小3,195,457B；其中148个文件、解压后内容共8,700,873B，与本地逐件路径及字节一致。读取全部实际 `exec.json`、stdout/stderr/stdin、输入、结果、slot 和 PID1 journal，未只采信作者汇总。

固定输入 SHA：`739d5c0aa889c512e6c996a67ac65b9422a21fbe2469c9855b1302badc2eb27a`；
runner SHA：`9f351c27b973df9d45054aeb26de2c90d9ed7b7cc5df25c28f8f1b0b2fb769d7`；
probe SHA：`7abeb8bec075045bbb37f9409159df837900a2bce537516b88bc98b9efcb0a78`。
[归档 inputs](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/8511_retention_original_evidence_v3/packages/swe_pydantic/fieldinfo_retention_v1/inputs_v3/inputs.json)的九份 payload 大小/SHA 均重算相符，加输入自身共十件。归档 runner/probe 与刚审的冻结本地版本逐字相同。

## 2. 实际四项结果与失败机制

三个容器分别恢复同一完整 baseline，只替换 `pydantic/dataclasses.py` 为其绑定版本。三次实际执行的 [诊断 stdin](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/8511_retention_original_evidence_v3/packages/swe_pydantic/fieldinfo_retention_v1/outputs/pyd8511-retention-20261003T153716Z-v3/qwen_original_retention_probe.stdin)与冻结 probe 逐字相同；不写额外测试文件、不要求 baseline 修好 repr，也不混入多字段排序或默认值校验开关。

| 保留行为 | baseline | narrow | 原 Qwen 的实际结果 |
| --- | --- | --- | --- |
| `Field(default_factory=list, repr=False)` | PASS，两个实例为空且列表独立 | PASS，同样独立 | FAIL，`HiddenFactory()` 报 `ValidationError/missing x`，工厂字段变必填 |
| 上述字段在无新增字段的子类中继承 | PASS，两个 Child 实例独立 | PASS，同样独立 | FAIL，`Child()` 报 `ValidationError/missing x` |
| `Field(default=1, gt=0, repr=False)` | PASS，字符串'2'转为2，显式0报 `greater_than`，位置x、阈值0 | PASS，同样结果 | FAIL，显式0未抛出要求的 ValidationError，诊断随后报 AssertionError |
| `Field(default=1, alias='y', repr=False)` | PASS，`y='2'` 实际成为 `x=2` | PASS，同样结果 | FAIL，`x` 仍为默认1，诊断 AssertionError 的消息为 `1` |

原 stdout：[baseline](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/8511_retention_original_evidence_v3/packages/swe_pydantic/fieldinfo_retention_v1/outputs/pyd8511-retention-20261003T153716Z-v3/baseline_retention_probe.stdout)、[narrow](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/8511_retention_original_evidence_v3/packages/swe_pydantic/fieldinfo_retention_v1/outputs/pyd8511-retention-20261003T153716Z-v3/narrow_retention_probe.stdout)、[原 Qwen](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/8511_retention_original_evidence_v3/packages/swe_pydantic/fieldinfo_retention_v1/outputs/pyd8511-retention-20261003T153716Z-v3/qwen_original_retention_probe.stdout)。前两次 RC0，后一次 RC1；程序逐项捕获并继续，所以四项实际均执行，未由第一项错误遮住后项。三个程序耗时分别0.659、0.606、0.629秒，stderr 均为空。

基线 `collect_dataclass_fields`（`pydantic/_internal/_fields.py:281–287`）检测 `dataclass_field.default` 是否仍为 FieldInfo。保留 FieldInfo 时，`FieldInfo.from_annotated_attribute`（`fields.py:330–337`）保留其配置；普通 dataclasses.Field 则进入另一分支。`_from_dataclass_field`（`fields.py:421–432`）只能从普通 default、default_factory、metadata 和 repr 重建字段。这些基线字节已由本次 [原 baseline tar](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/8511_retention_original_evidence_v3/packages/swe_pydantic/fieldinfo_retention_v1/inputs_v3/baseline.tar)直接核对。

原 Qwen 在 [实际原候选源码](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/8511_retention_original_evidence_v3/packages/swe_pydantic/fieldinfo_retention_v1/inputs_v3/qwen_original_dataclasses.py)中用 `FieldInfo.default` 或 `dataclasses.MISSING` 包装成 stdlib field，没有运输整个 FieldInfo，也没有转移 factory、gt metadata 或 alias。上述实际异常与这条数据流相符；narrow 保留整个 FieldInfo，四项均通过。基线文档 `docs/concepts/dataclasses.md:47` 已说明 Field 支持 factory，同段也展示字段约束；本次 baseline 的四项实际 PASS 提供更直接的行为依据。

因此这四项是原基线既有且需要保持的 PASS 行为，适合作为最小私有 P2P（原基线通过、修复候选仍需保持通过）组合。它们不是本次已经发布的正式参考节点；四项诊断也不足以证明所有 FieldInfo 配置、所有继承形式或其它 Python 版本正确。

## 3. 完整 baseline、候选与执行位恢复

baseline tar SHA `6207027aa65a3caad3ce78cbb4d08081b2f74a56432bbd6b25e91a1062c472d2`，7,075,840B；manifest 文件 SHA `9c61a99b9720ca2d4a1d2ce61c855f05d9839d4de2b5830e96c72fb332837672`。独立枚举452个唯一、安全 regular 成员，逐件内容 SHA 与 Git 执行位均符合 manifest；canonical baseline digest 为 `40135f281c216e76a04de6772eaaadcdfd0b46d949e98c5164f29cba2f454e45`。

三个变体的生产源码 SHA 分别为：

| 变体 | `pydantic/dataclasses.py` SHA |
| --- | --- |
| baseline | `3fd9cc00c536227d63b4232c60e67ce45521b1b7d8473cf7c8bd9866d9a1539f` |
| narrow | `337e4d552b22aef94960740b385c7ca93cd1b09619997e74e4e93da6427190df` |
| 原 Qwen | `161678b86e6cdde428771594d2c5e2d4f1016108a2c9fa9b7d900bc0fb28401d` |

narrow 源码经固定 [narrow.patch](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/8511_retention_original_evidence_v3/packages/swe_pydantic/fieldinfo_retention_v1/inputs_v3/narrow.patch)严格逐 hunk 数据应用，与上传源码一致。[原 FrozenPatch](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/8511_retention_original_evidence_v3/packages/swe_pydantic/fieldinfo_retention_v1/inputs_v3/frozen_patch.json)的唯一 modify/regular/100644 条目 Base64 解码后，与 Qwen 实际写入 stdin 及上述源字节完全相同；canonical FP digest 仍为 `4c305765cca042e14a8b79ebafa304394739f982b0eb68a471a47efbf92b3da1`。

实际恢复 stdin 均先移除自有容器中的旧 /testbed，再解包固定 tar、chown 至54321。随后实际 `restore_frozen_modes` 均以 `--user 54321:54321` 对452个 manifest 路径设置0644/0755，RC0；三份 chmod stdin 的完整字典均独立解析并符合 manifest。候选写入 stdin 解码字节正确。

六份源码身份 stdout（每候选前/后）均报告空 mismatch；各自452个内容 SHA 与布尔执行位完全符合其候选期望，前后逐项相同。五个原可执行文件的执行位均恢复：`build-docs.sh`、`tests/test_fastapi.sh`、`tests/test_pydantic_settings.sh`、`tests/test_validators_dataclass.py`、`update_v1.sh`。可见 [原 Qwen 前身份](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/8511_retention_original_evidence_v3/packages/swe_pydantic/fieldinfo_retention_v1/outputs/pyd8511-retention-20261003T153716Z-v3/qwen_original_source_identity_before.stdout)与[后身份](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/8511_retention_original_evidence_v3/packages/swe_pydantic/fieldinfo_retention_v1/outputs/pyd8511-retention-20261003T153716Z-v3/qwen_original_source_identity_after.stdout)。

这里核收的是冻结政策成员的 SHA/执行位。runner 没有额外对所有非政策文件做容器 census，也没有逐文件输出 UID/type/精确 Unix 权限；不能把这452条扩成全文件系统证明。baseline 的 `environment_package_digest=null` 与 FP 的 `excluded_pathset_changed=true` 均保留。本次只复建原 FP 唯一生产条目，不把旧模型交付历史改为无排除路径变化，不补成 typed 训练资格。

## 4. 实际解释器、权限、镜像和限额

全部实际 identity/probe 为 UID54321、GID54321、Python3.8.19、Pydantic2.6.0a1、core2.14.5，源码导入 `/testbed/pydantic/__init__.py`。未执行安装或重建镜像；使用既有派生镜像：

`sha256:df6c3affb7ea6fd826f44863ec92926f7b52558dd0f1b42e05f97aec9fe8ca68`

base/head 为 `e4fa099d5adde70acc80238ff810c87a5cec7ebf`，与已核原 GPU 身份一致。实际 image inspect 为 linux/amd64，三个容器 inspect 的 Image 均为上述 digest。

创建阶段 user0 仅保留 CHOWN、DAC_OVERRIDE，CapDrop ALL、非 privileged、no-new-privileges；v3没有增添 FOWNER 或任何 capability。六份54321进程状态的 CapEff/CapPrm/CapInh/CapAmb 均0，CapBnd为3，NoNewPrivs=1、Seccomp=2。此处私有 probe 以54321运行是直接诊断安排，不是公开 solver 的隔离验收；本次没有 CC、模型、网关或正式 grader。

实际 inspect 确认 network none、Mounts 空、Binds null、NanoCpus=2,000,000,000、Memory=MemorySwap=4,294,967,296B、PidsLimit512。三个精确 CID/PID 为：

| 变体 | CID | 容器宿主 PID |
| --- | --- | --- |
| baseline | `fae2230e46646729f005fb6e5696597fcc0b87c3be59450de0865ec2c48d0892` | 1133020 |
| narrow | `b9363a3aa0770a0ef16f6540da4cb4652f689a1d6ae6fc55577d9e766c113cb5` | 1133393 |
| 原 Qwen | `8281ddd0cd3bb67a6add1fbbcc6bf4c876565682bf75c3a72ae8e8e6cda4e733` | 1133770 |

创建/start/inspect/copy/restore/chmod/write/前身份/probe/后身份/rm/CID-query 全部实际命令已读；连同全局 image inspect/label-query 共38条，只有预期原 Qwen probe RC1，其余37条 RC0，全部 stderr 空。未见超时、未安装、解释器/导入错误或 infra 异常。Qwen RC1是这四项行为失败，不是新正式模型0分。

## 5. 槽、PID1终态、资源及清理

[slot status](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/8511_retention_original_evidence_v3/jobs/swe_pydantic/pyd8511-retention-20261003T153716Z-v3/status.json)绑定统一 CPU slot0、supervisor PID1132950、child PID1132951，2026-10-03 15:37:16–15:37:27 UTC，finished/RC0。[launch receipt](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/8511_retention_original_evidence_v3/packages/swe_pydantic/fieldinfo_retention_v1/launch_receipt_v3.json)绑定整体 timeout600秒、TERM后20秒强制结束、systemd RuntimeMaxSec660；各行为程序120秒、其它调用30秒。结果记录内部起止为15:37:16.309168至15:37:27.002859，共10.694秒。launch 的 `diagnostics_finished=false` 是派发时字段；不把它当最终状态。

[实际 PID1 journal](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/8511_retention_original_evidence_v3/packages/swe_pydantic/fieldinfo_retention_v1/journal_v3.jsonl)记录同一 unit 和 invocation `e804585040ac405997986faf534d5bb5`；PID1在15:37:27.080572 UTC明确 `Deactivated successfully.`，并记录3.941秒 CPU。终态依据是实际 journal 加 slot RC0，不是已回收 unit 的默认状态。

每个容器5个离散资源样本均绑定其 CID、PID、image 和相应 cgroup，无 sample_error；memory max/oom/oom_kill/oom_group_kill及pids max事件所见均0。采样峰值分别36,175,872 / 36,225,024 / 36,360,192B，pids峰值均8。最大相邻采样间隔约0.55/0.55/0.56秒；行为执行内分别有2/1/2个样本，短阶段与采样首尾未完全覆盖。不能据有限采样宣称连续全过程零瞬时资源事件；实际普通行为异常、全部命令与成功终态足以完成本次归因。

三个实际 CID 均 `rm -f` RC0，stdout 回显对应全CID；各精确CID查询RC0/空，最终唯一job-label查询同样RC0/空。[最终 label 查询](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/8511_retention_original_evidence_v3/packages/swe_pydantic/fieldinfo_retention_v1/outputs/pyd8511-retention-20261003T153716Z-v3/job_cleanup_query.exec.json)与 [结果原件](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/8511_retention_original_evidence_v3/packages/swe_pydantic/fieldinfo_retention_v1/outputs/pyd8511-retention-20261003T153716Z-v3/results.json)相符，本run零残留可核收。范围仅本作业，不外推共享机上其它资源或服务。

## 6. 旧失败记录、结论与后续范围

v1 `pyd8511-retention-20261003T151418Z-v1` 与 v2 `pyd8511-retention-20261003T152527Z-v2` 的真实 slot RC1、`stopped_infra_or_identity_hold` 和零行为执行保留；没有 probe 工件，也没有正式 reward。此前已核其自有CID/label均RC0清空。v2实际 identity stdout只列五个执行位变false，内容SHA相同。v3定向恢复已有效，但“tar先chown后chmod、root缺FOWNER导致属性恢复失败”仍为机制推断，不能因修复成功就断言是唯一已证首因。

**本次没有诊断范围内阻断。** baseline/narrow的四项PASS与Qwen的四项FAIL，在同一精确image/core/source、相同输入程序和资源限制下得到；前后完整452项身份与成功清理排除了此前执行位失真。原 Qwen 的 FieldInfo 信息丢失已获得直接运行支持，原173/raw1的材料覆盖不足仍成立。

支持起草最小私有新增保留组合，并对发布后的新版本执行正常独立材料、固定输入与正式 CPU 验收。公开输入未因此改变；无需新增 solve。草稿或本报告都不等于新177正式矩阵已通过，不回写原173/raw1/FP；后续正式奖励须由其真实新版本作业产生。完整 actor、其它 FieldInfo组合、其它Python版本、typed训练环境资格均不在本次通过范围。

