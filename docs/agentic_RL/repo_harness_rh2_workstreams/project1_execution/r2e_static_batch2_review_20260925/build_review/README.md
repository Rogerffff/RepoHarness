# orange3 4014 构建、交付边界与 R1/O1 聚焦复核

2026-09-25，Codex 独立子审。只读源码与已有证据，新增本目录探针和报告；未修改业务、维护测试、材料、账本或历史 evidence，未运行 Docker/SSH/网络，未提交。输入 HEAD `83760b15ae408f5ee6a118402a435b0123ea3c39`，包括既有未提交 B 线代码；16 份相关输入摘要见 [input_snapshot.json](input_snapshot.json)。本报告只负责 orange3 `4014f248` 的构建与交付、上一轮 R1/O1；其余 11 题的语义和全批 81 行统计由主审负责。

## 1. 结论

- **C2 是有证据支持的合理源码修复**：正式回放只应用 `.pyx`，26/27、reward 0；同镜像中以 root 实际重新 Cythonize/编译后，27/27。这个对照足以支持“源码修复需要构建才生效”，不能因 root 与正式评分身份不同就否定它；它没有证明 agent 构建或正式 actor 全链完成。
- **orange3 此次默认重建的环境缺陷成立**：agent 54321 已实际编译到链接阶段，链接命令引用不可读的 `/root/.../lib` 并找不到 `-lpython3.7m`。这不是只检查 `sysconfig` 的理论反例，也不是 base 上复制已有 `.so` 的伪重建。
- **有两处 P2 报告口径需收窄**：把 Git 兼容导出脚本当成当前 `fa_formal` 导出，错误推断 `.gitignore` 一定丢掉二进制；把一题一条默认构建命令的失败推广成所有仓库所有 C 扩展都无法构建。前者会直接误导“是否必须增加 grader 重建”的决策。
- **R1/O1 在原 finding 范围内 accepted / fixed**：批准配方内容绑定与单次字节读取闭环。本轮 15 项 CPU 探针、相关五份维护测试 68 passed；未据此声称镜像已重建、所有开发条件完备或 Qwen actor 已验收。

## 2. 既有实跑事实及其层级

路径前缀：`runs/r2e_actor_20260925/`；`devcheck` 本题目录缩为 `orange3__4014f2483e3bab0621c9ae0f994947c/`。

| 证据 | 实际执行与结果 | 能证明 / 不能证明 |
| --- | --- | --- |
| `grader/ledger_o4014_C2_pyx_only.jsonl:1`，及其中关联的 `eval_logs/evallog_replay-a9d37fc8d56d-oran_e45af2b2.eval.log` | 同镜像 ID `sha256:22558531…`；候选以 agent/54321 `git apply`；评分 54322；冻结投影只有 `Orange/preprocess/_discretize.pyx`；`install_skipped=true`；26/27，只有 `TestEqualFreq.test_below_precision` 失败 | 证明此次源码补丁未自动构建、在正式回放得 0。并非“构建成功后 `.so` 被 exporter 丢弃”的实验 |
| `grader/private_regrade/o4014_C2_nobuild.json:5–19` | root，不构建，26/27 | 同一私有复核方法的负对照 |
| `grader/private_regrade/o4014_C2_build.json:5–19` | root；`.venv/bin/python setup.py build_ext --inplace` 返回 0，记录 `[1/1] Cythonizing Orange/preprocess/_discretize.pyx`；27/27 | 证明 C2 源码确实被编译且本题期望全部通过；未覆盖正式身份、预算、冻结运输 |
| `grader/private_regrade/o4014_gold_build.json` | root；同构建命令返回 0；27/27；无本次 Cythonizing 记录 | gold 正控。不能将其作为修改 `.pyx` 后真实重编译的证据 |
| `devcheck/.../agentpath/captures/build.out:1–9` | agent 修改 `.pyx` 后执行构建，`BUILD_RC=1`；Cythonize 与 C 编译已进行；C 编译使用 `/opt/py/.../include/python3.7m`；链接使用 `-L/root/.../lib -lm -lpython3.7m` | 明确区分头文件可达与链接库目录仍旧。未验证额外链接参数或替代构建方式 |
| `devcheck/.../agentpath2/captures/build_full_error.out:1–7`、`linker_facts.out:1–9` | 第二次记录同样链接失败；`LIBDIR` 是旧 `/root` 前缀，`/root` 权限 0700，agent `ls` 被拒；新 `/opt/py/.../lib` 有 `libpython3.7m.so/.a` | 指向搬迁遗漏的直接证据。对“root 能读旧目录因而成功”的解释与 root 正控一致，但未做仅改变一个参数的因果干预 |
| `devcheck/.../orig/captures/pr9_8_cmd.out:1–12` | base 未改源码，仅 `running build_ext` 与复制已有 `.so` | 只能证明这次复制命令成功；作者已在 `grader_candidates.md:142` 撤回早先“agent 可重编译”结论，该更正正确 |

