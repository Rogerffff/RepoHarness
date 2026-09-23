# pydantic__pydantic-5706 — history 前私有分析（封存稿）

2026-09-21。在本题旧调查开放之前形成；保存后不回写。本轮仅静态读取与元数据核验，原始历史 RH2 不等于当前 CPU 或正式 actor 验证。

## 路径、身份、暴露与阅读范围

- `R=${REPO_ROOT}`。
- `P=R/runs/swegym_quality_batch01_20260921_v2/public/pydantic__pydantic-5706`；`Q=R/runs/swegym_quality_batch01_20260921_v2/private/pydantic__pydantic-5706`。
- `O=R/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/pydantic__pydantic-5706`。
- `E=R/runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-5706`。缩写展开后均为绝对路径，源码行号指 `P/base/`。
- 复用 investigator 角色卡明确允许的八方面协议、actor_environment_card、record_template；已读本题封存 `public_read.md`，实际公开 bundle/prompt/base_identity/environment brief、test/gold patches、grading/validation、run_refs、environment_record、原始两角色 ledger/logs 与 gold recipe/after scripts。environment_record 的 checks/status 和 analysis/history 路径名已暴露，没有打开其汇总结论链。未读本题 source_refs/history refs、manifest、主计划、method_adjustments、reviewer结论。
- 同一调查者此前按门完成8511，已见其源码/私有答案/获准历史；这里只复用一般版本知识，未把8511事实当本题证据。本題尚未接触自己的旧调查，不称完全未知Pydantic的盲审。
- base `70e7e99ca1861ad71520cc8fcf1a2fb913abbc10`，tree `cc191fc0e571a936cd3af5e6114c075d862f892f`，300 tracked entries，base_identity记录blob校验真，无.git、symlink/LFS/gitlink；public manifest digest `sha256:480f09d76fedfdb406fc845aab7d5e539d8af6ee905c562ce5ba7cc01203b86b`。当前base声明Pydantic2.0a4/core0.31.0，issue报告2.0a3/core0.25.0/Python3.10.11；不将报告版本当安装要求。
- 元数据Python只用 pathlib/json/re/hashlib/collections读取文本并核哈希；test.patch与grading内嵌值、gold.patch与validation值逐字相等，两份原始日志SHA256匹配run_refs。没有import项目、测试、安装、Docker、SSH、外网或模型运行。
- 实际深读：_generate_schema.py的generate_schema/property/prepare/type分派、Sequence/Iterable、std查找、annotation准备；_validators.py:46-74；json_schema.py的metadata调用、is_instance/list/function/chain/json_or_python与unsupported处理；_std_types_schema.py:520-600；main.py两个入口、type_adapter.py初始化和验证/schema入口、_model_construction.py:172-211；tests/conftest.py全文；test_json_schema.py导入与相关list、nested model/enum、unsupported/callable、ref、custom hook/generic、Iterable、unparameterized、mode、末尾mapping用例；test_types.py公开Sequence成功/错误/生成器、Enum不导出却可验证/序列化、unsupported自定义序列；test_edge_cases.py:2480-2522字符串拒绝；pyproject依赖与pytest配置、Sequence文档。273 P2P全量ID与原始状态核对，但未逐条读完全部测试体；其余文件不声称完整审查。

## 1. 公开目标、方向歧义与初态

issue明确报告Sequence[int]的JSON行为不一致，并写“model_validate_json应在model_json_schema抛异常时也拒绝”“schema导出失败看起来正确”。实际示例JSON验证已经抛ValidationError，所以不能把“有任何异常”当充分修复；可能指应在验证前报告schema不适用。公开材料未规定拒绝类别、阶段或泛化到哪些类型。

同时，公开实现已经支持Python Sequence[int]及JSON/Python分支（_generate_schema:826-845；json_schema:567-571），相邻List[int]有数组schema（tests/test_json_schema.py:692-705）。因此支持JSON数组、让两条路径都成功是合理工程方向。它消除了“schema失败”的条件前提，**并非形式逻辑上违反条件句**；但与报告者认为schema失败正确、主张更早拒绝的叙述存在实质方向差异。当前题面不足以唯一排除窄范围提前拒绝路线，不能从gold反推公开已明确要求成功。

