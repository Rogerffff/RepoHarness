# conan-io__conan-13788 独立初判

判断者：reviewer_pack10_conan。阶段：cross_review release 前独立静态审查。初判：`needs_review / static_review`，仅拟用于 `development_diagnostic`。历史 F2P/P2P 的0→1分差来自目标锁定版本错误；按(name, context) 区分同名依赖有公开源码依据。但 gold 把普通依赖的 fallback context 固定为 host，存在影响 build-context 传递依赖的具体静态回归疑点，尚未运行证明。不能用10项全绿认定 gold 完整。

## 阅读和暴露边界

仅读派发卡、中性方法及本包两题 PUBLIC/PRIVATE 原件、run_refs 明确指定的本题账本行/日志/candidate patch，以及 baseline/stage/projection 的授权 JSON 指针。未读 public_read、主审、history 或根汇总；没有执行/导入项目、测试、安装、网络、容器。静态导出与实际 actor 初态分开。

本题完整读 gold/test patch、`conans/test/integration/graph_lock/graph_lock_build_requires_test.py` 全268行旧内容和新增两参数测试全部断言；GraphLockNode 初始化/context/deserialize/serialize、GraphLock 构造:280–332、pre_lock_node/lock_node/check_locked_build_requires:480–585；Requirement:1–75；graph_builder.py:65–120、178–230、230–270、315–390、425–480；graph_manager.py 的 _RecipeBuildRequires、_get_recipe_build_requires/_recurse_build_requires；TestClient run/CLI/error:550–620；GenConanfile 的声明与render/repr决定段。README.rst:1–100、pytest.ini、requirements_dev.txt。额外风险抽读 graph_lock_ci_test.py:845–935（双profile CI测试前半，仅看见 br 叶节点、未覆盖本疑点）；未读该文件余段、其他graph_lock测试或全仓。以上八个旧P2P与新增False P2P全部语义核读，不以数量冒充覆盖。

## 需求—断言双向表

| 需求/旧行为 | 公开依据 | 测试ID/决定性断言 | 判断 |
|---|---|---|---|
| 配方和profile同名不同版本能否共存；复用lock是否选对版本 | 题面是提问，报告1.59；base为1.60.0-dev。旧测试已允许host/build双context，graph_manager以(name,context)保存/override | 新 `test_duplicated_build_host_require[True]`（唯一F2P）：force_host_context=True recipe tool/[^4.0] + profile tool/[^3.0]；安装前后均要求 `tool/4.0 from local cache - Cache` | 主目标有根据：跨context合法共存、host不应换为build版本；题面没有实际recipe/profile，具体强制host场景属未公开细化，保留轻度规格不确定性 |
| 普通host requires 不因同名build requirement改变 | 同上，Requirement默认None而普通图继承父context | 新同测试 `[False]`（P2P）：使用 with_requirement，前后同一句4.0断言 | 覆盖普通host路径，无普通build-context依赖 |
| 多条build依赖、build order保持 | 旧公开 `GraphLockBuildRequireTestCase::test_duplicated_build_require` | lock br ref/prev、完整build-order JSON与后续install/revision | P2P覆盖单context重复及旧构建顺序 |
| 同名两context合法且package_id各自保持 | `::test_package_both_contexts`、`::test_package_different_id_both_contexts` | lock JSON、host/build build-order、不同OS package_id精确值 | P2P是反对“禁止所有重复名字”的公开证据；protobuf均为叶节点，不覆盖工具的普通传递依赖 |
| lock复用不丢已有build信息 | `::test_build_require_not_removed` | 三次lock更新的ref/package_id/prev | P2P覆盖保留/重建状态 |
| 多个匹配版本、显式version范围规则 | `::test_multiple_matching_build_require` | ranges+lock必须报错，具体cmake/1.1安装输出 | P2P覆盖入口限制与明确版本选择 |
| profile工具与recipe工具都保留 | `::test_unused_build_requires` | cmake/gtest cache及Applying build-requirement输出 | P2P覆盖两个不同名字，单profile，不等于新同名双context |
| 动态删除锁定依赖须报错 | `::test_conditional_env_var` | USE_DEP建锁含两个引用；create时缺dep_recipe报指定错误 | P2P覆盖旧遗漏检查，按名字检查尚未加强到context |
| test_package私有build requirement可使用 | `::test_test_package_build_require` | consumer root/path、随后create输出cmake | P2P覆盖未锁test_package例外路径 |
| build-context工具的普通传递依赖须可复用lock | graph_builder:240、439–467继承node.context；Requirement:24 默认None | 上述新增与所选P2P无对应断言 | 具体覆盖缺口；gold fallback host与此调用链冲突，待有目的CPU对照 |

