# iterative__dvc-1681 — 独立原件初判

2026-09-21；Batch02 fresh reviewer；`scope=static_review`、`state=needs_review`、`intended_use=development_diagnostic`。保存时尚未阅读主审、公开读者或历史质量结论。

**初判：base 将绝对工作目录纳入 stage checksum，确有与旧无 wdir 文件不兼容的静态根因；gold 将序列化 wdir 改为相对路径，逻辑合理且历史 RH2 通过。唯一 F2P 实际失败点却是 `dumpd()["wdir"] == "."`，没有直接复现已保存的旧版本 checksum。应先验证“只在 checksum 内正规化”的合理替代路线是否被误拒，并验证真实非默认 wdir 的遗漏；不将当前参考 reward 直接等同向后兼容正确性。**

路径约定：`ROOT=${REPO_ROOT}`；`P=ROOT/runs/swegym_quality_batch02_20260921_v2/public/iterative__dvc-1681`；`Q=ROOT/runs/swegym_quality_batch02_20260921_v2/private/iterative__dvc-1681`；`R=ROOT/runs/env_recipe_repair_20260919/dvc_install_v1c/tasks/iterative__dvc-1681`。源码行号相对 P/base，日志行号为 eval.log 原件。

## 门禁、材料与证据层次

读过 reviewer 角色卡、记录模板、actor 环境卡与质量协议；本题公开 prompt/bundle/identity/环境说明，私有 test/gold/grading/validation/refs/environment_record，下述 base 源码和两次回放原件。已见 environment_record 的 status/checks/report **运行摘要**；没有打开 analysis/history 链接。没有读 results 既有文件、主审/公开审查输出、I2/history、B1/B2 聚合或指定三题之外材料。同上下文另审 3576/4166，不接收其主审结论。

S2 public/grading/validation 指定第 113 行与本包 JSON 相等；base=`9175c45b1472070e02521380e4db8315d7c910c4`。Q/gold.patch SHA256=`f275fc350e4cd4326b1f2bf7e0e432ef248b55322b95b2793b9328ef6d772ba4`，与 gold artifact/candidate.patch 字节一致。两侧 eval_script 的嵌入 test.patch 与 Q/test.patch 一致；recipe 五个审计文件各自哈希与 environment_record 匹配，两角色配方一致、before/after 测试命令段不变。

将公开 base 的全部 220 个文件与两侧 baseline_manifest 逐文件 SHA256 比较，220 个均一致，无缺失；本题无需套用另外两题的 setup.py 差异。materialized_head、task_base_commit、stage.head 都是本题 base；gold frozen_patch 仅改 dvc/stage.py，noop 无改动。

只做静态读取和元数据哈希；未执行/导入 DVC、测试/安装、Docker、SSH、联网或模型。**源码推断**和 **09-19 历史真实 RH2 回放**分别标明；没有当前 CPU、独立局部执行或正式 actor 验收。

## 公开需求与根因

用户升级后旧 `dvc add` 产生的 `.dvc` 文件被 `dvc status` 标成 changed checksum；示例包含 stage 顶层 md5、out 的 md5/cache/metric/path，**没有 wdir**。需求是恢复已有 stage 元数据的向后兼容，不能把输出文件 md5 与 stage checksum 混为一谈，也不是要求忽略所有真实变化。标题/版本字符串有 0.30/0.3.0 表述差异，最后公开复现版本指向本 base `9175c4`，不据笔误否定题目。

公开入口足以定位：

- `dvc/repo/status.py:6–25,67–90` 收集 stage 并调用 status；`dvc/stage.py:748–769` 只有 changed_md5 才添加 “changed checksum”；`changed_md5:182–183` 比较持久化 md5 与 `_compute_md5()`。
- `Stage.load:494–522` 对缺省 wdir 用 `"."`，再相对 stage 文件目录转成绝对 self.wdir。
- `Stage.dumpd:524–536` 原样放入 self.wdir（绝对值）；`dump:538–556` **仅写 YAML 时**转成相对 fname 的 wdir。
- `_compute_md5:558–579` 从 dumpd 取字典，移除顶层 md5；明确注释为兼容无 wdir 旧文件而仅在值恰为 `"."` 时删除 wdir。绝对值导致这个兼容分支不能命中。`dict_md5` 在 utils/__init__.py:76–104 递归排除 locked/metric 后对排序 JSON 求 md5。

因此公开代码本身已说明默认 wdir 不应改变旧 checksum，非默认 wdir 仍应参与 checksum。gold 把相对目录转换移到 dumpd，使哈希和写 YAML 共用表示；原相对转化从 dump 移除，另去掉 dump(fname=None) 的可选参数。没有实际运行原始大文件样本；无需拿到该 Wikipedia 数据文件才能检查 stage 元数据不兼容逻辑。