P1暂定为“公开方向未澄清”，而不是断言原题不可解或任何支持实现违背题面。适合的公开澄清应只说明预期行为，例如支持Sequence[int]的合法JSON数组与对应整数数组schema，同时保留Python Sequence行为；不应复制隐藏函数名或整套测试格式。是否采用此澄清需单独版本化，当前未改题。

初态路径：Model.model_validate_json直接调用core validator（main.py:415-440）；model_json_schema另走JSON Schema生成器（630-655）。模型构建先用GenerateSchema再建SchemaValidator（_model_construction:172-209）。Sequence[int]生成“is-instance Sequence → sequence_validator包list元素验证”的chain；JSON Schema导出chain首步（json_schema:546-551），is-instance不可导出（323-324,1209-1215）。原始noop恰在此失败，确认当前base仍有报告的schema问题。

不能把JSON Schema导出失败普遍等同core schema无效。公开Enum/IntEnum测试允许Python构造、dump、dump_json，同时期望JSON Schema报错（test_types.py:1422-1484）；这是拒绝路线不得无依据扩大成全局模型禁用的反证，但不单独决定Sequence JSON输入应成功还是拒绝。

## 2. 全部新增断言、fixture/helper与双向映射

test.patch仅新增typing.Sequence导入和两个参数化函数，文件为tests/test_json_schema.py。每函数分别对typing.List、typing.Sequence运行；`sequence_type0`=List、`sequence_type1`=Sequence。参数通过pytest提供，无Mock、无专用fixture/helper。tests/conftest.py:43-47的autouse仅关闭错误URL，create_module是其它旧测试的临时源码装载fixture，不参与新增测试。新增用例使用真实BaseModel、核心schema与JSON解析。

- F2P `test_sequence_schema[sequence_type1]`：局部Model.field:Sequence[int]，只调用model_json_schema，精确比较object schema、Model标题、field属性的数组type/整数items/Field标题及required列表。字典相等不绑定键顺序。标题/required/array形式均有相邻List测试依据；**要求Sequence导出成功**是上述公开方向歧义处。
- F2P `test_sequences_int_json_schema[sequence_type1]`：相同结构改字段名为int_seq、标题Int Seq；先精确比较schema，再 `assert Model.model_validate_json('{"int_seq": [1, 2, 3]}')`。最后只检查成功返回的truthiness，没有比较模型类型、字段内容/类型、元素转换、非法元素/非数组拒绝。虽有JSON验证语句，noop在前一个schema断言调用处已抛错，不能说原始noop日志实际触发了JSON输入失败。
- P2P `test_sequence_schema[sequence_type0]`、`test_sequences_int_json_schema[sequence_type0]` 运行完全同样断言但用List[int]，保护普通列表行为。四个新增case均有明确用途，两条Sequence F2P的schema部分较重复，第二条增加成功JSON路径。

| 公开要求/合理旧行为 | 公开依据 | 对应测试及断言 | 覆盖/冲突 | 现有执行/缺口 |
|---|---|---|---|---|
| 修复Sequence[int] JSON不一致 | issue全文；分流与List schema机制 | 两个Sequence F2P要求schema成功；第二个还要求合法JSON返回truthy | 成功方向可解释，但公开未唯一确定 | noop两项都在schema先失败；gold两项完成 |
| 题面提出schema无效时JSON更早拒绝 | issue描述与“seems correct” | 没有拒绝测试；成功schema前置断言会排除保持schema失败的路线 | 实质方向歧义；不是严格逻辑矛盾 | 需公开预期澄清；CPU不能决定需求 |
| List[int]原行为与JSON schema惯例 | test_json_schema:676-748 | 两个List参数P2P；既有test_list/list_union_dict等 | 覆盖相关场景 | 两角色通过 |
| JSON整数数据保真、类型转换、非法输入拒绝 | int标注、main.py验证接口、test_types:2029-2144既有元素校验 | 唯一JSON正例只assert模型truthy | 部分；无数据内容/负例 | 静态缺口；不可声称错误实现已获分 |
| Python tuple/deque保持、range转list | test_types:1876-1891；_validators:64-74 | test_sequence_success各参数 | **不在273 P2P，且官方命令不执行test_types** | 静态已读，未有本次引用运行；直接Sequence→list可破坏 |
| generator/set拒绝，str/bytes拒绝 | test_types:2010-2144；edge_cases:2480-2522；_validators:55-62 | test_sequence_generator_fails、test_sequence_fails、test_sequences_str | 不在冻结参考/执行文件 | edge字符串用例另有<3.9 skip；不能借本轮Python3.8证明覆盖 |
| items可为nested model/enum/custom hook | generate_schema:194-234,312-328；JSON Schema相关公开测试 | List[Foo]、List[Enum]、List[MyPath]及custom generic P2P | 非Sequence场景有保护，Sequence组合未测 | gold回调绕过入口的泛化风险见G2 |
| Sequence[Any]/裸Sequence、strict、嵌套与模式 | _sequence_schema Any分支；_std_types_schema:557-600；main/schema默认mode | 无新增相关参数；旧unparameterized只测试List/Dict等 | 未覆盖各自分派 | 不把typing.Sequence与Sequence[Any]当完全相同路径 |

