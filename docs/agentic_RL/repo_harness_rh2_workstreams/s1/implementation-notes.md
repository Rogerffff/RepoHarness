# S1 implementation-notes（行车记录）

执行计划：`../03-s1-execution-plan.md`。三节制，发现即记。

## Decisions

- [S1-0, 2026-07-09] slime 镜像 pin 定为 `slimerl/slime@sha256:a7317182c71d35712ee4edc86a5d1c313dc969efdf0026d339673299c186ea75`（U-H 验证通过的那个），F6 的双 pin 之一。远端保留镜像 + ~57GB HF 缓存供 S1-6/7 复用。

## Deviations

- [S1-0, 2026-07-09] 远端机器基础设施修复：Docker 登记了 nvidia runtime 但缺 NVIDIA Container Toolkit，装配 nvidia-container-toolkit 1.19.1-1 后 GPU 容器可用（属环境修复非计划偏离，记录备查——新租机器首日 checklist 应加这一条检查）。

## New-Unknowns

- [S1-0 核验, 2026-07-09] **引擎间 routing 行数约定不同（喂 S1-3）**：SGLang 路由行 = prompt_len - 1 + generated_len（本次 15-1+16=30，S0-6 的 [20,48,8] 同律）；vLLM（S0-5 probe）= prompt_len + generated_len（13+8=21）。TrajectoryProjection 的 tape 解码唯一点必须按引擎显式编码对齐约定（RoutingTensorRef.alignment 语义），不能假设两引擎同构。
- [S1 计划定稿, 2026-07-09] 两复核线程建议 A1~A10/B1/C1~C3 全部采纳（正式化为 s1/s1_supplementary_clauses.md，验收级效力）；F2~F6 定案，F5 按用户收紧版（并发 4/队列 8/可配置/实测后升）；F4 升四段式（B1 补 GPU pass-rate 预筛归 S2 末/S3-0）；uh_probe_result.json 已生成（A10）；8 题冻结状态已同步 swe_smoke_report.md（C2）。
