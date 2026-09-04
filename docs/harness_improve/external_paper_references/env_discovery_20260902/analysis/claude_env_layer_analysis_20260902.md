# 环境层综合分析与规划建议（Claude，2026-09-02）

> 性质：**讨论材料，非 owner 定案，非实施计划**。本文综合同目录三份调查
> （`rh2_env_layer_status`、`pi_environment_assets`、`external_env_increment`）
> 与 benchmark 图谱 pro 文档（`../../repo_harness_rh2_workstreams/tmp/外部pro模型调查2.md`），
> 给出环境层的坐标系、现状地图、组合建议、工作波次与待拍板项。
> 讨论阶段不套开发期协作手册。

---

## 一、环境的坐标系（把"环境=数据+仓库+harness+runtime"精确化）

三方独立收敛到同一形状（verifiers v1 的 Taskset/Harness/Runtime 三分、Harbor 任务包、我们的 `EnvironmentPackageV1`）：

```text
环境包（决定训什么/测什么）= task（题面+数据）
                            + workspace 快照（镜像 digest + base_commit）
                            + verifier/grader（评分事实唯一权威）
                            + runtime 需求声明（容器/资源/网络）
                            + 预算与终止语义
harness（决定以什么接口训）= 独立的一根轴，不进环境包
```

**把 harness 从环境包拆出去**的三个实际理由：① verifiers v1 在构造期就对 taskset×harness 做兼容 fail-fast，二者正交可组合；② B 线（多 harness 泛化）的因果矩阵要求"同环境 × 多 harness"，绑死就做不成；③ 反例：tau2/tau3 是唯二自带 harness 的环境，结论是"换 harness = 重写，只能当数据源"。

结论：**"决定环境 = 决定训什么测什么"精确化为：taskset×verifier 的组合分布决定训什么测什么；harness 轴、预算轴是叠加维度。**

## 二、现状合并地图：一句话是"资产硬、门缺、线断"

- **我们自己的**：216 题 SWE-Gym Lite 数据身份链已建成且防篡改极硬，但三处断裂——① 环境质量链零代码（四门 runner / EnvValidationReport / `grade_controlled_patch` 全部"设计齐备零实现"，其中 `grade_controlled_patch` 是单点瓶颈）；② 训练链零消费（miles 链固定吃 8 题 Verified 探针表）；③ held-out 一题未冻结（542 里 450 依赖从未发生的 R2E ingestion）。
- **可复用资产（重大利好）**：`reference/research-environments` 73 个环境里，terminal 域是完美候选（terminal_lego ~13.8k + tmax 14.6k 训练、terminal_bench_2 评测，全部 HarborTaskset 15~90 行薄壳，verifier 隔离天然达标，harness-agnostic，镜像预建）。与 **miles 官方 Harbor 集成**（`harbor-miles-v0.20.0`）汇合。
- **外部新事实（改判断的四条）**：① prime-rl v0.9.0 把 admission gates 做进正式版（资格化被验证为主流，但"做个门"的新颖性下降）；② Envs-FORGE 把难度控制升级为在线合成动作策略（CalibForge 之后最强参照）；③ Nebius 首次公开成本对标（153K→21K≈14% 存活、1 人日/任务、git 抓答案 reward hacking 实录）；④ Surge 办公任务 RL → SWE-Bench Pro +5.8 的跨域迁移证据。

## 三、环境组合（portfolio）建议

结合 benchmark 图谱 P0 能力（长程状态/完成验证/故障恢复/跨 harness 泛化/效率前沿）与内部辨识层六轴（同语义多接口/故障注入/compaction 边界/verifier 对抗/solver 难度/新鲜度）：

| 域 | 角色 | 载体 | 状态 |
|---|---|---|---|
| **SWE**（域 1） | 训练主域 + 首个 specialist | SWE-Gym Lite 216（过四门后出 bring-up 题单）；held-out 先用 SWE-Gym 半区 hydra66+bokeh26；R2E 后置 | 资产在、门未过 |
| **terminal**（域 2，建议新增） | 第二训练域 + C 线第二 specialist + TB 评测 | Harbor 格式：terminal_lego/tmax 训练，terminal_bench_2 评测 | 现成，成本低 |
| function-calling（冒烟） | 能力保持面 + 最便宜多接口探针场 | `bfcl_v3`（4,441 AST checker，零容器零网络） | 现成 |
| 故障注入（机制轴） | P0 能力 3 + A 线探针槽 | SWE/terminal 上加 fault proxy（S1/S2/S3 分类） | 待设计 |
| 合成/自产（供给轴） | 供给扩容 + 良率叙事（E8 必交付） | agent 自产（E4）→ SWE-smith 注入式 → Envs-FORGE 生成式 | 零实现 |

**为什么第二域强推荐 terminal**：三重汇合——PI 资产现成（28k 题量级）、miles 原生消费 Harbor、C 线 MOPD 需要第二个 specialist 域（同源约束下 specialist 必须自己训，terminal 是 SWE 之外验证成本最低的可执行域）。

