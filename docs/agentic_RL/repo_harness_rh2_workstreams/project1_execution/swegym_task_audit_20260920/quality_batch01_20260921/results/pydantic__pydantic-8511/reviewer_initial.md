# pydantic__pydantic-8511 — 独立初判（封存）

2026-09-21。角色：独立 reviewer；第一阶段，尚未读本包任一题其他角色结论。仅静态阅读、JSON/散列核验；未导入或执行题目代码，未安装、启动 Docker/SSH/模型，未执行新反例。用途为 development_diagnostic，scope=static_review；本记录不等于训练/正式评测批准或 actor 已验。

**初判。** 公开要求清楚：用 `pydantic.dataclasses.Field(repr=False)` 声明的字段应像 `dataclasses.field(repr=False)` 一样退出实例 repr，同时普通字段保持可见。私有 F2P 与这个核心目标相符，原始 noop 日志也在相应断言失败。gold 在 stdlib dataclass 生成方法之前传递 repr 的路线合理，未从已读源码和既有运行中发现原例必然失败或明确误拒合理实现的证据。但只测隐藏字段，不保护 `Field()` / `Field(repr=True)` 的可见性；现有真实运行仅覆盖 Python 3.8，不能证明原例的 3.11 或 gold 改动的 3.10+ 分支。本题可以保留为静态诊断候选，仍为 needs_review；优先做有明确判别力的 repr 正/负对照，再补 actor 条件。不能仅因 gold 得分 1 判质量通过。

## 路径、身份及暴露

- 权威根 `R=${REPO_ROOT}`。
- `P=R/runs/swegym_quality_batch01_20260921_v2/public/pydantic__pydantic-8511`；`D=R/runs/swegym_quality_batch01_20260921_v2/private/pydantic__pydantic-8511`。
- `L=R/runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-8511`。
- 已读共用 reviewer 卡、quality_review_protocol_20260920.md、actor_environment_card.md、record_template.md；另读 verification-before-completion 技能，仅用于文件封存核验。
- 已读 P 中题面、bundle、base_identity、environment_brief；D 中 test.patch、gold.patch、grading/validation/source_refs/run_refs、environment_record 的环境/运行元数据。后者含 `verified_environment_pair` 和 gold/noop 报告及 analysis/history 路径，属于已暴露内容；未沿任何 analysis/history 链接读取旧汇总。
- 已读指定 gold/noop 原始日志的安装、测试恢复、实际执行、失败/结果段和两份 ledger 第 1 行，以及 gold recipe.json / eval_script.after.sh。未读 public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json、任何 review.md、质量 history、manifest、主计划、method_adjustments 或其他角色结论。目录列表只用于定位允许文件，不以文件名推断结论。
- base 为 `e4fa099d5adde70acc80238ff810c87a5cec7ebf`，树 `f6b994800d90c9fd0671ac000b4aa5cfaa9a52f7`。bundle、grading、base_identity 的 commit 一致；test.patch/gold.patch 与各自 JSON 字符串逐字一致；gold SHA256 符合 validation。两原始日志散列均与 run_refs 一致。
- 题面报告用户环境 2.1.1 / core 2.4.0 / Python 3.11.4；任务 base 是 2.6.0a1 / core 2.14.5，grading 指定 Python 3.8。这是用户报告与修复基线差异，不能单凭差异判材料错配；原始 noop 证实核心问题在所评分基线仍存在。

## 需求—断言和执行映射

