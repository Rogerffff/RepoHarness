# Moto6408：R18 普通 CPU 诊断验收

2026-10-03。固定 R18 的三臂评分、真实 UID54321 原公开安装与真实 CC 五条公开操作已通过作者核对及非作者最终验收，可以提交本材料版本的基座探针。

固定 release 为 `cat2-cpu-r2e093-swe40-moto-offline-20261003-v1`，manifest `a84bdc339618e010440df3728c982b2d1d141b1f8295f69761984386ee3a512e`。实际 CPU COPY-only 镜像为 `sha256:f00e022c3edf2dd23121abab802e401a64ee9e98598f07fb37a83d5c4c2012a1`；公开题面、base、原安装与测试命令保持。

- noop／gold／reorder_only 实际 raw 为0／1／0，原安装均退出0，每臂96个参考完整，原95个 P2P 全通过。gold 全部通过；reorder 已通过原测试前缀，在新增635行唯一归属断言被准确拒绝，实际同一标签返回2个镜像而非1个。
- 真实 UID54321 执行原 `make init` 成功，解释器与 ECR 模块来自 `/testbed`，模块 SHA 与原 base 一致，boto3／botocore 均1.35.9。实际镜像与2CPU／4GiB／PID512／shm64MiB限制、激活及自有清理通过。
- 真实 CC2.1.205＋确定性桩执行原 INSTALL、C1、C2、C3a／b。C2 在完成两次标签写入和读取后于公开脚本30行 `initial_image != new_image` 失败，准确复现原问题；两个公开 pytest 命令分别19项与原95项通过。首请求、完整轨迹／输出、实际身份／隔离及 finally 清理均已核。两个旧 marker 检查 false 原值及适用边界保留。

最终非作者报告：[moto6408_final_cpu_non_author_20261003.md](../../reviews/moto6408_final_cpu_non_author_20261003.md)，23841B，SHA256 `3184bfc0aa0ee57da2692d18b23d78fb6c2b0d7ff5a21e70a9e2ef45a2641112`。独立核对136件原运行文件及四个归档。题主全文读取，随后仅将一处 find-links 路径笔误经原件核对改为 `/opt/rh2/build-wheels`，已验证其余字节不变。

原件 job 为 `moto6408-cpu-81c24ca0fe48`、`moto6408-cpu-85ef01245f8b`、`moto6408-uid-f1109eba8347`、`moto6408-actor-ab7e8c1ffbbd`，均 parent0，位于 `runs/category2_repair_20260929/moto_cpu_20261003/<job>_evidence/`。

本验收限定普通诊断：公开 CC 不代表自主模型求解，未证明 actor→FrozenPatch→grader，也未授予 typed actor、训练或留出资格。原随机 manifest helper 保持；单轮结果不证明跨种子稳定。旧 R13 安装2及原 raw 保留，旧 R5 反例正式分数仍未知。GPU须固定自己的实际代码／镜像／首请求，产生新 baseline、FrozenPatch 和完整结果。