独立复核已重算 C2 补丁与正式 eval log 的 SHA-256，并用当前 parser 对日志及三个 root 复核结果的完整状态尾段逐键重算；均与原结果一致，见 [probe_result.json](probe_result.json):5–68。root 结果保存的是日志尾段；其中 27 个状态键完整，未宣称拥有未保存的全量构建输出。

公开源码也支持合理性：`.../v3/public/<iid>/worktree/Orange/preprocess/_discretize.pyx:16–17,31–57` 的两个返回都可能带重复切分点；C2 两处都做 `sorted(set(...))`，不人为舍入数据。`Orange/preprocess/discretize.py:147–151` 把其结果直接交给 `_fmt_interval`（同文件 51–53）使用。它与题面 `user_prompt.txt:26–30` 的唯一阈值需求一致；本结论不是“所有输入上的形式化正确性证明”。

## 3. 当前生产调用链：源码补丁与构建后文件树是两种输入

### 3.1 实际链路

1. **任务面**：`prepared_task_face.py:432–449,505–511,609–615` 选择派生 image ID，rollout 和 grader 使用同一派生镜像。当前测试不变的 `.venv` 是环境，不属于候选文件 delta。
2. **基线及候选树**：R2E policy 在 `contracts/baseline_manifest.py:122–125` 只排除 `.git/`、`.harness/`、`.venv/`，并省略 `__pycache__`、`.pytest_cache` 目录。`baseline_census.py:52–94` 枚举其它普通文件/软链，完全不读 `.gitignore`。
3. **正式 actor**：`generate.py:3408–3417,3479–3489` 在 `fa_formal` 静止屏障后调 `export_frozen_patch`；`patch_exporter.py:169–173,251–299` census、比较内容摘要，再以 base64 携带新增/修改字节。`.so` 与 `.o` 都是支持的普通文件。
4. **正式回放**：`replay_grade.py:369–388` 对传入文本补丁以 agent 身份应用后直接调用同一 exporter。C2 输入文件本来只有 `.pyx`，且应用与导出之间没有构建步骤，所以这次 frozen artifact 也只有 `.pyx`。这是这次 0 分的确切运输前提。
5. **投影**：`r2e_grading_scripts.py:275–278` 设置隐藏文件/入口精确控制面，`test_globs=()`；`trusted_projection.py:170–200` 按排除法保留其余候选条目。普通的 `Orange/preprocess/*.so`、`_discretize.c`、`build/.../*.o` 均可进入 candidate。
6. **fresh grader**：`manager.py:1811–1818,1861–1870` 校验 baseline 后重放冻结 delta；`2748–2839` 对普通文件解码并经 stdin 原字节写入，`build_delta_write_command:500–522` 明确二进制安全。它没有按扩展名丢弃二进制。
7. **评分运行**：`r2e_grading_scripts.py:117–126` 仅写 `RH2_INSTALL_SKIPPED=1` 然后运行可信 `run_tests.sh`；本题 `v3/private/<iid>/run_tests.sh:1` 只有 pytest。没有自动 C/Cython 重建。