| 公开要求或合理回归 | 原件依据 | 测试及逐条断言 | 判定和证据范围 |
| --- | --- | --- | --- |
| 关闭字段 repr，同时保留普通字段 | P/user_prompt.txt 原例；base/pydantic/fields.py:201、670；dataclasses.py:208–220 的 stdlib 生成路径 | 新 `test_repr_false[Field]`：局部类 A，visible/hidden 都是 str；通过关键字构造；断言 visible 的完整字段片段存在、hidden 的完整字段片段不存在 | 唯一 F2P。与需求直接对应；不是 mock 或双方同异常比较。noop 失败、gold 通过。没有完整重跑用户的整数/位置参数原例；仅核源码等价路径。 |
| stdlib field 的既有隐藏语义 | 同题对照类 x；dataclass 的 stdlib 委托接口 | 新 `test_repr_false[field]`：相同两断言 | 是 P2P，gold/noop 都通过。 |
| 两种 Field 构造方式的默认工厂、required 元数据保持 | base/docs/concepts/dataclasses.md:47；base/tests/test_dataclasses.py:519–534 | 修改 `test_default_factory_field[field/Field]`：两个参数化分支都断言 `user.id==123`、新增激活 `user.other=={'John':'Joey'}`，继续断言 id required、默认值 repr 为 PydanticUndefined、other 非 required、工厂返回字典 | 两个分支均为 P2P，gold/noop 都通过；新默认工厂断言有公开旧行为依据，不是题外新增功能。 |
| `Field()` 以及显式 `Field(repr=True)` 继续可见 | fields.py:201/591 默认 True；docs/concepts/fields.md:515–534（例子是 BaseModel，结合 dataclass 委托/默认行为解释，不单独扩大规格） | 新 repr 测试中 visible_field 没有用 Field；旧文件对实例 repr 没有其它直接断言 | **缺失。** 仅对“应隐藏”分支的验证不能保护正常 Field 的显示。参见后续负对照。 |
| Field 默认值、默认工厂、别名/签名、继承仍正确 | collect_dataclass_fields:281–292 保留/还原 FieldInfo；tests/test_dataclasses.py:1948–1969、2481–2507、2617–2625 | 已读 `test_default_value[1/None]`、`test_default_factory_singleton_field`、`test_schema`、`test_dataclasses_inheritance_default_value_is_not_deleted`、`test_signature`、`test_inherited_dataclass_signature`、`test_alias_with_dashes` | 相关分支在 168 P2P 中且日志通过；P2P 不覆盖这些组合与 repr=False 同时使用。不能用这些测试证明所有 repr 组合。 |
| kw_only、slots 和 Python 版本兼容性 | dataclasses.py:144–167；旧测试 1622–1693、2301 起；pyproject.toml:64 支持 >=3.8 | 原有 `test_kw_only`、`test_kw_only_subclass`、4 个 inheritance 组合、4 个 slots 组合 | gold/noop 日志均 SKIPPED；也不在评分参考中。`test_dataclasses_with_slots_and_default` 虽在 P2P 且通过，但 3.8 下 slots 参数不进入 stdlib，不能作为 3.10+ slots 覆盖。 |
| Annotated 字段声明、ClassVar/InitVar 等不受无关损坏 | _fields.py:267–287、fields.py:340–372；旧测试 617–670、2395–2440 | 已读 InitVar/derived/post-init/ClassVar、Annotated gt 校验、组合声明测试及 dataclass_decorators helper | 是相关类型/调用链抽查，不是所有组合穷举。Annotated 中的 repr=False 无专门测试；gold 只检查类属性中的 FieldInfo，因此没有属性值的 Annotated 情形不在其处理路径，是否属于本题必修范围应另行界定，暂不据此宣布 gold 错误。 |

新增/修改测试没有专用 fixture；已读文件 imports、参数化构造器，`tests/conftest.py:46–50` 的唯一 session autouse 仅设置错误 URL 环境变量。默认工厂 helper 是测试内无参 lambda。`dataclass_decorators` 位于新 repr 测试之后，不是其 helper；为相关继承/组合 P2P 阅读了完整定义（1650–1675）。新增断言未要求 gold 私有 helper 名、特定算法或函数调用顺序。repr 字段片段沿 stdlib 表示格式，且未钉死局部类 qualname，未发现它凭空排斥一条遵循 dataclass repr 的合理修法。

