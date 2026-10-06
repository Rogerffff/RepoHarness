# Moto5960：R18 普通 CPU 诊断验收

2026-10-03。固定 R18 的三臂评分、真实 UID54321 原公开安装与真实 CC 六条公开操作已通过作者核对及非作者最终验收，可以提交本材料版本的基座探针。

固定 release 为 `cat2-cpu-r2e093-swe40-moto-offline-20261003-v1`，manifest `a84bdc339618e010440df3728c982b2d1d141b1f8295f69761984386ee3a512e`。实际 CPU COPY-only 镜像为 `sha256:4bafbb6965ff41c0f6eb50a73f831e7b62c41b5beda6ffad957fbc926c2359ac`；公开题面与 base 保持，原 `make init` 和测试命令保持。

- noop／gold／omit_keys_only 实际 raw 为 0／1／0，三次原安装均退出0。原两个 F2P、新增 scan KEYS_ONLY F2P 和155个 P2P 均完整计入。实际 pytest159项与 parser158个参考的差异来自两个含空格参数的历史合键，两行三臂均 PASSED；不修改 parser。
- omit 的 Count／Items 长度前置断言通过，新增4754行断言准确检出两条结果仍含 payload；其它两个 F2P 与全部 P2P 通过。
- 真实 UID54321 下原 `make init` 退出0，目标模块来自 `/testbed`，boto3／botocore 为1.35.9；实际镜像与资源限制核对通过，最终自有容器／网络查询成功且为空。
- 真实 CC2.1.205＋确定性桩执行原 INSTALL、C1、C2、C3a／b／c。C2 两种投影分别完成3／6项读取后在最后目标断言失败；三个公开 pytest 命令分别15、1、2项通过。首请求公开 prompt、轨迹、完整输出、实际身份／隔离及 finally 清理已核。两个旧 marker 检查 false 原值保留，实际解释器及激活权限证据见独立报告。

最终非作者报告：[moto5960_final_cpu_non_author_20261003.md](../../reviews/moto5960_final_cpu_non_author_20261003.md)，23106B，SHA256 `f9da4c33ab813b0b6e5c9bff02d4cb57eda45a0104050b890d6b560f25aef35d`。独立重新核对138件原运行文件及四个归档，报告已全文读取。

原件 job 为 `moto5960-cpu-eeaa3dd27a5d`、`moto5960-cpu-66515b832d45`、`moto5960-uid-a680fa8321a6`、`moto5960-actor-668cd16294ae`，均 parent0，位于 `runs/category2_repair_20260929/moto_cpu_20261003/<job>_evidence/`。

本验收限定普通诊断：公开 CC 不代表自主模型求解，未证明 actor→FrozenPatch→grader，也未授予 typed actor、训练或留出资格。旧 R13 安装2和旧 raw 保留；旧 R5 反例正式分数仍未知。GPU须固定自己的实际代码／镜像／首请求，并产生新 baseline、FrozenPatch 和完整结果。
