# Pydantic8793 下一片：保留 Annotated 外赋默认值

2026-09-30。**输入材料已准备，未实施、未登记激活、未运行新项目测试或评分。** 当前没有新增用户决策事项；根线程复核本材料，等待当前 MONAI CPU 切片收口后，再按既有 D6 授权实施。历史 result 中“当夜未授权”的说法属于09-29原证据，不回写；两道 mypy 之后逐步扩展的授权已有效，本页仍不等于题通过。

最小修订是在原正式受测 `tests/test_json_schema.py` 追加一个普通命名测试，检查 `create_model` 的 Annotated 字段赋予默认值 5 后，省略该字段的模型实例确实取到 5。保留原 **3 F2P＋364 P2P＝367 项参考**，新增 **1 P2P** 后为 **3 F2P＋365 P2P＝368 项参考**。这些数目由原 grading 行实际计算，不是原日志总执行数。

## 为什么不能直接追加两项既有测试参考

已有旧公开测试优先核过，没有先造新补丁：

- 已证回归在 `tests/test_annotated.py::test_annotated[...]` 的两个参数例；原 `test_patch` 和实际正式命令只选择 `tests/test_json_schema.py`。两项旧回归既不在原 364 P2P 中，也没有进入原正式执行。因此 `forced_required` 原得1不是“已执行失败却被忽略”，而是当前正式选择没有覆盖它们。
- 两个参数例的完整 nodeid 包含空格。冻结 Pydantic parser 的 `parse_log_pytest_pydantic` 使用 `line.split()[1]`，两项都会被截为同一个 `tests/test_annotated.py::test_annotated[<lambda>-5-FieldInfo(annotation=int,`。直接登记完整 nodeid 将缺席；登记截断键会碰撞，也无法保证具体参数例的状态。完整名称及逐字符分析保存在 [existing_node_analysis.json](../../../../../../../runs/category2_repair_20260929/swe_materials/pyd8793_next/existing_node_analysis.json)。这只是对既有源码与历史 node 名称的分析，没有重新收集测试或重放整份旧CPU日志。
- 旧两项断言比较精确 `FieldInfo` repr。可以在未来独立处理通用精确参考绑定，但本题的默认值行为已有公开依据和既有行为对照，无需为此扩展公共 parser、使用静默截断别名或增加参数化 repr 约束。
- `test_create_model_usage` 确实验证普通字段默认值123，但未使用 Annotated；历史同次开发运行包含它且仍通过，不能单独拒绝本错误候选。

因此本片保留原命令和 parser，在已受保护的原文件增加一个不参数化的普通函数。不是把两项旧测试改名，也不把私有 shell 后检当正式评分。

## 公开依据与新增断言

公开规范来自该题精确 base 的 [fields 文档](../../../../../../../runs/category2_repair_20260929/swe_materials/pyd8793_next/source/base/docs/concepts/fields.md)：默认值使字段可省略；41–59行明确 Annotated 可搭配 Field，默认值可以在 Annotated 外赋值，也可在内使用 `default_factory`。公开 [test_annotated](../../../../../../../runs/category2_repair_20260929/swe_materials/pyd8793_next/source/base/tests/test_annotated.py) 16–90行两项参数例要求外赋5保留，公开 [test_create_model_usage](../../../../../../../runs/category2_repair_20260929/swe_materials/pyd8793_next/source/base/tests/test_create_model.py) 38–46行验证动态模型省略有默认值的字段。原 [公开题面](../../../../../../../runs/category2_repair_20260929/swe_materials/pyd8793_next/source/original_public.json) 使用同一 `create_model`＋Annotated API要求 Ellipsis 表示必填；修复该路径不能顺便清掉具体默认值。**gold 只作为正对照，不是本断言的公开规范来源。**

候选新增函数为：

```python
def test_create_model_annotated_preserves_assigned_default() -> None:
    """Annotated metadata must preserve the assigned default in create_model."""
    from pydantic import create_model

    Model = create_model('Defaults', x=(Annotated[int, Field(description='x')], 5))

    assert Model().x == 5
    assert not Model.model_fields['x'].is_required()
```