新增总共2个参数实例、各2个正向字符串断言，无直接锁文件结构/上下文/3.0版本保留断言。TestClient每次run重置out并要求RC=0，故第二次4.0断言不是首次输出残留；但只看4.0不能充分验证profile的3.0也正确保留或真正消费的二进制/环境来源。False参数确实是P2P，不能把两个参数都算F2P。

## Gold、合理非gold路线与回归疑点

Gold两处改动（同文件）：导入CONTEXT_HOST；将lock_node的refs由name索引改为(name, locked-node.context)，查询以require.build_require_context为准，None时固定host。显式build requirements在graph_builder:90–101赋context后锁定，因此修复True分支的同名覆盖原因清晰。旧RecipeBuildRequires/graph_manager已经按(name,context)区分recipe与profile；gold没有理由推翻这项公开旧行为。

可接受的非gold路线是按context筛选锁定节点，或分开普通requires和build_requires的查找；无需使用相同字典推导式。盲目拒绝同名跨context虽契合提问者初始预期，却违反现有双context公开测试，不能算已证正确替代解。现有输出断言不强制私有内部布局，但基于具体CLI措辞，措辞变化会影响断言。

**具体疑点（静态推断，非已证运行回归）**：设host app通过build requirement使用tool/1.0，tool普通`requires="dep/1.0"`，启用build profile。graph_builder._create_new_node:439–467令tool为build；普通dep由node.context继承build；GraphLock:280–332把此context存到locked-node。第二次用lock，_get_node_requirements:208对tool的普通Requirement调用lock_node，此require.build_require_context仍为None（requires.py:24）；gold查(dep,host)，锁里为(dep,build)，可能抛 `Require 'dep' cannot be found in lockfile`。Base按name查找不受此键不匹配影响。当前selected P2P中的build-context工具均无普通传递依赖，不构成反证。另有缺context旧lock反序列化取None的兼容性疑问，未展开、不能列成确认故障。

check25可确认测试缺少该路径；check26保持unknown（有源码依据的待验疑点）；check27可保留目标局部正证据，但完整性unknown。未执行反例，不声称已经证实gold破坏既有合理行为。

## 历史原运行与身份

w01-2账本第15行noop、第16行gold均已机械选行核读，行SHA、两份完整日志SHA已核对。原gold candidate.patch字节等于本题gold，SHA `6abb6d5db6bf7eeb7f44aa9aa0da9b3823256b63ff94fdcda85c6c9b50869366`；baseline与stage指针指向 `c1b3978914dd09e4c07fc8d1e688d5636fda6e79`；projection noop空、gold只含`conans/model/graph_lock.py`。这是历史绑定，非actor实际初态。

运行使用`source /opt/miniconda3/bin/activate`、`conda activate testbed`、`cd /testbed`、`PYTHONPATH=:/testbed`；原安装依次`python -m pip install -r conans/requirements.txt`、`...requirements_server.txt`、`...requirements_dev.txt`。三个安装命令的位置分别noop:424/445/449、gold:457/478/482，安装最后命令RC=0。实际测试`pytest -n0 -rA conans/test/integration/graph_lock/graph_lock_build_requires_test.py`，Python3.10.14/pytest6.2.5/xdist3.5.0。

| 角色 | 原日志位置 | 测试RC/观察 | expected映射 |
|---|---|---|---|
| noop | 869b80b6:482–551 | RC1；collected10；1 failed/9 passed；289行第二次lock安装后缺4.0字符串 | True F2P失败；8旧P2P+False均通过 |
| gold | 423e6042:515–558 | RC0；collected10；10 passed | F2P1/1、P2P9/9 |