结论是：**仅交付 `.pyx` 且 grader 不构建，会继续使用旧扩展；如果解题者已经在可评分树内成功生成新的 `.so`，当前正式冻结链具有运输该二进制的能力。** 后一种需要实际 agent 构建成功再验证完整链，不能由本报告冒充已实跑。安装到 `.venv` 内的变化仍按既有环境排除语义不运输。

### 3.2 BR1 / P2：误把 Git 兼容导出当成正式冻结路径

- **当前行为 / 位置**：批次二 `grader_candidates.md:144` 及 `commands/agentpath_orange3_4014.json:41–49` 将 `manager.EXPORT_PATCH_SCRIPT` 的 `git add -N` / `git diff --binary` 标作正式导出，并用 `.gitignore` 推断 `.so`、生成的 C 和 `build/` 不交付。
- **违反的不变量**：审查结论须对应当前可达生产消费者（G/F/M）；`manager.py:1804–1837` 已将 frozen delta 与旧 workspace Git 导出分成互斥路径。
- **证据 / 可达性**：上面 3.1 的 `fa_formal` 分支与回放分支均使用 census。不是未来能力；`s1_compat`/无 frozen 输入的 Git 路径仍存在，但不等于本题正在验证的正式冻结路径。
- **影响**：把“这次只给源码且没构建”误说成“任何 actor 编译产物都交付不了”，从而错误收窄修法、把 grader 自动重建描写成解决该题的唯一方向。`base_untracked.txt` 是否存在也不能说明 frozen 路径会掺入未变化的 `datasets/install.sh`；这些初态文件已在 baseline，未变化时不产生 delta。
- **复现**：本目录 `probe.py`，以本题真实 `.gitignore` 和 R2E policy 在临时真实文件树中调用生产 census/export/classifier/投影，然后调用真实 `_apply_frozen_delta` 应用循环。变更的 `.pyx/.c/.so/build/*.o` 全保留、原字节重放；未变化的 `datasets` 不导出。探针只替换命令运输为本机 shell，**`.so/.o` 为哨兵字节，未运行编译器或导入模块**。
- **分期 / 最小修法**：本轮报告口径修正，T1 强报告；无需修改 exporter、评分或增加 guard。原始 C2=0 与 root=27/27 全保留。
- **验收**：明确 `fa_formal` 与兼容 Git 路径，去掉 `.gitignore` 必然丢失正式编译产物的论断；后续如果选择“agent 构建后交付”方案，另以真实改动后的 `.so` 摘要贯穿 actor artifact→fresh grader→导入与目标键验证。

### 3.3 BR2 / P2：构建失败范围被全称化

- **当前行为 / 位置**：批次二 `README.md:72` 写“agent 身份下重建任何 C 扩展都在链接时报 `cannot find -lpython3.7m`”，并覆盖 orange3/pandas/numpy/pillow；同页 57 行与 `env_data_eval.md:220` 沿用这一范围。
- **违反的不变量**：实测范围与推断范围需分开（A/G/N）；文件后缀不能替代真实解释器、构建器和链接参数证据。
- **证据**：真正执行失败的是 4014/C2 的 `python setup.py build_ext --inplace`。观测的配置只有 `LIBDIR/LDLIBRARY/BLDLIBRARY`。日志确实证明该链接命令使用旧路径、agent 不可读；并未测每个扩展，也未測显式传入可访问 `-L`/库搜索路径的构建。`pillow__3a61…/orig/captures/env.out:5` 和 `pillow__2b06…/orig/captures/env.out:6` 已显示 `cpython-39` 产物，不能把 orange3 的 `-lpython3.7m` 当成它们的实际命令。
- **影响 / 可达性**：这个缺陷在本题默认构建路径当前可达，需保留为真问题；其他题可登记同源风险或待抽查。全称结论会提前排除编译类候选、夸大所需修复范围，实际频率仍未知。
- **最小修法 / 分期**：本轮把摘要改成“orange3 4014、Python 3.7.9、当前派生镜像的该默认构建命令实测失败；其他解释器/构建方式尚未验证”。无须为收窄报告增加运行时检查或剔题规则。
- **验收 / 复现**：本目录 probe 校验上述两份 agent 日志；对其它仓库如要报“已实测”，至少保存一次修改实际编译源文件后触发编译/链接的完整命令与错误。只打印 sysconfig、dry-run、成功导入旧 `.so` 或复制旧产物均不足。