**terminal 接入两形态（必须现在讲清的取舍）**：
- **T-a（miles Harbor agent server）**：agent loop 在 Harbor 侧，miles 只出 policy 端点。接入最快，但绕过 CC harness 和 token-faithful capture 链——黑盒式，与 Polar 同类。
- **T-b（rh2 capture 主线）**：自己的 CC harness 跑 terminal 任务，只复用 Harbor 任务格式 + verifier 边界。保持 tape/DIS/eligibility 全链，但要给 CC harness 配 terminal 任务面，把 Harbor verifier 接进 grading manager。
- 建议：**T-b 主线 + T-a 对照/评测面**。理由：训练信号可信性是立身之本，黑盒形态会让掉 B 线和 DIS 前提；T-a 作为"同任务不同接入形态"对照本身有价值，且能先跑起来验证任务质量。（详细审计见 `harbor_miles_integration_audit_20260902.md`。）

## 四、工作波次建议（标注"无论方向如何都要做"= 分层交付兜底层）

```text
E-Wave1【接线+补门】—— 无论最终实验选什么都要做
  ① grade_controlled_patch 受控评分入口（T2-d，签名已定，单点瓶颈）
  ② 四门 runner + EnvValidationReport（T2-e，规格已写死；x86 CPU ~$15-40/1-2 天）
  ③ 216 题过门 → BringupService 换表（W2a 依赖）→ bring-up 题单
  ④ held-out 先冻 SWE-Gym 半区（T=50~80 可满足），不等 R2E
  ⑤ W3b 归属线确认：AntiCheatSpec 改为运行期正向能力事实，
     环境包侧只保留镜像清理类生产期动作（要显式承认的设计变更）

E-Wave2【第二域 terminal】—— C 线与评测层前置
  ⑥ Harbor 任务格式 → EnvironmentPackage 映射（扩 source 枚举 = schema 升版）
  ⑦ T-b 形态接入 + terminal_bench_2 评测面；T-a 对照按需
  ⑧ terminal_lego 是私有 HF repo——可得性先确认

E-Wave3【资格化研究面】—— A 线研究增量
  ⑨ solver-relative learnability 探针（216 题 × 两 API solver + 一弱本地模型）
  ⑩ GPU pass-rate 预筛 [0.1,0.8] 落地（载体 = C 包待拍板）
  ⑪ verifier hardening 探针（exploit 清单用 SWE-rebench 实录 + Hardening 论文分类）

E-Wave4【供给扩容】—— 后置，按良率数据拉动
  ⑫ agent 自产流水线（E4 五步，50~200 题，良率=E8 必交付）
  ⑬ SWE-smith 注入式 / Envs-FORGE 合成动作策略 / K3 知识图谱（远期梯队）
```

**研究定位的诚实判断**：admission gates 进 prime-rl 正式版后，"我们做了资格门"不再是差异点。差异点在三处——(a) solver-relative learnability 与训练资格治理（EligibilityGate）的**贯通**（上游只到任务采样层，没接训练资格与轨迹事实）；(b) 诚实良率/成本数字披露（对标 Nebius 14%、1 人日/任务——我们 216 题四门存活率、自产线良率本身是可发表工程证据）；(c) 四门+受控评分+held-out 家族治理作为**可审计整链**而非散装检查。

## 五、待拍板项（按急迫排序）

1. **E-Wave1 是否立即启动**（`grade_controlled_patch` + 四门 runner 与 W0~W8 排期关系——它逻辑上属"数据线"，可与 infra 线并行）。
2. **第二域 terminal + Harbor 载体是否定案**，及 T-b 主线 / T-a 对照的形态取舍。
3. **held-out 冻结方案**：SWE-Gym 半区先冻（建议）vs 等 R2E ingestion。
4. **W3b 归属线**：确认 AntiCheatSpec 从环境生产期产物改为运行期能力事实（plan-06 已实际这么定，环境层文档需跟进承认）。
5. **verifiers pin 升级**：影响面已评估（见 `verifiers_v031_primerl_v090_impact_20260902.md`）。结论：升级=T0，pin 后 v1 经三轮重写，taskset 薄壳 + wire 契约需结构性重写（`info/run_rollout/run_group` + `@group_reward` 整体删除，换 `RunRequest{task_data}`→`RunResponse{episode}`），但 Form A 物理协议稳定、graph token-identity 三不变量语义保留。**建议：首训冻结期不升（无一是当前 Wave 前置），训后窗口做受控升级 spike；但 v0.3.0 的网络隔离配置形状（`NetworkPolicyConfig.allow/block` + EgressProxy，默认 `allow=["*"]` 精确等价旧 `--network host`）与 prime-rl v0.9.0 的 zero-output 熔断可现在即作为设计输入吸收，不产生依赖。** 待 owner 确认升级时点。

**一句话总结**：环境层最大杠杆不在"找更多新方法"，而在两周内把已有 216 题接上质量门和训练链（E-Wave1），同时用现成 Harbor terminal 资产以最低成本打开第二域（E-Wave2）——前者兜住分层交付的底，后者为 C 线 specialist 和评测层铺路；资格化研究增量（E-Wave3）站在这两块地基上做。