## 需求—断言双向映射：全部 1 F2P、12 P2P

实际命令 `pytest -rA tests/test_stage.py tests/unit/stage.py`。注意后者文件名是 `stage.py`，不是默认 `test_*.py`；配方显式指定了它，不能把一般 tests/unit discovery 与本次执行等同。

| 公开要求/旧行为 | 具体测试和全部决定性断言 | 对应程度/反向要求依据 |
|---|---|---|
| 默认 wdir 不应使 stage 改变 | F2P `tests/test_stage.py::TestDefaultWorkingDirectory::test_ignored_in_checksum` | fixture 当前版本 dvc.run 执行 `echo test > foo`，deps=bar、outs=foo。**新增** `d=stage.dumpd(); d[WDIR]=="."`；已有 YAML wdir=="."；删除 YAML wdir 并重写；**新增**重读后 `d.get(WDIR) is None`；已有 reload 后 `stage.changed()==False`。前一新增断言限制内部表示；后一新增断言确认输入确实删除。它使用当前版本自行生成 checksum，不是旧版本持久化 hash。 |
| 无 wdir 的既有 checksum 值 | P2P `tests/unit/stage.py::TestStageChecksum::test` | Stage(None,"path")，mock dumpd 为 cmd=mycmd、固定 outs/deps、顶层 md5；`_compute_md5()==e9521a22111493406ea64a88cda63e0b`。固定 hash 是持久化兼容性契约，不能仅因精确值而称误拒。 |
| 显式默认 wdir 与无 wdir 等价 | **新增** P2P `TestStageChecksum::test_wdir_default_ignored` | 相同 mock 字典增加 wdir="."，仍要求 `e9521a22111493406ea64a88cda63e0b`。测 checksum 函数，不测真实 dumpd 或 Stage.load 路径。 |
| 非默认 wdir 应影响 checksum | **新增** P2P `TestStageChecksum::test_wdir_non_default_is_not_ignored` | mock 字典 wdir=".."，要求 `2ceba15e87f6848aa756502c1e6d24e9`。合理回归，但 mock 绕开绝对 self.wdir → dumpd 相对表示转换。 |
| 重载不擅改持久化 md5 | P2P `TestReload::test` | dvc.add 返回一个非 None stage；YAML 顶层 md5 改成 32 个“1”；load 返回非 None；dump 后 md5 原样保留。不是 old/new checksum 兼容验收。 |
| cmd schema 旧行为 | P2P `TestSchemaCmd::{test_cmd_object,test_cmd_none,test_no_cmd,test_cmd_str}` | cmd={} 应抛 StageFileFormatError；cmd=None、无 cmd、cmd="cmd" 的 validate 正常返回。 |
| deps/outs schema 旧行为 | P2P `TestSchemaDepsOuts::{test_object,test_none,test_empty_list,test_list}` | deps={}、outs={} 分别抛格式错误；分别允许 None、[]；允许 list 中 path+md5（含 None/缺省），outs 的 cache=True/False 也合法。 |
| 旧 `dvc add` .dvc 的 status 应恢复 clean | 冻结选集中无旧版本/手工历史固定 md5 的完整 Stage.load→status 断言 | 原因可从公开 source 定位，但 F2P 不直接证明原例。需加载已知旧 checksum fixture 做行为比较。 |
| 真实非默认工作目录与路径/缓存/运行行为 | 冻结选集中无真实非默认 Stage.dumpd 输入 | 相关公开 `tests/test_run.py:617–666` 已读：默认写 "."；fname 放子目录时 self.wdir 保持根、YAML wdir=".."；显式 wdir 忽略旧 cwd。该文件不在本次执行/参考集。 |

全部 test.patch 断言已展开：F2P 增两段；unit 增两个固定 checksum 测试；没有普通生产源码混入 test.patch。相关 helper/fixture 已读：TestSchema._validate_fail；tests/basic_env.py:13–116 生成小本地 foo/bar/code/data、临时 Git 仓库并 Repo.init；没有要下载 issue 示例大文件的测试依赖。

## 合理解误拒、自然部分实现与 gold 回归

**明确的替代路线疑点：**保留 dumpd 的既有绝对 self.wdir 表示，只在 `_compute_md5` 的局部字典中把绝对 wdir 按 self.path 所在目录转相对；对已相对的 `.`/`..` 输入保持原值，然后继续既有默认值排除规则。`dump()` 原本已正确写相对 YAML，无需变动；执行/输出解析仍使用绝对 self.wdir。它有能力修复旧 checksum，且应保留三个 mock checksum 契约，但必然不满足新增 `dumpd()[WDIR]=="."` 断言。题面要求 status 兼容，没有要求修改 dumpd 表示；故这是**有具体源码依据的静态误拒候选**，尚未写补丁/执行，不声称已有 RH2 reward=0 的对照。

