# iterative__dvc-6954 独立复核初判（封存后不回写）

记录时间：2026-09-20 21:28 UTC / 2026-09-21 05:28 SGT。角色：B3 DVC 整包 fresh 独立 reviewer。权威根目录为 `.`；下列相对路径均对此根目录。机器处置：`state=needs_review, scope=static_review`；用途：`development_diagnostic`。

**独立结论：题面成立，核心评分与公开要求相符；可保留为静态诊断候选，但不能宣称覆盖全部负数形式或实际 actor 已可用。** 未发现要求 gold 特定内部实现的断言。确定的覆盖边界是只用一个 `-1` 单测判修复，未直接验证 CLI 原例、负浮点数、容器内负数及参数更新回归。当前无证据须先改题；如将 reward 解释为完整需求满足，先做下述定点覆盖实验。

## 阅读与暴露

先读共用 reviewer 角色卡、模板、actor_environment_card 和 quality_review_protocol；再读本题 public 的 prompt/bundle/base_identity/environment_brief 和精确 base 的相关源码/旧测试，然后读本题 private 全部七份原件。`environment_record.json` 自带 gold/noop 结果摘要，已见，故不是无结果暴露盲审。另读 run_refs 精确指向的两条 ledger、日志相关原始区段、diagnostics、gold driver.log、安装输入 recipe 和 wrapper、gold eval_script.after.sh；inventory 只取 common、families.dvc_install_v1c、本题 exact instance_id 对象，未追 analysis_reference。没有读取任何题的主审/公开审查产物、历史质量结论。没有执行项目代码、测试、安装、Docker、网络或新 CPU 验证；已有日志复读不称重跑。

材料包逐 blob/清单验收复用协调者的验收，不重新导出。public/base_identity 给出 base `28dd39a1a0d710585ff21bf66199208b1b83cbde`、tree `dbf053d617b46eae35ed6ad30eccd4caae0922b7`；grading 与此一致，gold SHA256 `50ed349f0cad3875991e03a9a4c9a01c0ff286cc18a00f1c221f121bcddb8116` 与原 gold ledger candidate 相符。静态包无 `.git`，不代表实际 actor 镜像没有公开历史或额外资产。

## 1. 公开目标与合理实现

题面要求 Python 参数文件的负数可以供 `dvc run/repro` 使用，给出 `my_int = -1` 与完整 `dvc.yaml` 复现；YAML 已可正常工作。不是要求执行任意 Python 代码，也没有指定 `ast.literal_eval`。公开 base `dvc/utils/serialize/_py.py:21–27,89–119,123–181` 的路径明确：`-1` 为 UnaryOp，而 `_get_ast_value` 仅接受 Num/Str/NameConstant，ValueError 被树遍历吞掉，参数因此缺失。`dvc/dependency/param.py:91–138` 从 `.py` LOADERS 读出值后，对缺项报题面同类错误，初态路径相符。

合理解可以保留 helper，只增加对数值 USub（并视已知语义处理 UAdd）的安全解析；也可以采用 gold 的 literal_eval。只需修改非测试源文件，未见必须触碰评分恢复文件的修法。保留 class/实例属性、注解赋值、重复赋值最后值与非参数局部变量过滤，是公开源码和旧测试可见的行为。

## 2–3. 完整断言、F2P/P2P、公开旧行为映射

已逐项读完 test.patch 全部 45 新增行。它仅新增 `tests/unit/utils/serialize/test_python.py`，无自定义 helper/fixture；两个函数都直接调用公开可导入的 `parse_py` 并断言值字典。tests/conftest.py 的自动 fixture（日志、UI、连接池）已读，未把这些 fixture 当作业务覆盖。13 个执行节点、13 个解析键、1 F2P + 12 P2P 需分开计数；此题刚好一一对应。

