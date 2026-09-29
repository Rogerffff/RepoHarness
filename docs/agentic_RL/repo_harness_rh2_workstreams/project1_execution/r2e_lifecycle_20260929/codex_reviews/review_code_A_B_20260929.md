**结论：A 的机制复核通过，可以用于编制两题 R-f 修订；具体新版题面仍须验收。B 有一处 P1，且尚未完成 R-d 验收，不能把“45 张镜像构建成功”当作正式可用。** 全程只读，未修改文件。

## 1. 代码问题

### A：P0 / P1 / P2 均没有

已核实：

- [构建公开面前应用修订](</Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/envpack/ingest_r2e_subset.py:646>)，随后计算新题面摘要并执行泄漏扫描。
- 前后 SHA、片段出现次数、非法目标、重复修订、空结果、无实际变化等拒绝逻辑成立。
- 修订号、前后摘要、决定出处进入 manifest；评分面记录修订号，包摘要绑定新版公开面。
- [消费期核对新版题面摘要](</Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/envpack/ingest_r2e_subset.py:839>)。独立探针确认：漏传修订单、错误后摘要、“旧题面却声称已修订”均被拒。
- 48 题重新 ingest 后，**四份数据文件及 manifest 均与现有封板产物逐字节一致**；现有四类修订和 v3 产物未受影响。

### B：P0 没有；P1 一项；P2 没有确认的额外代码缺陷

**P1：构建与消费的配方摘要口径不一致，阻断 orange3 `9b5494e2`。**  
可达性：`production_reachable`，现有正式入口可达。

- [构建端](</Users/roger/Desktop/claude-code-verl-stage0h/rh2/scripts/build_r2e_derived.py:534>)用叠加前摘要检查环境要求，但输出 overlay 只携带叠加后摘要。
- [正式 actor／回放共用检查](</Users/roger/Desktop/claude-code-verl-stage0h/rh2/src/repoharness2/adapters/slime/prepared_task_face.py:460>)仍将叠加后摘要直接交给 `env_requirement_mismatch`，而批准集合只有旧摘要。
- **复现**：取 `overlays_all_45.jsonl` 第 26 行，配封板同题 public/grading，调用 `overlay_binding_mismatch`，返回：
  ```text
  overlay:env_recipe_not_approved:r2e-mr-020:recipe_sha256=sha256:caa2db...
  ```
  同题原配方摘要 `512277…` 在构建端通过。45 条 overlay 中只有这一条失败。
- **影响**：包含该题的正式 `PreparedTaskFace` 会拒绝构造；不是仅少一条评分。
- **使用前修复**：统一构建与消费的组合摘要验证，保留批准内容绑定，不能只检查 `+env_v2` 字符串。验收须覆盖合法组合通过、错误依赖／摘要仍拒绝。不必因此暂停其它题的验收。

**兼容性补充**：不开开关时，六种 Dockerfile 组合及原配方摘要均与 HEAD 一致；但 [facts 无条件新增 `base_recipe_*`](</Users/roger/Desktop/claude-code-verl-stage0h/rh2/scripts/build_r2e_derived.py:528>)，所以不能宣称“所有输出逐字节不变”。

## 2. A 能否用于正式材料

**机制可以用，无需先修机制代码。** pillow `2b061b68`、orange3 `22e98f8f` 正式发布前仍需：

1. 完成具体题面修改的 base 实跑依据、逐行无答案／隐藏细节核对，以及未接触私有材料的新公开读者验收。
2. 新增修订单版本，同步更新输入 pins、ingest 产物及代码摘要锚点，保留旧 v3。
3. 题卡／汇报明确标注“自建修订题＋版本”，不能仅凭原 `instance_id` 冒充原 benchmark。

本次通过的是**修订机制**，不是尚未提交的两份具体新版题面。

## 3. B：R-d 四项验收

| 项目 | 判断 | 已有证据与缺口 |
|---|---|---|
| **① 改动范围、镜像身份、没有替代解题** | **部分满足** | `4014` facts 有镜像／配方身份和项目、venv 完整性证据。脚本直接写入范围在 `/opt/py`，不安装包；但[实际扫描所有匹配旧前缀的文本](</Users/roger/Desktop/claude-code-verl-stage0h/rh2/scripts/r2e_derive/sysconfig_v1.sh:21>)，并非配置文件白名单，另有字节码重编及递归 chmod。正式使用应保存实际修改清单，确认符合声明范围。 |
| **② 原失败路径、真实产物、原 bug 保留** | **未满足** | 手工对照支持“链接失败得到修复、工作区 `.so` 重建并被导入”。还缺**新配方镜像上的源码修改→构建→正式导出→全新 grader 实际加载并体现新行为**；也缺未修源码时公开 bug 仍存在的行为证据。 |
| **③ 按影响范围、同身份/profile 复验** | **部分满足** | 已有同 UID、无网络定点对照，但工作区权限是模拟正式启动；解释器同时影响 actor/grader，仍缺正式 profile 下的开发链及新镜像真实评分正负对照。 |
| **④ 范围、未查项、失败解释与保留** | **部分满足** | [记录明确承认端到端未做](</Users/roger/Desktop/claude-code-verl-stage0h/runs/r2e_lifecycle_20260929/evidence/sysconfig_manual_before_after_20260929.txt:16>)。另外三题损坏目前只有汇总说明，所给证据不足以核对失败现场和恢复结果，不能计为环境验收通过。 |

`sysconfig_paths_relocated` **足够检查配置字符串迁移，不足以验收构建能力**：它不验证库／头文件实际可读、链接成功、候选行为生效或正式交付。

## 4. 今晚使用前的必要事项

- 先修 B 的消费摘要问题，再启用含 `9b5494e2` 的正式题包。
- 编译题完成上述代表性正式交付链；不得用路径检查或 `import` 成功替代。
- 当前 45 条覆盖表缺 orange3 `f237f968`、pandas `294cbc8d`、`32dd55cb`；恢复并复验前保持暂挂。

**独立验证范围**：53 项无需落盘测试通过；另做内存重放和消费拒绝探针，重算匹配全部 45 条配方摘要；ruff、`bash -n` 通过。未重跑 11 项需落盘测试，也未运行 Docker／正式评分。