没有skip/xfail；3个DeprecationWarning是regex escape和imp，不是失败。原输出对实际错误选到哪个版本被pytest截断，故只确认4.0消失，不从日志捏造完整依赖图；name字典覆盖原因有源码支撑。parser记录10个身份、段外0、reference_missing/skipped为空，版本swegym_parsers@242429c1；reward分别0/1。清理removed=true/rm:ok，无重试或本次复跑。

noop原日志135–137工作树clean，243行`git diff <base>`无差异；gold135–142只改graph_lock.py，248–276 diff符合gold。两份日志的`git show`展示base提交内VS2017测试修改，**并非未提交初始改动**。恢复目标测试后patch apply clean，restored/expected/present均1，setup RC0。实际actor status --porcelain输出/RC/采集阶段仍unknown。

历史评分user=rh2grader/54322，candidate应用user=agent/54321，观测import `/testbed/conans/__init__.py`、pkg version=1.60.0-dev；与报告者1.59不同是任务基线版本，不冒充现场版本。image tag=`xingyaoww/sweb.eval.x86_64.conan-io_s_conan-13788:latest`，expected digest=`sha256:c61a9b9f87dcee19aff867f583028bd115f6fcf3487c2c603471787a9eb7472d`，actual ID=null；scripts_digest=`sha256:47ec952aaa32c5c07cab7035fdb11bfc9866e916cb500380e9d6519aba1f8355`仅标识历史脚本。policy cpus=2.0/memory_bytes=4294967296/network=deny_all/pids_limit=512；resource原值mem_peak_mb=95.371/91.129，不换算。未核原脚本archive内容或当前评分接线。

## 八方面与开发需求

| 方面 | 已查与剩余 |
|---|---|
| 版本与初态 | patch/expected/base/历史绑定核对；实际actor树、源镜像忽略资产未知 |
| 公开规格 | 双context合法共存可由源码旧测试推断；实际故障recipe未给，强制host是测试细化 |
| 测试覆盖 | 全部新增断言和9个P2P已逐项核读；build工具普通传递依赖遗漏 |
| Gold正确性/回归 | 局部纠正同名覆盖有证据；完整性和传递依赖回归待验 |
| 运行评分 | 原10项完整执行、目标断言失败、映射和候选绑定核对；不是全仓或所有实现证明 |
| Actor开发 | 历史grader支持本地无编译recipe/lock流程；actor缓存写权限/依赖/入口未验 |
| 暴露及提交 | 审查者见本题gold/隐藏断言/日志；实际actor消息、工具可见私有材料未知，不以审查暴露替代check29 |
| 用途/筛查偏差 | 受限静态开发候选，有具体可改变判断的疑点；封存流程不证明无漏检/误拒/抽样偏差 |

| 操作/资产 | 公开依据 | 历史证据适用条件 | 缺口 | 最小验证建议 |
|---|---|---|---|---|
| Python源码导入、CLI export/create/install/lock、可写cache和profile | README与公开graph_lock测试 | 历史rh2grader本地cache合成recipe，无外部编译/下载需要 | actual actor解释器、HOME/cwd/权限、默认profile与asset位置未知 | 正式actor入口记录sys.executable/conans.__file__、HEAD/status/diff和cache权限；`python -m pytest -n0 -rA conans/test/integration/graph_lock/graph_lock_build_requires_test.py`可验证旧公开回归 |
| build-profile普通传递依赖锁定可复用 | graph_builder/context与公开跨profile能力 | 本题历史选中测试不含该链 | gold是否引入可复现回归 | 私有隔离CPU中以无编译dep/tool/app配方，对base与gold各做`conan export dep dep/1.0@`、`conan export tool tool/1.0@`（tool requires dep/1.0）；app build_requires tool/1.0；`conan install app -pr:b=default -pr:h=default --build --lockfile-out=conan.lock`，再`conan install app --lockfile=conan.lock`，观察dep的context/RC/锁定错误；将环境错误与功能错误分开 |

