# D6 两题 CPU 正式验收运行说明

整理：2026-09-29。**状态：脚本已准备，未连接远端、未启动容器、未执行六行评分。** 本页对应 [实施 Brief](implementation_brief.md)；不是通过回执，不授予训练资格。根线程审核冻结代码和 runner 后执行，不需要重新请求用户批准本轮范围。

## 运行什么、如何判读

首片只运行 `python__mypy-10424`、`python__mypy-17071`。每题按 noop → gold → C1 顺序，经正式 `TrustedTaskController` prepare、候选 agent 身份投影、冻结导出、正式 `SWEGradingManager` 评分，预期奖励分别为 0、1、0。并发为 1；每题独立 context、manager、run ID 和 `rh2.d6.<run-id>` label 前缀。

runner 位于 `runs/category2_repair_20260929/tools/d6_acceptance_v1/`：

- `seal_code.py`：给负责人已经冻结的 `code_v1` 建逐文件 SHA 清单；不复制代码、不修改材料。
- `run_acceptance.py`：默认仅受信 prepare 与材料／dispatch 核对；只有显式 `--execute` 才访问 Docker 和评分。
- `launch_detached.py`：以独立进程 session 启动命令，保存 PID、完整 stdout/stderr 和原始 argv；不执行 SSH。

**正常结束与验收通过分开。** `recordmanifest.json` 的六行自动检查成功仍标为待独立复核和 actor 补验；不要把进程退出 0、reward 1 或容器清零当成最终验收。每题三行原／新增参考投影位于各自 `review.json` 与 manager 的 `diagnostics.json`。完整测试失败应是预期断言失败，不能由导入、收集、安装或资源故障替代。

## 执行前必须已有的事实

1. 新 D6 生产改动与修订材料已经审阅；将本次工作区的有效快照冻结为 `/work/category2_repair_20260929/d6/code_v1/`。里面保留仓库相对布局：`rh2/src`、CLI 与依赖的 `docs/.../s2/` 原件／新产物、修订单和本题材料 manifest。不要从旧 HEAD 取回旧 barrier；根线程已说明当前 `root_git_boundary_fix_20260929` 已验快照需要纳入冻结。冻结清单放在 `code_v1` 外，不要在运行期间改它。
2. 私有补丁按原相对路径放在输入根之下：`runs/category2_repair_20260929/swe_materials/first_mypy_bundle/...`。runner 对 manifest 登记的全部冻结材料核 SHA 与 bytes；不会拿这些补丁替换正式 grading bundle。实际评分材料只来自冻结代码的受信 loader。
3. 运行 Python 已安装当前 RH2 依赖（含 `pydantic`、`swebench`）；可以复用远端旧 `code_v1/rh2/.venv/bin/python` 作为解释器，**导入源码仍强制使用本次新冻结树**，并记录解释器路径、Python 与包版本。解释器复用不表示旧代码复用。
4. 两张本地镜像及其基础镜像存在。以下 ID 已由根线程提供；本脚本不构建、不拉取镜像。派发前核 tag→ID、基础层继承和离线 ENV，两侧容器均以完整 image ID 启动。

| 题目 | tag | 本次派生 image ID |
| --- | --- | --- |
| 10424 | `rh2-category2/install-wave1-python__mypy-10424:20260929-v2` | `sha256:64472be326bc6cb14d3fb3beea3bd6ac8f71bab29c159c6e92538adcbe55c27f` |
| 17071 | `rh2-category2/install-wave1-python__mypy-17071:20260929-v2` | `sha256:0111b5f8ac2ce898b81259d9dedc5aad1aa4059ac0f69a446073c2c3e8deffba` |

安装复用依据是 [installation_reuse.json](../swe_materials/first_mypy_bundle/installation_reuse.json) 和 `runs/category2_repair_20260929/remote/image_prepare_v2/`。10424 镜像初态对 `test-requirements.txt` 的修改属于原镜像，不能 reset 掉。本轮 `DerivedImage` 正式 replay 路径同时控制候选和 grader 镜像；不用 R2E 专用 overlay 字段伪造 SWE 事实。

## 根线程执行命令

以下命令在远端已有授权的 `/work/category2_repair_20260929` 执行；本说明没有发起 SSH。`D6_PY` 必须填实际已验证的运行解释器，`D6_INPUT` 是保留 `runs/` 相对布局的材料输入根。清单 SHA 必须在核审冻结文件后由根线程填入，不能使用未经检查的旧清单。