合理非 gold 路线：保留原 kw_only 逻辑，仅在 `FieldInfo.repr` 为 False 的字段上创建 stdlib field 并保留必要 kw_only/default，而非包装所有 FieldInfo；或在建立 dataclass 字段元数据阶段正确传递 repr。现有测试不限制必须采用 gold 的全部包装方式。此路线仅为静态可行性判断，未编写/运行候选补丁。

## 八方面覆盖与未查

| 方面 | 本次实际检查 | 限度/保留项 |
| --- | --- | --- |
| 公开需求 | 完整题面、hints、环境说明；dataclass/Field 文档及签名 | user_prompt 是静态渲染；hints 是否进实际消息尚未核。公开目标不依赖读隐藏测试。 |
| 材料与初始问题 | 精确 base 元数据、两补丁、grading/validation 一致性；base make_pydantic_fields_compatible 的版本分支；noop 实际失败 | 未执行原例；未重新算整树对象 ID。base 无 .git，真实镜像可见祖先/资产未查。 |
| 测试与要求 | 所有新增/修改断言、唯一 F2P、168 P2P 名单及日志状态逐条核对；上表相关 P2P 测试体 | 未读 168 项每个无关测试体；明确漏掉 Field 的默认/显式 True repr 回归，原例 3.11/位置参数未直接覆盖。 |
| 误拒合理解 | 测试调用/断言、正常 stdlib repr 格式、非 gold 路线 | 无实证误拒；未穷举合法替代实现，也未执行替代解。 |
| 回归与 gold | gold 全部改动；public dataclass→stdlib→complete_dataclass→collect_dataclass_fields→FieldInfo 传播；默认、工厂、继承、Annotated、ClassVar/InitVar/签名 | 未发现已证实 gold 错误；True、default/factory+False、继承+False、Annotated repr 等组合及 Python 3.10+ 未执行。 |
| 开发条件 | pyproject/Makefile、测试 imports、recipe 和安装日志；核心包与测试依赖 | grader 已验不等于 actor 可用；候选派生镜像、agent shell 激活/PATH/写权限及实际源码导入需 CPU 补验。 |
| 交付与评分边界 | test.patch 只改 tests/test_dataclasses.py；gold 只改 pydantic/dataclasses.py；ledger projection 包含该源文件且无忽略；原日志恢复并重打官方测试 | 当前材料没有合法修复必改测试文件的证据。没有复核整个平台 parser/隔离；实际 actor 输入可见性和答案泄漏未验。 |
| 题目关系与用途 | 当前题版本/公开 URL/暴露已记录；本包按顺序先审本题 | 尚未读 5706，不能判重复题/补丁派生；未查全题库。无模型能力、成本、训练价值结论。 |

## 原始运行证据的边界

`L/gold/ledger.jsonl:1` 和 `L/noop/ledger.jsonl:1` 是 **2026-09-19 真实 RH2 评分重放原件**；本次仅重读。两者是 `pydantic-install-v1` 的本地派生镜像 `sha256:4c4a01e8ed281b10ab94e9f37f7a02f33e2b0b9b1cefba4d72a253a394ce94d5`，不是 public 镜像 digest 本身；user=`rh2grader`、uid=54322、deny_all、2 CPU/4 GiB、可写解释器前缀 `/opt/miniconda3/envs/testbed`。ledger 记录目标包来自 `/testbed/pydantic/__init__.py`、版本 2.6.0a1，candidate projection 只含 `pydantic/dataclasses.py`（noop 空）。