## 4. R1/O1：原问题在限定范围内收口

| 项目 | 独立核对 | 裁定与边界 |
| --- | --- | --- |
| R1：环境步骤名不能代表批准依赖内容 | `environment_overlay.py:55–80` 现要求批准摘要 `512277…`；`build_r2e_derived.py:201–220` 摘要覆盖 recipe、env step、wheel 内容摘要；`499–502` 在 Docker 前核对。实算摘要等于 `derived7/overlays.jsonl` 与 orange3 9b54 `facts.json` 的真实值。相同步骤名/错摘要被拒；错误依赖构建走到拒绝而不接触 Docker | **accepted / fixed**。闭合“env_v2 任意依赖也可过”的漏洞，不声称仅靠自报摘要重新证明镜像所有内容。镜像 ID/来源绑定仍沿既有可信覆盖表边界 |
| 共同消费者 | `prepared_task_face.py:407,505–510` 先互检再建正式任务面；`replay_grade.py:780` 的 `_overlay_static_mismatch` 调相同互检；构建调用同一要求 | 无需给 actor/replay 增加第二套要求表；现有维护测试验证原入口链及材料运输 |
| O1：核摘要与解析分别读文件 | `load_overlays_input` 在 `prepared_task_face.py:466–471` 一次读 bytes，核摘要后直接解析该 bytes；新 `parse_environment_overlays` 在 `environment_overlay.py:115–131` 不读文件 | **accepted / fixed**。对真实 derived7 overlay 记录 `read_bytes` 恰一次，同时禁止同路径 `read_text` 仍通过；闭合原 TOCTOU，而非泛化为所有输入读取都已审计 |

维护测试：原复核同五份文件，**68 passed，0 failed / skipped**，见 [targeted_tests.txt](targeted_tests.txt)。其中构建反例到 Docker 边界即停；没有实际调用 Docker。运行命令（`rh2/`）：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/adapters/test_r2e_actor_task_face.py \
  tests/adapters/test_r2e_replay_overlay.py \
  tests/envpack/test_build_r2e_derived_env.py \
  tests/envpack/test_ingest_r2e_subset.py \
  tests/adapters_miles/test_r2e_group_transport.py -m 'not docker' \
  --basetemp=../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_batch2_review_20260925/build_review/pytest_tmp
