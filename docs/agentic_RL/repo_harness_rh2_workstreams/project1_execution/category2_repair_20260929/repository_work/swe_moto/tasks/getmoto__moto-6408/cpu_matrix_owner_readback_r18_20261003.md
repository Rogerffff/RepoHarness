# Moto6408 R18 三组对照：作者原件读回

2026-10-03。实际 noop／gold／reorder_only 为0／1／0，原 make init 三次均0，每次96项参考完整。本报告关闭三组评分原件读回；实际 UID 安装、公开 CC 及最终非作者验收仍待补全，不代表普通模型或训练准入。

固定消费者 R18 `cat2-cpu-r2e093-swe40-moto-offline-20261003-v1`，manifest `a84bdc339618e010440df3728c982b2d1d141b1f8295f69761984386ee3a512e`；实际 COPY-only 镜像 `sha256:f00e022c3edf2dd23121abab802e401a64ee9e98598f07fb37a83d5c4c2012a1`。新 ENV、材料、脚本、有效 patch、1F／95P 逐键均与固定 expected 相符；两作业 runtime_inputs 逐字节相同，合计三组属于同一运行条件。

noop `moto6408-cpu-81c24ca0fe48` 父退出0，回收45件原件；安装10.659秒 rc0、pytest12.030秒 rc1，原 F 失败、95P 全通过。详见 [noop读回](cpu_noop_preflight_r18_20261003.md)。

gold／reorder `moto6408-cpu-85ef01245f8b` 父退出0，回收60件原件；archive `6ff5b8c6f576b7b64b6dbece5979726040c404f5a33f38a0f56961a064b15d56`，manifest `6e7484af8524ee398148aa6d4d84476a002e231f10a00dbe04d355fce47cb093`。gold 安装11.126秒 rc0、pytest12.367秒 rc0、96项全通过／raw1；reorder 安装11.146秒 rc0、pytest12.698秒 rc1，仅原 F 所在函数失败／raw0。

reorder 的原测试前缀全部走过，包括读取迁移后的第二份 manifest；新增 `len(moved["images"]) == 1` 在文件635行实际观察2而失败，95P 仍全通过。它只改返回顺序，未移除重复标签归属，因此新断言确实拒绝该不正确修法。这里只证明新版真实拒绝位置，不伪造旧 R5 正式得分；固定工具的 constructed_negative_unrun 描述是运输前历史字面值，当前原件已实际运行。

逐原件 SHA／bytes 均复核；原完整 pytest 的96项与 parser96键一致，无重复、缺失或 skip。gold 与 reorder 的 FrozenPatch 均仅修改 `moto/ecr/models.py`，regular100644，无私有 pathset 改动；将精确原 patch 在公开 base 副本应用后的字节，与各 FrozenPatch 的完整 base64 内容及 digest 逐字节一致。两份实际源码 SHA 分别为 `6409665fa0420c68497ff050f3af09240fa4a8d0facbf19c883f4439c3d41a01` 和 `48d45a656d49931ccc3ae43c03e555b6b5240015bf4f7fb95b443ef55c46f315`。trusted restore／apply 成功，只由原 consumer 应用测试 patch。

两臂 CLI 包装退出0，与原 pytest0／1分别记录。candidate 删除成功；完整 CLI footer 的 manager containers_open／supply_open／cleanup_failures 均空，halted／aborted 空，final exit0；自有容器及网络查询 rc0，stdout／stderr 空。原件位于 `runs/category2_repair_20260929/moto_cpu_20261003/` 两 job 的 `_evidence/`，逐参考作者读回为各 `_author_raw_readback_r18_v1.json`。旧 R13 安装2及对应 raw 不回写；新三组不替代 UID、真实 CC 或非作者验收。