相关P2P已追：test_list、List[int]/union/dict、List[Foo]、List[enum]、Iterable、unparameterized List/Dict、unsupported ImportString/Callable、refs与自定义ref、MyPath hooks、custom generic hooks、serialization/validation mode。它们有价值，但没有任一在base模块中使用Sequence（对该文件全文搜索无匹配，补丁才引入）；不能把273个JSON Schema测试当Python Sequence兼容性证明。doc/usage/types/sequence_iterable:116-118声称generator可接受，与当前实例检查和明确旧测试冲突，保留为旧文档冲突，不据它授权修改既有generator拒绝行为。

## 3. 合理替代实现与可蒙混部分实现

合理替代（选择支持方向时）：复用一个经 `generate_schema(item_type)` 处理的list_schema，保留原Python is-instance+sequence_validator，使用json_or_python_schema分流；JSON导出已有 `json_schema.py:567-571` 可直接处理JSON分支，未必需要gold新增的metadata回调。测试不绑定回调名、core字典结构或文件位置，应保留接受这条路线的空间；本轮未实跑其通过性。

可区分错误候选L1：把 `_sequence_schema` 全部替换为 `core_schema.list_schema(self.generate_schema(get_first_arg(sequence_type)), allow_any_iter=True)`。它可自然生成整数数组schema并验证给定JSON正例，所有非Sequence的JSON Schema P2P原则上不受影响，却失去Python Sequence实例检查和原容器重建；tuple/deque变list、generator/set可能接受。这不是人为硬编码特定字段名，而是修JSON问题时容易采用的局部简化；公开旧测试足以判其不完整。其真实RH2分数仍未知，必须并列得分与旧行为对照，不能静态断言已证实假阳性。

“提前拒绝”替代需要明确异常范围/阶段，可仅限制目标Sequence JSON路径，不能泛化成禁止所有不能导出schema的模型。因公开目标歧义仍未消除，本轮不把任意拒绝补丁预判为正确，也不把失败F2P简单叫误拒已证实。

## 4. gold检查与未测边界

gold只改 `_generate_schema.py`，无新依赖：JSON走list_schema，Python保留is-instance和sequence_validator，Any分支仍不走元素wrapper。静态能解释它修复原int例子；历史gold两个F2P和273P2P通过提供对应运行支持。题面完整双字段原例、非法JSON、Python回归未由该模块实际验证。

**G2：自定义items的JSON导出泛化风险（静态，非已确认base回归）。** gold.patch:11-13回调重新调用 `self._generate_schema(item_type)`，而用于验证的list在17行调用 `self.generate_schema(item_type)`。公开入口先处理prepare annotations、`__get_pydantic_core_schema__`以及JSON hooks（_generate_schema.py:194-234,312-328），直接私有分派不会执行这些入口步骤。对一个普通自定义类X，若它通过core hook返回int_schema，验证侧可能成功，而JSON回调重新分派X时在436-447报unsupported；Sequence[MyPath]也可能丢已支持的JSON扩展。现有MyPath测试只包List（test_json_schema:2188-2215），不覆盖该路径。