| 公开要求/旧行为 | 公开依据 | 断言与冻结引用 | 判断 |
| --- | --- | --- | --- |
| 顶层负整数成为参数 | prompt 的 `my_int = -1`；_py.py helper | `test_parse_valid_types[UNARY_OP = -1-result9]` 返回 `{'UNARY_OP': -1}`；冻结 F2P 键截至 `[UNARY_OP` | 核心覆盖。原始 noop AssertionError 为 `{}` 对预期负数，不是导入错误 |
| 正常标量保持原值 | 旧 `tests/unit/dependency/test_params.py:114–153` | BOOL、INT、FLOAT、STR、NONE 五个 P2P | 覆盖；布尔与数值的 Python `==` 不作严格类型断言，通常实现无直接冲突 |
| dict/list/set/tuple 正常值 | 同上和 _ast_assign_to_dict 容器分支 | DICT、LIST、SET、TUPLE 四个 P2P，逐项字典等值 | 覆盖现有一层正数例，未测负数或嵌套容器 |
| 类属性、self 属性与局部作用域、重复赋值 | _py.py:104–115,162–168；旧 dependency tests:155–176 | class P2P 要 EPOCHS=70、layers=9，不含 bar | 覆盖这些公开旧行为，无内部调用形状限制 |
| 不把构造调用/普通算式当静态参数 | _get_ast_value 原行为 | CONSTRUCTOR `dict(a=1,b=2)`、SUM `1+2` 两个 P2P 返回 `{}` | 公开源码可推知，合理回归要求；不强迫使用 gold |
| 负浮点、任意负整数、容器/类中负数、注解负数 | 标题“Negative numbers”；已有 FLOAT/容器/注解/类支持 | 无直接新增断言 | 覆盖缺口。仅接受负 int 的实现静态上可过本组却漏 `-0.5`；尚未执行候选得分验证 |
| 原始 `dvc repro` 和参数更新 | param.py 调用链；旧 `tests/func/params/test_show.py:37–55`；`tests/func/experiments/test_experiments.py:246–327` | 不在本题执行文件和冻结参考中 | 未直接保护，不能用单测通过代称端到端通过 |

F2P/P2P 全部读取，无隐藏精确文案、helper 命名或 Mock 调用次序约束。parser 以 whitespace split 取第二 token，故带空格的参数 nodeid 在冻结引用中截短；本题上述每个参数的首 token 唯一，未发现相互覆盖冲突。不能把这类截短泛化成所有参数都可靠。

## 4. gold 完整性与调用者

gold 把 `_ast_assign_to_dict` 所有标量入口（dict key/value、list、set、tuple、普通及注解赋值）一致替换为 `ast.literal_eval`，删除旧 helper；不是只修顶层 `-1`。遍历层现有 ValueError/AttributeError 处理保留。静态上覆盖负 int/float 和既有容器内的负数，又继续拒绝这两个普通调用/算式例。公开原例的 ParamsDependency 路径会消费该改动，无未交付配套更改可见。

也追读 `parse_py_for_update → modify_py → _dump`、`dvc/repo/experiments/__init__.py:363–384` 的 MODIFIERS 使用与上述 update_py_params 旧测试。gold 扩大 literal 类型/嵌套容器的可解析范围，而更新器仍按旧的行替换方式工作；未证明扩展类型全可更新。题目主要是读取负数，暂不把旧更新器限制或未测嵌套扩展直接判 gold 错；这些更新旧测试未在本题计分。未穷举所有合法 Python 字面量或全仓调用者。

## 5. 原件运行与环境身份

运行证据是 `runs/env_recipe_repair_20260919/dvc_install_v1c/tasks/iterative__dvc-6954/{gold,noop}/ledger.jsonl:1`，不是当前 ROOT/rh2 运行。两者为历史真实 RH2 replay，candidate 补丁以 `agent/54321` apply，评分安装/测试政策为 `rh2grader/54322`、deny_all、2 CPU/4 GiB、64 MiB shm，解释器前缀向 grader 开写。不能因此证明正式 actor 同样能安装。

- gold：原 run 2026-09-19 08:00:48 UTC（16:00:48 SGT），log `...888e8b72.eval.log:650–715` 有 editable build/install 成功、RH2_INSTALL_RC=0、`pytest -rA tests/unit/utils/serialize/test_python.py`、13 collected/13 passed、RH2_TEST_RC=0；ledger reward=1，F2P 1/1、P2P fail 0/12。导入观察 `/testbed/dvc/__init__.py`。
- noop：原 run 08:00:17 UTC（16:00:17 SGT），log `...9b69e9e3.eval.log:595–703` 安装成功且 rc0，625 行同一测试命令，635–673 为负整数真实 AssertionError，683–696 为12 pass/1 fail，rc1；ledger reward=0、F2P 0/1、P2P fail 0/12。
- 两日志 diagnostics 的 reference_missing=[]、reference_skipped=[]、parsed=13；gold/noop reward 与原始摘要相符。`env_qualification=absent` 保留，不能用 environment_record 的 verified_environment_pair 标签改写该字段。
- 派生镜像为 `sha256:e54a7bc51b8d4fd9187c6ac0bd2282c52d51ae2e2695bae263adf58a7159a1ed`；public 原镜像 manifest digest `sha256:1cf3894f41768d84c21d9d9ba02cf59b886bfc391f15f3f7f0c8e3eb972bcb09`。本次未验证目标节点镜像存在性。
- 安装输入是批次 `recipes/iterative__dvc-6954.json`；wrapper:61–85 精确匹配原安装字符串、替换 eval/candidate 脚本并保存审计。实际新安装为 `pip install -e '.[all,tests]'`，保留首个安装退出码。每 run `recipe/recipe.json` 是审计输出。Dockerfile COPY wheels/只证明资产路径设计，安装成功由上述原始日志支持。原 wheel/context 本地未保存，若目标无原派生镜像须另准备，未执行。