**相反方向的具体漏测候选：**只把 dumpd 的 wdir 固定成 `"."`，保留其它方法。这是默认目录问题中可能出现的过窄修复：新 F2P 的默认例满足，原 dump 仍会把真实相对 wdir 写入 YAML；三个 unit 通过 mock dumpd 注入自己的字典，不能看到实际 dumpd 对非默认目录也返回 `"."`。因此真实非默认 wdir 可能不再影响 checksum，而冻结矩阵仍不能察觉。是否实际得到 reward=1 必须 CPU 回放；本轮仅提出该自然部分实现与非默认目录反例，不构造测试识别/硬编码测试 ID。

gold 选择在真正的 dumpd 统一相对表示，按源码能同时服务默认/非默认；比上面固定 `"."` 更完整。已追查 `is_cached:352–380` 对两个 dumpd 的比较；create:439–451 会先确定绝对 path/wdir；load 同样先固定路径；run/save、repo/add/commit/imp/lock/reproduce/metrics.modify 的 dump 调用；repo/move.py:45–66 在移动后更新 path/wdir 再 dump；OutputLOCAL.dumpd:57–68 按 stage.wdir 写相对 output 路径。未发现 gold 在这些内部调用路径的确定破坏。

全 base 的 `.dump(...)` / `.dumpd()` 检索未发现内部调用 Stage.dump 时提供 fname；所以 gold 去掉可选参数没有已找到的内部调用回归。它不由题面直接要求，外部 API 兼容未查，不能据此声称任意外部调用保持兼容。Stage 的 path=None 临时构造在 repo/move 只用来解析输出，没有看到对它调用 dumpd 的路径。没有全仓/平台穷举。

## 历史 RH2 原件

| 原件（相对 R） | 原始证据与适用范围 |
|---|---|
| `gold/ledger.jsonl:1`；`gold/eval_logs/evallog_replay-er19-dv1-iterativ_ed4fa666.eval.log` | log SHA256=343e328a…7d21f 与 ledger/run_refs 一致；:235–247 官方两文件恢复/应用成功；:388–410 兼容 wheels 离线安装；:542–551 editable 安装成功；:561–566 收集 13；:1469–1486 十三项全部 pass、rc=0；F2P1/1、P2P12/12、reward1。 |
| `noop/ledger.jsonl:1`；`noop/eval_logs/evallog_replay-er19-dv1-iterativ_ffddd94c.eval.log` | SHA256=da0ebba6…dc43f 一致；:520–525 同样收集13；:543–546 **实际先失败在 dumpd wdir 的绝对 /tmp 路径不等于 "."**；未走到该测试后面的 remove/reload 断言；:1404–1409 一失败/十二通过、rc=1；F2P0/1、P2P12/12、reward0。 |
| 两侧 recipe、诊断、projection/frozen、stage、driver | `awscli==1.15.85 PyYAML==3.13 colorama==0.3.9 rsa==3.4.2` 先以 --no-deps 安装，然后 `-r tests/requirements.txt`，再 editable `[all]`；日志用 /opt/rh2/build-wheels；安装失败命令为空，rc=0；只 source 投影，无排除路径变更；官方恢复2；清理成功，无 driver 残留。 |

派生镜像 `sha256:d71db46cbc0fdd24b26db0202e326bc9ec9764b07b19704fb293383849220a70`；Python3.8.19/pytest7.4.4；执行 grader 是 rh2grader/54322、deny_all、2 CPU/4 GiB、64 MiB shm、可写 `/opt/miniconda3/envs/testbed`。工作区 import 路径由 ledger 观察到 `/testbed/dvc/__init__.py`。import 版本 `0.30.0+9175c4.mod` 与安装分发 metadata `0.30.0` 是不同观察项，不混成不同 base。env_qualification=absent。

唯一 F2P 加上的表示断言将原 roundtrip 测试变成失败；原来“当前创建→删 wdir→当前读取”两侧都可用同一绝对路径生成 checksum，因此该 roundtrip 本身不足以发现跨旧版本兼容缺陷。这一说明来自源码与失败位置；没有借旧质量报告佐证。历史 reward 1/0 只证明这 13 项的本次分离。

## 开发条件和交付/评分边界