可在后续用下述最小类定义检查，但优先级低于L1；此行为在base中本就无法导出Sequence schema，所以不能称“gold破坏已可工作的Sequence[X] schema”，也不能将issue明确int场景强行扩为任意类型完备性：

```python
from typing import Sequence
from pydantic import BaseModel
from pydantic_core import core_schema
class X:
    @classmethod
    def __get_pydantic_core_schema__(cls, source, handler):
        return core_schema.int_schema()
class CustomItems(BaseModel):
    values: Sequence[X]
```

应分别观察CustomItems.model_validate_json与model_json_schema，不预写“本轮已失败”。对于模型/ref和mode还有复杂调用链，未穷举。gold在目标int上通过不消除此边界，也不据此直接reject。

## 5. 原始运行核对：执行与冻结保护分开

两条 `E/{noop,gold}/ledger.jsonl:1` 为2026-09-19 RH2 replay、`pydantic-install-v1`；实际image `sha256:ccecd4e5820e16d1bfefa35fc6d2ccef95be84d09037ad677815df5f0ac039f4`，与公开manifest原像分开记录。grader为54322、2CPU/4GiB、deny_all、64MiB shm、可写conda前缀。候选应用记录agent/54321只证明应用步骤，不是正式actor工具/交互会话。

- noop日志 `E/noop/eval_logs/evallog_replay-er19-pyd1-pydanti_d4a2811f.eval.log`：132-150表明HEAD是精确base、工作树有pdm.lock/pyproject变化。152-1114的大段diff来自**git show当前base提交**，不是额外未提交业务改动；1115才开始对base工作树diff。3502-3512显示额外pre-commit>=2.21.0依赖。3514-3554官方测试恢复和应用成功。3693-3765从build-wheels完成安装，core0.31.0、Python3.8；3775-3777确实运行test_json_schema.py、collected278。4053-4058四个新增case中两个Sequence失败；4061及4139均在model_json_schema调用处，4135/4213为IsInstanceSchema错误。4227-4237=2 failed/275 passed/1 xfailed、rc1。
- gold日志 `E/gold/eval_logs/evallog_replay-er19-pyd1-pydanti_2ce45489.eval.log`：3733-3805安装完成，3815-3817同模块collected278；4093-4096四项均通过，4100-4105=277 passed/1 xfailed、rc0。
- 元数据逐行核对全部冻结参考：F2P2/P2P273，无缺席；gold2/2+273/273 reward1，noop0/2+273/273 reward0。实际额外执行的两个Callable fallback warning参数用例均通过、`test_get_pydantic_core_schema_calls`为xfail，三者均**不在冻结参考**。parser记录277，不能冒称总collected277或所有277通过项都受reward保护。
- 已读xfail声明（test_json_schema:3616-3623）：已知JSON hook调用次数问题；不得把这一已有xfail当本题新gold失败。两个warning测试正文1265-1278已读，是告警与fallback schema输出，不是Sequence测试。
- ledger导入位置`/testbed/pydantic/__init__.py`、版本2.0a4，gold projection仅pydantic/_internal/_generate_schema.py且ignored_paths=[]；cleanup.removed=true、runner_integrity_changed=false。历史安装gold4.318s/noop4.777s，测试2.97s/4.108s，峰值约133/167MiB，不用来填本次actor耗时/资源合格。
- recipe及eval/candidate after scripts确实editable安装当前源码，再消费testing/testing-extra metadata；官方只恢复tests/test_json_schema.py。工作树安装元数据来自镜像遗留，不把静态base导出当完整运行树。

## 6. 开发条件、交付与控制面