```

## 5. 最小后续、分期与停止条件

| 事项 | 分级与建议 | 最小验收 / 停止条件 |
| --- | --- | --- |
| 本轮报告事实边界 | BR1/BR2 先修口径，不改历史实验或 reward | 明确 root 构建、agent 默认构建、源码补丁回放、正式冻结产物四个证据层；完成即足够继续余题静态审查 |
| 4014 开发环境修复 | **T1 工程修复**：若仅把搬迁遗留的构建配置改指向同版本 `/opt/py` 副本，保留权限、材料、依赖版本和评分阶段，这是恢复解释器搬迁的完整性；不能只因“环境配方”就自动升 T0。用户“先不修”与本轮只读授权仍然有效，此处仅提出分期 | B 环境 owner；在将本题当作允许 Cython 正常开发的 actor 题之前，uid 54321 修改 C2 后真正 Cythonize/编译/链接、导入新 `.so`、题面复现通过。先用可访问的库搜索路径做单变量诊断，再决定修 `LIBDIR` 及哪些实际消费者还用到旧前缀；不需要放开 `/root` 权限 |
| 配方身份联动 | recipe 内容改动会改变 composite digest；R1 正在正确拦截未批准新摘要 | 新配方/新 image ID 留新证据，不回写旧 derived7；涉及 mr-020 的同配方镜像重新核其批准语义后更新摘要。不要为恢复测试绿色直接放宽摘要要求，也无需不加区别重跑全池 |
| 是否增加 grader 自动重建 | **deferred T0**：R2E 接线计划 `r2e_grading_wiring_20260920.md:113` 已明确无安装段、源码改动不会自动重建。新增阶段会改变可得 reward、构建失败归因及时间预算，需要用户选择；不能在修环境时顺带加入 | 先区分继续运输 agent 已构建产物、允许源码交付并由 grader 构建、继续仅作诊断三种方案。若选自动重建，候选构建代码须在现有候选身份 54322 与预算下运行，不能放到 root 可信 setup；另验 noop/gold/C2 与构建失败分类 |
| 已成功构建产物的正式评分 | **experiment-required**，不是当前 exporter 新功能需求 | 环境修复后做一题真实 actor/或等价冻结链：新 `.so` 摘要进入 frozen artifact 并被 fresh grader 原样重放、实际导入该路径、27 键对齐。CPU 哨兵不能替代该实验；也不因未做而推翻现有 root 构建证据 |
| 其它仓库 C/Cython 范围 | 先登记，不当已实测失败，不新增统一拒绝/排除 guard | 如下阶段要用其编译开发能力，按实际 Python/构建器选少量代表题，保存真实修改→编译/链接→导入事实。未进入这类运行方案时可递延 |

本轮没有需要阻塞继续静态审查的新 P0/P1，也没有要求立即实施的新增 T0。R1/O1 在本报告范围收口，不为“还可以设想的错配”继续扩守卫。已有 rollout E2b 可信 PATH 修复已由 A 在 `b169c10e` 实施（`infra.md:1175`）；grader 侧 E2b 属 B 在制品与后续聚焦验收，本报告未重新审查该安全边界，不把它写成“两侧均未做”。

## 6. 维度覆盖与验证限度

| 维度 | 本轮依据 |
| --- | --- |
| A / G | 真实 agent 编译与链接日志、root 正反对照；追到 actor/replay→census→projection→manager 字节应用；15 项 CPU 探针 |
| B / F | 源码仅交付与构建产物交付分开；无自动重建是当前已记来源限制；不新设编译题拒绝或剔除规则 |
| C | 未新增挡板；后续按实际用途选择验收，静态审查不被扩展成全池构建闸门 |
| D / H | B 持有环境配方；共同 `env_requirement_mismatch` 唯一内容要求；R1 摘要与真实 derived7 记录一致；O1 单次读取 |
| E | 私有 root 构建有 Cythonizing，base 复制没有；本机二进制哨兵只验证运输，不冒充构建；68 项定向维护测试 |
| I / K | 环境搬迁窄修可先于自动重建选择；不新增长期 owner/状态机；分期与停止条件见 §5 |
| J / M | 修正“正式导出”“任何扩展”两处注释/报告与实际行为的不一致；保留原始 reward 和层级 |
| L | 未增加热路径，也未测真实编译成本或大产物开销；若自动重建/实际二进制纳入运行方案，成本随那次试验记录，不以 CPU 小夹具外推 |
| N | 已见 Python 3.7 / 3.9 差异，按解释器与构建参数界定外推；未验证其它构建后端/链接器组合 |

探针复现（`rh2/`）：`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_batch2_review_20260925/build_review/probe.py`。结果 [probe_result.json](probe_result.json) 共 15 项通过。没有实际编译新扩展、重跑旧容器、补充外部资料，也没有验证真实模型解题、崩溃恢复或其它任务的训练准入。