| 必需操作/资产 | 公开依据 | 现有证据/当前缺口 | 最小后续命令或操作（未执行） |
|---|---|---|---|
| 定位 status/Stage/checksum，导入工作区 | stage.py、repo/status.py、utils；setup.py | 源码入口清晰；只有历史 grader 导入证据 | actor 实际 bash 输出 id/cwd/PATH、sys.executable、dvc.__file__ 与版本。 |
| 运行公开窄测试与本地 legacy fixture | tests/test_stage.py、tests/unit/stage.py、basic_env.py | 只需 Python、pytest/mock、Git、shell echo、YAML 与 DVC 依赖；本地小文件即可 | `pytest -rA tests/test_stage.py tests/unit/stage.py`；再对固定旧 md5、默认/非默认目录做 load→status/changed_md5 对照。 |
| 依赖准备/安装 | setup.py 的 `[all]` 与 tests/requirements.txt；旧 boto3==1.7.4 | 09-19 SDK pins 与离线 wheels 已有成功；原公开 actor 镜像是否具备它们未知 | 在准备阶段固定同配方；不能默认 actor 能公网补包或写 grader 的 conda 前缀。 |
| 临时仓库/缓存写入 | TestDir/TestGit/TestDvc 与运行源码 | 合法资产是生成的小文件/临时 Git 仓库，不需 issue 中的大文件、外部服务或新编译目标 | 核 agent 的 /testbed、HOME、tmp 可写以及 Git 配置；运行窄复现区分导入故障和目标 checksum。 |
| 交付修复 | 合理解可限于 dvc/stage.py | gold source 实际被投影；无需修改测试或无法提交资产 | 验证 source delta 生效并重复行为对照，测试 fixture 只作诊断。 |

当前 RH2 `prepared_task_face.py:312–355` 用 test.patch 的精确两文件做恢复：`tests/test_stage.py`、`tests/unit/stage.py`，`test_globs=()`；不是所有测试名字都被排除/恢复。test.patch 没有生产源码。旧 public_hints 的“所有测试改动不计分”不能代表当前机制，实际提示渲染仍未捕获；本题合理 source 修复无需改测试，不以此请求或假定可违背旧操作指令。无 additional_exclusions 建议。

评分依冻结1 F2P+12 P2P，恰好对应该选集13节点；不是完整项目回归集。其它公开 test_run 非默认路径测试即使另行运行，也不能无说明当成冻结奖励标准。一般完整 pytest 的非参考断言失败不自动将 reward 降为0，全局收集/启动失败另查 manager。

正式 actor 仍从 public bundle 取 public 镜像/digest；回放的派生镜像、grader54322 的前缀可写性与 `apply_user=agent/54321` 均不是正式 agent54321 工具会话证明。共用卡及源码的 `/root/.rh2_bash_env`、隐藏 /root 只形成实际激活/PATH 待核项；不能宣称已坏或已修。公开静态导出无 .git 不表示真实镜像没有答案线索；Git sanitize、实际资源/CLI工具/消息与公开镜像资产未逐题验收。

## 八方面状态与唯一优先下一步

| 方面 | 本稿覆盖/限度 |
|---|---|
| 公开需求 | 旧 metadata 向后兼容、默认/非默认和数据 checksum 区分；公开材料能定位根因。 |
| 材料/初始问题 | S2/base/patch/回放身份、全部220个base文件哈希一致；未跑原例大文件。 |
| 测试要求 | 全部新增/修改断言和13参考展开；真实 legacy checksum 与真实非默认 dumpd 缺覆盖。 |
| 合理解误拒 | checksum 内正规化而不改 dumpd 的路线有明确依据，待 CPU 证明行为与分数分离。 |
| gold/回归 | load/create/save/is_cached/dump/move/output 调用链与公开非默认路径测试已查；无确定 gold 回归，不宣称穷举。 |
| 开发条件 | 本地小资产/导入/安装需求已给；历史 grader 成功，当前 actor 权限、激活和依赖未知。 |
| 交付/评分 | source 投影和精确测试恢复已核；无新路径排除或安全结论。 |
| 题目关系/用途 | 同仓另外两题不同目标，未证派生关系；gold/隐藏测试已暴露，不能复用为公开 solver；无模型成功率推测。 |

唯一优先下一步：在同一明确配方上做一组双向 CPU 对照——base、gold、仅在 `_compute_md5` 正规化的合理替代解、dumpd 固定 "." 的自然部分实现；用已知旧无 wdir checksum fixture 和真实非默认目录测试判断公开兼容行为，再分别记录13项冻结得分。若误拒或漏测成立，优先增加行为层 legacy/non-default 验收并重新判断内部表示断言，不能为了保 gold 而把内部实现要求补进题面。正式 actor CPU 验证另列，未完成前不是 ready_for_probe。

本轮项目 CPU 未运行，token/费用无工具观测，记 null。三题初稿完成后遵守全包门禁暂停，等待第二阶段明确开放；不改本初稿、不读取他人结论。