`Model().x == 5` 是决定性实际行为断言，`is_required()` 只作公共字段 API 的辅助检查。没有要求内部 helper、`_attributes_set`、字典结构、repr 或 gold 算法。内层 `Field(3)` 与外层 Ellipsis 的优先级争议继续在范围外。

既有 CPU29 私有 `public_defaults` 使用相同 `create_model('Defaults', x=(Annotated[int, Field(description='x')], 5))`。base/gold 输出 `PUBLIC_DEFAULTS_OK`；同一已导出源码的 `forced_required` 在求 `M().x` 时精确报 x missing ValidationError，已由[独立复核](../../../swegym_cpu_preprobe_20260929/reviews/pydantic8793_result_review.md)确认。故该历史行为支持新断言的预期，但不等于新测试已执行。

同一公开命令还含 `Factory().y == 7`，base/gold通过；错误候选在默认5处先失败，不能宣称其工厂7也已被独立判坏。本片只把已证的默认5列为新增正式P2P，默认工厂保留为已有公开开发控制，不额外扩张 oracle。

## 固定材料与静态核对

完整来源、大小、SHA及候选状态见 [materials_manifest.json](materials_manifest.json)。材料根为 `runs/category2_repair_20260929/swe_materials/pyd8793_next/`：

| 材料 | 用途 |
| --- | --- |
| `original_test.patch` | 原测试补丁逐字节保留。 |
| `extra_tests.patch` | 应用前提为 immutable base 已应用原测试补丁。 |
| `effective_test.patch` | 完整有效补丁候选，直接应用 immutable base。 |
| `references_candidate.json` | 原／新增／有效参考分列，原顺序不变。 |
| `controls/noop.patch`、`gold.patch`、`forced_required.patch` | 空候选、原 validation gold、既有已证错误候选。 |
| `source/base/`、`source/source_*_row.jsonl` | 精确公开基线文件与来源第171行。 |
| `history/` | 旧结果、逐候选正式ledger／log／frozen patch与公开开发行为的逐字节副本，不改历史原件。 |
| `environment/`、`environment_reuse.json` | 固定镜像、8wheel恢复与候选安装配方。 |
| `patch_commands.json`、`static_checks.json`、`inspection/` | 本轮新增材料的本机Git／AST核对证据；不是actor工作区。 |

绑定 base `832225b90672c68e2d4067bd0ffecf834d62b48b`、tree `11e57c7275fdd5baa73461a82eeee828ea47e522`。`s2/ingest` 四份原件第171行与既有 frozen public/grading 对象精确相同；原 `test_patch` 字节相同，gold与原 validation `golden_patch` 相同。所有原参考去重、F2P/P2P不重叠；新增节点唯一、无参数展开。

本轮只新增输入验证：5次 `git apply --check` 通过，两条应用路线的完整文件实物相等；去掉唯一新增函数后的 AST 与原补丁结果相等。gold/forced_required 在本地静态副本应用后的 `pydantic/fields.py` SHA 分别为 `d813d8cc…9530f1`／`5e466533…1b01c5`，与旧正式 frozen源码一致。没有 import pydantic、pytest collection、项目测试、容器、SSH、安装或模型调用，也没有重跑旧三方CPU或静态角色审查链。

## 环境与安装可复用到哪里

固定源镜像仍为 `xingyaoww/sweb.eval.x86_64.pydantic_s_pydantic-8793@sha256:bdd9a2ddbca3a265f115d7f704eff78d39282f38d5be34bb8e338b717cc41b5c`。CPU29复用09-19安装修复，但仅加入8个公开wheel，排除了1021-byte私有canary；因此09-19九wheel镜像ID不能冒充09-29八wheel镜像ID。