```bash
D6_ROOT=/work/category2_repair_20260929
D6_TOOLS="$D6_ROOT/tools/d6_acceptance_v1"
D6_CODE="$D6_ROOT/d6/code_v1"
D6_INPUT="$D6_ROOT/d6/input"
D6_PY=/work/category2_repair_20260929/code_v1/rh2/.venv/bin/python

"$D6_PY" "$D6_TOOLS/seal_code.py" \
  --code-root "$D6_CODE" --out "$D6_ROOT/d6/code_v1_manifest.json"

# 将上一步输出、经根线程核审的 SHA 填到这里。
D6_CODE_SHA='<reviewed-code-manifest-sha256>'

"$D6_PY" "$D6_TOOLS/run_acceptance.py" \
  --code-root "$D6_CODE" \
  --code-manifest "$D6_ROOT/d6/code_v1_manifest.json" \
  --code-manifest-sha256 "$D6_CODE_SHA" \
  --input-root "$D6_INPUT" \
  --out "$D6_ROOT/d6/prepare_review_v1" --run-id d6-mypy-prep01

"$D6_PY" "$D6_TOOLS/launch_detached.py" \
  --dispatch-dir "$D6_ROOT/d6/dispatch_v1" -- \
  "$D6_PY" "$D6_TOOLS/run_acceptance.py" \
  --code-root "$D6_CODE" \
  --code-manifest "$D6_ROOT/d6/code_v1_manifest.json" \
  --code-manifest-sha256 "$D6_CODE_SHA" \
  --input-root "$D6_INPUT" \
  --out "$D6_ROOT/d6/cpu_acceptance_v1" --run-id d6-mypy-cpu01 --execute
```

预检查与正式运行分别输出到新目录；已经存在就拒绝，不续写历史结果。正式运行再次走同一个 controller，所得 prepared manifest 的生成时间可以不同，材料内容身份必须相同。`dispatch_v1/stdout.log` 是未截断宿主输出；运行期间只需读取 `status.json`，最终读 `recordmanifest.json`。若需要终止，向 `dispatch.json` 里的 PID 发送 SIGTERM；runner 会停止后续派发并进入有界清理。不要 `kill -9` 后宣称已完成清理。

当前 timeout 沿用生产默认：候选阶段 900 秒、grader reset／可信 setup 300 秒、测试 1800 秒、单次评分总期限 3600 秒、候选／manager 单容器清理 120 秒；manager 总收尾外层 guard 为 300 秒。CPU／内存／PID 默认分别为 2 CPU、4 GiB、512，实际 profile 与摘要落盘。它们是技术限时和资源约束，不是用户总预算。若观察到 setup 300 秒不足，保存失败事实再按根线程允许的 900 秒窄调整另开新版本；本版不默认扩大它。

## 自动核对与独立审阅入口

每行目录为 `<out>/<instance_id>/{noop,gold,C1}/`，每题 spec 与 manager 清理记录在上一层。

| 入口 | 必须核实的事实 |
| --- | --- |
| `recordmanifest.json` | 新冻结代码清单 SHA、runner 脚本 SHA、私有候选 SHA、两题镜像 ID、解释器与依赖版本；严格6行；没有复用旧资格。 |
| `prepared/`、`private/` 与 `<iid>/spec/join.json` | 新有效 bundle 的环境／公开／评分摘要；正式 actor `PreparedTaskFace` 与 replay builder 的脚本、材料和 hygiene 一致；错误 dispatch 环境摘要被拒绝。 |
| `<iid>/spec/*.sh` | 实际完整命令保持 vendor 前缀，只扩大登记的 mypy case 并集；原／新增测试恢复和保护范围；候选安装两段与默认整段脚本均可核。 |
| `<iid>/<variant>/artifacts/` | agent 身份写入的真实候选、baseline、frozen patch、classification 和 projection；候选 image ID 与 frozen projection digest 一致。 |
| `<iid>/<variant>/report.json`、`ledger.jsonl` | 完整公共 report 与正式 replay 行；`swe_f2p_p2p`／`binary_v1` 不变；0/1/0 和失败归因符合预期。 |
| `<iid>/<variant>/review.json` | 实际逐节点状态、pytest 收集计数行，准确3/5节点；原F2P／原P2P／新增P2P分别列示；无缺席、skip或非参考额外节点。 |
| `<iid>/eval_logs/*.eval.log` 与 `*.diagnostics.json` | 完整安装／测试输出、所有 ERR trap 失败子命令、真实测试RC和终止、phase耗时与资源事实；不能用安装段末RC0抵消前面失败。 |
| `<iid>/<variant>/supplemental_observation.json` | 同一实际 grader 在正式测试后、清理前，以 rh2grader/54322 导入目标模块；导入路径和SHA与冻结源码一致；新增测试文件恢复到base SHA、root属主、候选不可写。 |
| `<iid>/manager_close.json` | 候选行 `cleanup.removed=true`，manager最终无未关容器，本run label残留查询成功且为空；查询超时／失败必须视为未知并停派。 |