唯一优先下一步：交任务二做上表传递依赖链的**同条件base/gold私有CPU对照**。预期若base成功而gold在普通dep锁定时报context不匹配，可将check26由unknown改为已证问题；若都成功，应保留调用/lock JSON来解释默认context推断为何不成立。先取真实入口/初态证据；无需全仓。含gold的该环境与结果不得送给独立solver。

## 证据目录与稀疏记录

- PUBLIC：`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/conan-io__conan-13788`；文中 base 相对路径均以此目录下 `base/` 为根。
- PRIVATE：`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/conan-io__conan-13788`；已读 user_prompt/public_bundle/base_identity、gold.patch/test.patch/grading.json/validation.json/run_refs/source_refs/environment_record。
- noop：`/Users/roger/Desktop/claude-code-verl-stage0h/runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-2/ledger.jsonl:15`；日志 `/Users/roger/Desktop/claude-code-verl-stage0h/runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-2/eval_logs/evallog_replay-f216-baseline01-w_869b80b6.eval.log`（授权1–551；实读初始化身份、安装/测试/目标失败区段，并检索全授权范围的命令与状态；conda激活内部逐行未审）。
- gold：`/Users/roger/Desktop/claude-code-verl-stage0h/runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-2/ledger.jsonl:16`；日志 `/Users/roger/Desktop/claude-code-verl-stage0h/runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-2/eval_logs/evallog_replay-f216-baseline01-w_423e6042.eval.log`（授权1–558；实读初始化身份、安装/测试/目标失败区段，并检索全授权范围的命令与状态；conda激活内部逐行未审）。

下列13字段只是本初判的稀疏记录，不替代主审screening_record。未列check=not_checked；pass仅限所引历史/静态范围。

