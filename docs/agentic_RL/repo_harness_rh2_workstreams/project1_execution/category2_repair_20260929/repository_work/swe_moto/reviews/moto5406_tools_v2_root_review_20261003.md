# Moto5406 新验收工具附件核查

2026-10-03，root 非作者审查。附件 `runs/category2_repair_20260929/release_work_20261003/moto5406_acceptance_tools_v2/`，工具清单 SHA256 `711de3afcd5f71e865ccfdcb73902814c5280141ecb6737465ef1698cc08fddf`。绑定第三版 `cat2-cpu-r2e069-swe6-20261003-v1`，外部 manifest `40ca2914da2be665754175954defe4bbecfdb31efc1ad394153c09acfb5f9f15`。

**允许题主按此冻结附件执行已授权的 CPU 验收。未取得实际新 CPU/actor 通过。** root 逐文件核工具清单 9 件 SHA/大小，并阅读实际 common 增量。旧工具没有回写。

- 清单兼容只将发布的 `files.size` 严格归一为原 `bytes`，仍比对完整文件集、SHA与大小。未知 schema、额外字段和混合树继续拒绝。
- 旧布尔草稿锁改为实际 producer 绑定检查：固定 producer、公开及私有 digest，原/新 registry 和 28 参考、原补丁、原镜像逐项吻合；不是无条件解除检查。
- actor 和 actor-to-grader 两文件逐字不变；replay 仅帮助文案变化；预算、安装、manager、候选和清理沿原路径。
- 作者实际使用工作区统一解释器做默认 prepare 成功，actor/replay spec一致，坏 dispatch 被拒，安装仍 `make init`。此过程无 Docker；812 个发布成员事后保持一致，记录在同级 `moto5406_acceptance_tools_v2_checks/`。

远端由题主使用总协调指定的 `runtime_cpu_v2`，将 CLI 参数映射到本机实际路径；已有 fixed_inputs_local 仅是本地静态示例，不能直接搬过去或伪称新机身份。实际 inspect/done 输入必须来自该主机已核源镜像。先默认 prepare，成功后才用 `--execute`；输出到新目录，出现 infra 或清理未知按现行停派规则处理。