补充观察复用原 manager 的 `_observe` 收口点，只在 `post_candidate_observation` 后执行一条独立、20秒限时的候选身份命令，原观察返回值原样交回。**不改变任何评分 spec、脚本、parser、参考、reward 或资格摘要。** 原始输出单列，不进入评分解析。若实际加载 `.so`，本版自动核对会失败；必须另补该编译产物确由候选源码构建的窄证据，不能把 `.so` SHA假称源码SHA。

10424 的目标模块是 `mypy.checker`、`mypy.meet`；17071 是 `mypy.typetraverser`。新增保护文件分别是 `check-isinstance.test` 与 `check-typevar-unbound.test`。私有 gold 和 C1 始终只用于受信验收，不进入 actor 的公开命令清单。

只改参考时 public digest 可以不变。现有候选代码工件可以在明确的新材料下重评分；环境身份由同次 prepared → host grading → assignment → spec／ledger 连接到 frozen projection。**本 runner 不声称 FrozenPatchArtifact 本身已经携带 environment digest，也不伪填这个公共字段。** 正式消费层的旧prepared／新host、旧dispatch／新材料混配反例由实现者测试覆盖，运行记录链接本次真实身份。

## 两题 actor 证据与最小补验

可复用旧入口是 `rh2/experiments/task2_swegym_dev_20260925/devcheck.py` → `base_probe_fixes_20260923/acceptance_startup_2.py` → 正式 `ClaudeCodeDriver.run` 和桩端点。两题旧证据分别在 `runs/task2_swegym_dev_20260925/runs/mypy10424/orig/`、`mypy17071/orig/`。二者都有真实 CC 2.1.205、agent/54321、`/opt/miniconda3/envs/testbed` 激活、prelaunch成功和容器／网络清理。10424 相关公开测试为133 passed/1 skipped；17071为135 passed/1 xfailed；题面原例均如期返回非零。不能把这些全量成功数写成此次新增节点验收。

旧证据不覆盖本次离线wheel派生层、D6材料身份或正式冻结消费；旧 `devcheck.py` 还会只保留200KB尾部并删除完整文件，`Runner.run` 只调用driver、没有正式freeze。因此不直接复用它的“完成”标记核销D6。旧 `checks.bashenv_denied_for_agent=false` 也不能改写成全项通过；其命令清单未实际覆盖该检查，要以当前真实权限证据说明。

最小新增安排是**每题一次真实 CC＋独立桩实例**，不需GPU、付费模型或再做六次评分：

1. 用本次prepared公开面、新代码和确定的派生image ID。按正式profile、非交互shell、agent身份启动；记录CC tarball SHA、prelaunch、激活、实际模块来源及完整输出。
2. 桩只下发公开开发命令：Python/pytest/身份；按既有安装次序逐条执行、逐条RC落盘；运行本题新增的公开case并保留完整pytest输出。base上新增P2P应通过；不把gold、C1或私有评分清单传给CC。
3. 对干净公开行为导出真实冻结工件，使用当前无root Git的quiescence barrier、baseline census、`export_frozen_patch`、classification/projection；保留公开诊断文件只写 `/tmp`，避免给代码delta添无关文件。
4. 将已注册的分派身份经正式 `PreparedTaskFace.grading_spec()`/bringup resolver核对到D6材料，再核冻结projection与该调用的关联。六行正式replay已验完整grader，可以只补真实CC导出与新材料join；不为证明相同spec再次机械复制矩阵。
5. 两题都核完整清理；缺日志、安装失败、激活或源码不符就停在未验状态。

**当前具体缺口：**仓库旧devcheck没有“完整日志保留＋正式quiescence/freeze＋注册dispatch的grader join”这一整体入口。runner中的`PreparedTaskFace`真实加载/错身份拒绝是静态transport核对，不能冒称上述真实CC链路已验。需要根线程选择复用本轮生产冻结验收入口，或对旧devcheck做仅记录与冻结扩展后再跑这两次；本文件先交六行矩阵，不用未完成的actor扩展阻塞其审核。

## 本次本地校验范围

已对三个Python脚本做语法检查、CLI help核对，对两条生成的补充观察脚本执行`bash -n`。另用两题合成日志验证准确节点／收集数、安装末RC0但前面子命令失败仍拒绝、参考SKIPPED仍拒绝；结果和脚本SHA记录在工具目录`local_validation.json`。未运行远端、未启动容器、未拉取镜像。冻结代码尚未由本子任务生成，受信prepare与六行真实运行待根线程执行。独立review必须核本页列出的新证据，再逐题决定是否达到D6验收条件。
