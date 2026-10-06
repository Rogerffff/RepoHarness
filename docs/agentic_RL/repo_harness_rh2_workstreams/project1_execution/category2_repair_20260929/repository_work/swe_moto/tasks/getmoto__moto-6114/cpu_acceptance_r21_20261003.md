# Moto6114 新37参考：普通探针 CPU 验收

日期：2026-10-03。题主已完整读取并核对[最终非作者报告](../../reviews/moto6114_r21_neptune37_final_cpu_non_author_20261003.md)，19639 bytes，SHA256 `3d7cbf50091a3105ac04301f3a1e90e407fea8b5935ada48db52302e2826a110`。新37参考满足当前普通双模型诊断探针的题级 CPU 条件。训练、留出和 typed-actor 资格未授予。

材料为 `moto6114-cluster-identity-neptune-preservation-v2`，有效测试补丁 SHA256 `2a9661d78743cf5e36f8363e308d63260ab2076bf4bc1d68de8a9e5fd226dda4`：保留原1F／34P，新增两条现有 Neptune 按名称 start／delete 的 P2P，共37参考。公开题面、base、原安装和测试入口保持。

| 有效控制 | 正式分数 | 原 make init／pytest 退出 | 原35项 | 新2项 | reset |
| --- | ---: | --- | --- | --- | ---: |
| R19 noop | 0 | 0／1 | 原F失败、34P通过 | 全过 | 300秒 |
| R19 gold | 1 | 0／0 | 全过 | 全过 | 300秒 |
| R19 wrong_first | 0 | 0／1 | 原F返回错误集群、34P通过 | 全过 | 300秒 |
| R21 exact_qwen_source | 0 | 0／1 | 全过 | 两项失败 | 900秒 |

四个有效控制完整覆盖37参考，无缺失、跳过、重复或解析范围外项，原安装成功，候选和 manager 正常清理、自有资源查询实际成功且为空。固定旧 Qwen 源码在新 CPU 尝试中按名称启动 Neptune 抛 `InvalidDBClusterStateFault`，删除访问不存在的 `deletion_protection` 属性而报 `AttributeError`；两项均为语义失败。该源码重放不是新自主模型尝试。

三臂来自固定 R19，manifest `2cfdd9b4f1134c0915346b727b729665482c4c1121b550764833f16f2982402e`；恢复臂来自固定 R21，manifest `630f71fc1a4ae6f587f3161fae56d92927a91801ae4b08954a556ee059cada9c`，job `moto6114-cpu-9b1ef9d10723`。R21 仅按明确材料和实际 CPU 镜像 `1d8dded2ee5bbe9275514fdc603116ac9f36da5e30c19b2d4ffcba4d4a9f27d5` 的已发布保护政策延长 reset；其它脚本和预算保持。不能写成四臂全同条件；单次恢复不证明旧超时根因消除，也不证明900是成功的唯一原因。旧 R19 exact 的300秒保护超时仍是 infra_failure／null，未改成0。

实际开发 UID54321 在 R19 的原 `make init`、激活、testbed 模块、SDK1.35.9及清理已验。历史真实 CC 三条指定公开操作仅按相同公开条件和 helpers 的既有报告范围复用；历史物理镜像不同，没有 fresh R19／R21 CC、完整公开题面首请求自主解题、真实 actor FrozenPatch 或 actor→grader 验收。两项历史 marker false 保留。

另立新37探针请求，旧35 CPU 验收、旧 Qwen raw1／安装2、旧 FrozenPatch、旧支持失败和旧探针请求保留原身份。GPU执行者独立固定兼容代码、实际镜像与完整预算，核两个用户的 wheel 可读性及原安装；不同物理 GPU 镜像不能自动借用 CPU 的900政策。双模型首轮结果仍须题主逐轨迹分析，单样本不能推出稳定性。