- gold 日志 `evallog_replay-er19-pyd1-pydanti_cb903f4a.eval.log:143` 对应指定 base；456–465 的初态环境差异在 pyproject 增加 pre-commit，另有 pdm.lock 差异。不能把此运行说成精确 base 无环境改动。469–508 恢复并应用官方测试；646–682 editable 安装成功，核心依赖 2.14.5；738 的真实命令为 `pytest ... tests/test_dataclasses.py`；831–832 两个 repr 测试通过；927–937 为 169 passed / 11 skipped、test rc 0。
- noop 日志 `evallog_replay-er19-pyd1-pydanti_8ae8a3eb.eval.log:677` 使用同文件命令；770 与868–874 显示隐藏字段仍出现的真实失败；884–894 为 168 passed / 1 failed / 11 skipped、test rc 1。
- 对每个 reference ID 读取原始日志结果：gold F2P 1/1、P2P 168/168；noop F2P 0/1、P2P 168/168，和两行 ledger 一致。环境记录是二次元数据，结论以对应原件为依据。
- `L/gold/recipe/recipe.json` 将原 `pdm add pre-commit; make install` 改为候选 editable install，加从 pyproject testing/testing-extra 读取依赖；eval_script.after.sh 与实际命令对应。安装依赖由本地 `/opt/rh2/build-wheels` 支持；不据此假定 actor 可以联网或重用 grader 的前缀写权限。
- 参考集（冻结 F2P/P2P）是评分范围，不是全部 API 回归标准。历史实际运行、冻结参考定义和本次静态推断以上分别说明；没有当前 CPU 或真实模型执行。

## 最小后续实验及开发需求

**唯一优先质量实验（未执行）：** 以同一 base/测试/recipe 对比 gold 与一个只把所有 FieldInfo 包装为 `dataclasses.field(default=field_value, repr=False, ...)` 的过度修复。保留 kw_only 等其它行为，避免凭空篡改测试。先运行公开原例及一个类中同时使用 `Field()`、`Field(repr=True)`、`Field(repr=False)` 的正常 repr 对照，再运行相同 RH2 reference。如果错误候选得分 1 但前两个 Field 消失，即实证一条有公开旧行为依据的错误回归漏测；若其因已有 P2P 失败，记录具体保护断言并撤回“可能漏评分”推断。该实验也以 gold 作为正确对照，但不预定它所有扩展组合必通过。

后续 actor 最小验收不要求隐藏测试：在拟使用的正式 agent/54321 工具 shell 打印 `id`、cwd、`sys.executable`、pydantic/core 版本和来源；运行题面原例及公开 `tests/test_dataclasses.py -k 'default_factory_field or signature or dataclasses_inheritance_default_value_is_not_deleted'`。用临时公开复现检查 Field 的 True/False、default/default_factory、位置/关键字构造；Python 3.11 下另跑公开 kw_only/slots 测试，区分原例版本验证与现有 3.8 评分。所有命令尚未执行。

| 需要的操作/资产 | 公开依据 | 现有证据与缺口 | 最小确认及预期 |
| --- | --- | --- | --- |
| 定位并修改 Python 源码 | dataclasses.py:147/208；字段定义 fields.py | 已可定位；gold 源文件已被历史 projection 消费 | actor 从 /testbed 导入；临时改动后公开复现能看到行为变化，交付仅源文件即可 |
| core 与测试工具可导入 | pyproject.toml:64–68、97–115；测试 imports | grader 3.8 + core2.14.5 可用；actor 未验 | 上述解释器/包来源检查；公开窄测完成而非导入失败 |
| 安装/构建能力 | pyproject 与 recipe；Makefile install 会涉及更多开发组和 hooks | 修复本身不新增依赖、不需重编 core；若必须重装，wheel/build backend 及权限待验 | 预置已满足的 wheel/依赖通常足够；不要把 make install 的可联网全组操作当本题必需 |
| 外部资产/服务 | 题面纯类定义/构造/repr；相关测试为内存数据 | 已读范围不需要权重、数据集、远端服务 | 保持离线公开复现即可；无运行期公网要求 |
| 文件恢复边界 | eval_script 恢复 tests/test_dataclasses.py；projection 源文件可见 | 不需要改受恢复测试文件；hints 的泛化“所有测试修改都会恢复”非当前完整机制 | 记录实际提交源码差异及被评分源码来源，不以测试改动求修复 |

本份初判保存后不回写。下一阶段只在协调者统一开放两题结论后另写 review.md。