CPU29实际源配置ID为 `sha256:e61eaef6…382162`，派生 grader ID为 `sha256:039bc9c3…f671e`。三方均离线安装成功，从 `/testbed/pydantic` 加载；actor是CPython3.8.19、core2.16.2。候选安装仍应从当前 `pyproject.toml` 消费 testing／testing-extra并editable安装当前源码，不能升级pydantic或core替代问题修复。初态 `pdm.lock`／`pyproject.toml` 已有改动，不称pristine；新机记录实际diff及SHA。

本材料包有Dockerfile、fetch脚本、8份公开wheel的精确URL／SHA／长度，共272,014字节，以及历史实际下载／build证据；**当前题级输入包没有wheel原字节或固定源OCI层归档**。缺件和可追溯下载来源逐项列于 [environment_reuse.json](../../../../../../../runs/category2_repair_20260929/swe_materials/pyd8793_next/environment_reuse.json)，未检查外部主机缓存，不声称全机不存在。registry今日可取性未检查；新机按digest拉取、逐wheel核内容并记录新派生ID后，才确认恢复适用性。CC运行时与公共relay供应由root负责，不把历史安装记录当新机资产。

旧三方2CPU／4GiB、deny_all；trusted setup约282.232／216.979／189.364秒，实际测试9.088／5.838／5.799秒。旧candidate预算900秒、grading deadline3600秒；它们是旧真实配置而非新机最低要求。新profile与全部有效timeout另登记。旧 `resource_facts=null` 仍为未知。

## 后续最小机制与有限验收

现已实施的 MONAI `replace_test_patch_append_p2p` 对任务、路径和新增节点采用精确白名单。Pydantic本片不需要新操作、题面替换、自由命令或公共parser改动；实施时只需：

1. 把本题精确identity／`tests/test_json_schema.py`／普通节点列入同一受信操作登记，原／有效补丁SHA及base文件SHA绑定；扩展目前MONAI限定的schema／registry白名单。Pydantic另列固定登记SHA，重放时按确切任务取所属登记pin，保留mypy及MONAI各自登记和既有材料身份；无需动态注册平台。原登记与原产物保留，新的注册及产物另存，不把本准备manifest当运行配置。
2. 从原件重放新包，恢复原 `test_patch` 后核parent digest；命令仍由vendor派生为 `pytest -rA --tb=short -vv -o console_output_style=classic --no-header tests/test_json_schema.py`。该完整文件继续恢复、核SHA、保护；候选不能重写测试。
3. 共用既有actor／replay builder、材料／环境身份、旧资格失效和原／新增分区；保持完整baseline硬比较、奖励及安全边界。MONAI白名单扩展并不证明Pydantic新材料已具备资格。

最少做一次新固定材料版三方正式评分：

| 候选 | 原3 F2P | 原364 P2P | 新默认5 P2P | 预期联合结果，尚未执行 |
| --- | --- | --- | --- | --- |
| noop | 3失败 | 364通过 | 通过 | reward0，参考368项完整 |
| gold | 3通过 | 364通过 | 通过 | reward1，参考368项完整 |
| forced_required | 3通过 | 364通过 | 实例x missing，目标断言失败 | reward0，参考368项完整 |

每行核真实368个精确参考、原／新增分区、无参考missing／skip、完整测试退出、目标失败栈、安装每步、实际候选源码、受保护文件字节／root属主／不可写、完整baseline、两层清理。原完整日志另有非参考skip/xfail，不能把非参考状态混入参考分母，也不能把collection失败当错解被拒。

在同一新材料版补一次真实CC固定命令actor及原始冻结工件送fresh grader直评，证明本题三端初始化与baseline一致；开发命令可复用已有公开清单，不把新私有测试/gold发给actor。旧actor证据证明公开开发通道可用，仍未证明正式题面实际交付，也不能给旧工件换材料标签、重算baseline替代原样直评。该项共3次replay＋1次原工件完整评分，不是模型样本。

非作者复核代码／材料和新证据后，再交题级转类。公共评分可信性、正常模型比较、训练准入仍由对应线程确认。本材料准备没有核销这些条件。