## 6. 开发条件

| 操作/资产 | 公开依据 | 已有证据与缺口 | 最小建议（未执行） |
| --- | --- | --- | --- |
| 导入/编辑工作区 DVC | _py.py、param.py、setup.cfg:31,35–78 | 历史 grader 用 Python3.9.19、pytest6.2.5 且导入 /testbed；正式 agent PATH、import 与 prefix 权限未知 | actor 实际 shell 检查 UID/cwd/PATH/解释器与 dvc.__file__，确认编辑生效 |
| 运行公开复现 | prompt 的本地 git init、dvc init、cat、dvc repro | 无外部服务/数据需要；仅本地小文件、Git与已准备依赖，资源估计小但未验 | 隔离临时目录按题面建 stage，检查 b.txt 与 dvc.lock 中 -1；不改测试文件 |
| 公开旧回归 | dependency test_params:114–176、func params/show | pytest-mock 等在 setup.cfg tests extras；tests/conftest 导入较宽依赖，不能只装 funcy 就宣称测试可用 | 窄跑公开 `tests/unit/dependency/test_params.py::test_read_params_py`，不需要隐藏新测试 |
| 离线安装 | setup.cfg、pyproject、input recipe | 历史评分配方已离线安装；actor是否消费该派生镜像/修复配方未验 | 在准备阶段固定相同依赖/wheels；不推定解题期可下载 |

修复本身不需新包、私有资产或可被恢复的源码。public_hints 声称 conda 已激活及“所有测试修改都会恢复”，均不能作为实际环境证明；源文件修复不受该禁改测试指令妨碍。

## 7. 投影、恢复、计分边界

只读冻结 `runs/env_recipe_repair_20260919/frozen_sources/dvc.tar.gz` 的相关成员文本，没有解包或导入：replay driver/adapter、prepared_task_face、spec_vendor，以及沿导入链的 trusted_projection、scoring、swegym_parsers。关键身份：adapter SHA `031046ba444e26a91643ce988c3855e80acb1b4cf90408235d61ff35d87fb896`；face `31ff5145dfa8b71b2a183b14f8a5fbfe4572b71911af54023c8168e534e4f8a3`；spec_vendor `8e0037b27c87268ed7df97ef64d261d0e6dac7375bc85fd5badd0fecdb94d41d`；projection `5ef126803e93e3606123a4aef4389d35bad0551a622020d1dd22f0db32224a60`；scoring `b6c8b9bd3e9cac604bc0d03b0b243ef9646de369e94bb6a65e60eadd3a64f5ab`；parser `995bb6aae58a94f9553946c2f9aea59a158ad4fdf4d7fc0137802c11362b2276`。

face:312–337 按 test.patch 精确触碰路径设 test_files，test_globs=()。本题唯一官方恢复/保护文件为 `tests/unit/utils/serialize/test_python.py`，非“全部测试路径”；新文件由 root trusted setup 应用，diagnostics restored=0、apply_rc=0、test_files=1，符合 base 中没有该文件。gold ledger projection included_paths 仅 `dvc/utils/serialize/_py.py`、ignored_paths=[]。spec_vendor:164–197 从 patch 派生运行文件；scoring:189–270 使用冻结 F2P/P2P 清单和标记段，正常 pytest rc1 不自动等于 reward0。此题实际唯一失败刚好是 F2P，故两者结果一致。其它 conftest/pytest 配置可影响收集属共享未覆盖控制面，不虚构本题攻击已验证或追加路径排除。

## 8. 暴露、关系与下一步

本 reviewer 已见本题 gold/隐藏测试/环境结果，应隔离于后续 solver；不提供模型成功率或学习价值猜测。此初稿时尚未读另外两题原件，不能仅因同仓判同题或泄漏；跨题关系待整包主审开放后的最终 review 补证，不回写本稿。

唯一优先后续实验（建议，未执行）：在明确标识的 actor/评分诊断条件下做“仅支持负 int 的部分修复”定点对照：先用公开 `-1` 与 `-0.5` 两个参数复现核实其行为，再用同一冻结 RH2 运行材料核计分。静态预期该部分修复能过唯一 F2P 而漏负浮点；实验用于量化测试覆盖缺口，不作为合理替代解或独立模型求解成功。执行前仍须补齐目标镜像/配方可用性与实际 actor 入口事实。当前没有执行授权，因此所有候选、CPU验证和测试修订均未实施。