```json
{
  "task_id": "conan-io__conan-13788",
  "task_revision": "c1b3978914dd09e4c07fc8d1e688d5636fda6e79",
  "source_adapter_ref": "/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/conan-io__conan-13788/source_refs.json",
  "recipe_ref": "/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/conan-io__conan-13788/run_refs.json",
  "code_snapshot_ref": "/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/conan-io__conan-13788/base_identity.json",
  "facts_ref": [
    "/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/conan-io__conan-13788/run_refs.json",
    "/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/conan-io__conan-13788/environment_record.json"
  ],
  "checks": {
    "1": {
      "status": "unknown",
      "evidence_refs": [
        "private/run_refs.json及本稿历史原运行（仅历史grader范围）"
      ],
      "by": "reviewer_pack10_conan"
    },
    "2": {
      "status": "pass",
      "evidence_refs": [
        "本稿需求—断言表、Gold与风险分析"
      ],
      "by": "reviewer_pack10_conan"
    },
    "3": {
      "status": "unknown",
      "evidence_refs": [
        "public/environment_brief.md、actor_environment_card.md及本稿边界"
      ],
      "by": "reviewer_pack10_conan"
    },
    "8": {
      "status": "unknown",
      "evidence_refs": [
        "public/environment_brief.md、actor_environment_card.md及本稿边界"
      ],
      "by": "reviewer_pack10_conan"
    },
    "9": {
      "status": "pass",
      "evidence_refs": [
        "private/run_refs.json及本稿历史原运行（仅历史grader范围）"
      ],
      "by": "reviewer_pack10_conan"
    },
    "10": {
      "status": "unknown",
      "evidence_refs": [
        "public/environment_brief.md、actor_environment_card.md及本稿边界"
      ],
      "by": "reviewer_pack10_conan"
    },
    "17": {
      "status": "pass",
      "evidence_refs": [
        "private/run_refs.json及本稿历史原运行（仅历史grader范围）"
      ],
      "by": "reviewer_pack10_conan"
    },
    "18": {
      "status": "pass",
      "evidence_refs": [
        "private/run_refs.json及本稿历史原运行（仅历史grader范围）"
      ],
      "by": "reviewer_pack10_conan"
    },
    "19": {
      "status": "pass",
      "evidence_refs": [
        "private/run_refs.json及本稿历史原运行（仅历史grader范围）"
      ],
      "by": "reviewer_pack10_conan"
    },
    "20": {
      "status": "pass",
      "evidence_refs": [
        "private/run_refs.json及本稿历史原运行（仅历史grader范围）"
      ],
      "by": "reviewer_pack10_conan"
    },
    "21": {
      "status": "pass",
      "evidence_refs": [
        "private/run_refs.json及本稿历史原运行（仅历史grader范围）"
      ],
      "by": "reviewer_pack10_conan"
    },
    "23": {
      "status": "unknown",
      "evidence_refs": [
        "本稿需求—断言表、Gold与风险分析"
      ],
      "by": "reviewer_pack10_conan"
    },
    "24": {
      "status": "pass",
      "evidence_refs": [
        "本稿需求—断言表、Gold与风险分析"
      ],
      "by": "reviewer_pack10_conan"
    },
    "25": {
      "status": "issue",
      "evidence_refs": [
        "本稿需求—断言表、Gold与风险分析"
      ],
      "by": "reviewer_pack10_conan"
    },
    "26": {
      "status": "unknown",
      "evidence_refs": [
        "本稿需求—断言表、Gold与风险分析"
      ],
      "by": "reviewer_pack10_conan"
    },
    "27": {
      "status": "unknown",
      "evidence_refs": [
        "本稿需求—断言表、Gold与风险分析"
      ],
      "by": "reviewer_pack10_conan"
    },
    "29": {
      "status": "unknown",
      "evidence_refs": [
        "public/environment_brief.md、actor_environment_card.md及本稿边界"
      ],
      "by": "reviewer_pack10_conan"
    },
    "33": {
      "status": "unknown",
      "evidence_refs": [
        "public/environment_brief.md、actor_environment_card.md及本稿边界"
      ],
      "by": "reviewer_pack10_conan"
    },
    "40": {
      "status": "unknown",
      "evidence_refs": [
        "public/environment_brief.md、actor_environment_card.md及本稿边界"
      ],
      "by": "reviewer_pack10_conan"
    }
  },
  "issues": [
    {
      "category": "actor_evidence_gap",
      "scope": "实际开发入口/消息/初态/权限未取得",
      "evidence_refs": [
        "public/environment_brief.md",
        "private/environment_record.json"
      ],
      "proposed_action": "任务二在正式actor入口采集所需事实，不以历史grader替代",
      "status": "unknown"
    },
    {
      "category": "coverage_gap",
      "scope": "新增仅核4.0输出，不核build-context工具普通传递依赖及profile3.0保留",
      "evidence_refs": [
        "private/test.patch",
        "base/conans/test/integration/graph_lock/graph_lock_build_requires_test.py"
      ],
      "proposed_action": "保留测试范围限制，优先检验下一项具体gold疑点",
      "status": "issue"
    },
    {
      "category": "potential_gold_regression",
      "scope": "普通build-context依赖None fallback被当作host；静态推断未运行",
      "evidence_refs": [
        "private/gold.patch",
        "base/conans/model/requires.py:24",
        "base/conans/client/graph/graph_builder.py:208",
        "base/conans/client/graph/graph_builder.py:439"
      ],
      "proposed_action": "任务二做dep/tool/app双profile同条件base/gold锁定复用CPU对照",
      "status": "unknown"
    }
  ],
  "file_rules": {
    "additional_exclusions": []
  },
  "revision_refs": [],
  "disposition": {
    "state": "needs_review",
    "scope": "static_review",
    "reason": "静态候选；gold传递依赖context疑点待目的性CPU对照，actor待验"
  },
  "usage": {
    "intended_use": "development_diagnostic",
    "reviewer_private_exposure": [
      "本包两题gold/test patch、grading/validation、各自授权原日志与候选绑定"
    ],
    "actual_actor_private_exposure": "unknown",
    "solver_delivery": "不得交付含gold/隐藏测试/审查结论材料"
  },
  "costs": {
    "tokens": null,
    "cost": null,
    "current_cpu_seconds": null
  }
}
```