| 操作/资产 | 公开依据 | 已有证据范围 | actor缺口/最小验证 |
|---|---|---|---|
| 定位与源码提交 | issue、_sequence_schema、main两个入口 | gold源码路径成功投影，官方恢复测试文件 | 实际UID/cwd/HEAD与可写工作区未知；合法修复无需写会被恢复的测试或系统文件 |
| Python/core导入 | pyproject:60-65；core入口 | grader用Python3.8/core0.31.0/Pydantic2.0a4工作区导入成功 | 正式actor shell打印sys.executable、版本、包来源；旧BASH_ENV/激活声明不得代证 |
| 原例运行 | user_prompt含list[int]，报告Python3.10 | grader3.8不兼容原样list[int]语法，但隐藏测试用typing.List | actor若3.8，可公开等价改写typing.List[int]或加future annotations再复现；记录该适配，不能把TypeError当目标bug。两个API分开调用捕获现象 |
| 窄测试 | test_json_schema imports；test_types/edge imports；pytest配置 | grader module全跑，pytest及相关依赖就绪 | actor执行公开Sequence测试和最小复现；需pytest/dirty-equals/core/typing_extensions，完整schema模块还会用email-validator等已备包 |
| 准备/安装/编译 | pyproject hatchling/readme、testing组 | grader build-wheels与可写前缀支持offline editable install | actor能否访问对应离线wheel/缓存与安装权限未验；最小源码修复不要求编译Rust、全量make或文档构建 |
| 外部资产/服务/资源 | 题面全为标准库类型与本地Pydantic | 本题历史deny_all完成 | 无本题运行期网络API、数据库、GPU或数据集；真正actor profile/tmp/home/依赖消费待验 |

本题test.patch不混普通源码。public_hints禁止测试修改若适用，不阻挡source-only修复；临时shell复现可用。实际消息尚未捕获；“所有测试都会恢复”与当前具体恢复面不可混为一谈。metadata安装、pytest配置/conftest是潜在共享控制面，本轮没有攻击验证，也不新增文件排除。真实镜像未来历史/答案资产未审；源包无.git不能代替泄漏验收。

未做本题跨任务聚类；不以同仓库/相同文件推断关系。审查含gold、隐藏测试和public_read，未来solver不得使用本稿；无模型成功率、学习价值或训练准入结论。

## 7. 暂定处置与唯一优先CPU实验

`needs_review/static_review`、`development_diagnostic`。需要先明确接受/拒绝方向，独立于环境问题；不建议以当前原题直接解释模型失败为能力不足。原始grader配方对照有效，但正式actor待验。L1为具体漏测候选，G2为int以外泛化静态风险，均未执行。

唯一优先CPU实验：在隔离Python3.8/core0.31.0、同一pydantic-install-v1派生配方中，对base、gold及L1“朴素Sequence→list”候选，**一次对照**同时运行官方评分与下面基于公开旧行为的窄检查。L1改法限定为前述_sequence_schema返回list_schema，不动测试、配置、评分脚本。先记录模型schema与JSON成功状态，再独立检查Python容器/拒绝行为，避免一个失败让其它观察缺失。以下完整断言只是建议，尚未运行：

```python
from collections import deque
from typing import Sequence
from pydantic import BaseModel, ValidationError

class Model(BaseModel):
    values: Sequence[int]

# 每条独立记录结果，base的JSON/schema失败不应中断其Python回归检查。
assert Model(values=(1, 2, 3)).values == (1, 2, 3)
assert Model(values=deque([1, 2, 3])).values == deque([1, 2, 3])
for value in ((x for x in [1, 2, 3]), {1, 2, 3}):
    try:
        Model(values=value)
    except ValidationError as exc:
        assert exc.errors(include_url=False)[0]['type'] == 'is_instance_of'
    else:
        raise AssertionError('non-Sequence accepted')
```

选择理由：它直接区分题意合理的旧行为与冻结评分是否会放过常见简化实现，不依赖G2的扩展范围争议。若L1拿满分且旧行为失败，才将漏测由静态候选提升为真实RH2反例，随后提出窄回归修订；若不得分，记录是哪项现有保护捕获，撤回对应预测。需求方向由公开规范澄清解决，不能由实验中gold得分倒推。

八方面均按上述限定范围覆盖：公开需求、材料初态、断言映射、误拒合理路线、gold/回归、开发条件、投影评分边界、用途关系暴露。未查全仓/每条P2P体、正式actor/消息、完整镜像资产、完整CPU跨版本或模型结果。本题旧调查尚未开放，至此封存。
